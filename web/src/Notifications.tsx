import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import Modal from "./components/Modal";
import { Pagination, RecordState, useRecords } from "./records";
import type { ListPosition, HistoryMode } from "./navigation-state";

type Destination = { id: string; name: string; configured: boolean };
type Channel = {
  id: string;
  name: string;
  destination_id: string;
  task_statuses: string[];
  enabled: boolean;
  interval_seconds: number;
  revision: number;
  configured: boolean;
  destination_review_current: boolean;
};
type Delivery = {
  id: string;
  channel_id: string;
  channel_revision: number;
  destination_id: string;
  task_id: string | null;
  status: string;
  attempts: number;
  http_status?: number | null;
  result_code?: string;
  created_at: number;
  test_mode?: boolean;
  payload: { task_name?: string; kind: string };
};
type Position = ListPosition & {
  onPositionChange: (value: ListPosition, mode?: HistoryMode) => void;
};
type ListProps = {
  search: string;
  onSearch: (value: string) => void;
  status: string;
  onStatus: (value: string) => void;
  position: Position;
  canAdmin: boolean;
};
const taskNames: Record<string, string> = {
  completed: "완료",
  failed: "실패",
  stopped: "중지",
  interrupted: "서버 중단",
  rejected: "승인 거절",
};
const deliveryNames: Record<string, string> = {
  queued: "전송 대기",
  dispatching: "전송 중",
  delivered: "수신처 수락",
  failed: "실패",
  unknown: "미확인",
  blocked: "전송 차단",
};
const reasonNames: Record<string, string> = {
  receiver_accepted: "수신처 서버가 요청을 수락했습니다.",
  receiver_rejected: "수신처 서버가 오류 상태를 반환했습니다.",
  transport_unconfirmed: "요청 처리 결과를 확인하지 못했습니다.",
  process_receipt_unconfirmed:
    "이전 프로세스의 전송 결과를 확인하지 못했습니다.",
  address_unavailable: "수신처 연결 주소를 확인하세요.",
  destination_changed: "수신처 설정이 변경돼 전송하지 않았습니다.",
  channel_changed: "알림 채널이 변경돼 전송하지 않았습니다.",
  credential_unavailable: "수신처 인증 설정을 확인하세요.",
  channel_approver_unavailable:
    "채널을 승인한 관리자의 현재 권한을 확인하세요.",
  channel_not_approved: "채널의 수신처 검토가 필요합니다.",
};
const changed = () => window.dispatchEvent(new Event("aegis-records-changed"));
const message = (error: unknown) =>
  error instanceof Error ? error.message : "요청을 처리하지 못했습니다.";
const date = (value: number) => new Date(value * 1000).toLocaleString();
function useMounted() {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return mounted;
}

function ChannelEditor({
  channel,
  destinations,
  onClose,
}: {
  channel?: Channel;
  destinations: Destination[];
  onClose: () => void;
}) {
  const [name, setName] = useState(channel?.name || ""),
    [destination, setDestination] = useState(
      channel?.destination_id || destinations[0]?.id || "",
    );
  const [statuses, setStatuses] = useState(
      channel?.task_statuses || ["failed", "interrupted"],
    ),
    [enabled, setEnabled] = useState(channel?.enabled || false);
  const [interval, setInterval] = useState(
      String(channel?.interval_seconds || 60),
    ),
    [revision, setRevision] = useState(channel?.revision || 0);
  const [latest, setLatest] = useState<Channel | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const pending = useRef(false),
    mounted = useMounted(),
    retry = useRef<{ body: string; id: string } | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const definition = {
      name: name.trim(),
      destination_id: destination,
      task_statuses: statuses,
      enabled,
      interval_seconds: Number(interval),
      ...(channel ? { expected_revision: revision } : {}),
    };
    const body = JSON.stringify(definition);
    if (!retry.current || retry.current.body !== body)
      retry.current = { body, id: crypto.randomUUID() };
    try {
      await api(
        channel
          ? `/notification-channels/${channel.id}`
          : "/notification-channels",
        channel ? "PUT" : "POST",
        { ...definition, request_id: retry.current.id },
      );
      if (mounted.current) {
        changed();
        onClose();
      }
    } catch (error) {
      if (mounted.current) setError(message(error));
      if (channel)
        try {
          const current = await api<Channel>(
            `/notification-channels/${channel.id}`,
          );
          if (mounted.current && current.revision !== revision)
            setLatest(current);
        } catch {
          /* Retain the draft and its original failure. */
        }
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={channel ? "알림 채널 수정" : "알림 채널 만들기"}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <form onSubmit={submit} aria-busy={busy}>
        <fieldset disabled={busy} className="notification-fields">
          <label>
            채널 이름
            <input
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            수신처
            <select
              required
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            >
              <option value="">수신처 선택</option>
              {destinations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                  {!item.configured && " · 설정 확인 필요"}
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend>알릴 작업 상태</legend>
            {Object.entries(taskNames).map(([id, label]) => (
              <label className="notification-check" key={id}>
                <input
                  type="checkbox"
                  checked={statuses.includes(id)}
                  onChange={(e) =>
                    setStatuses((values) =>
                      e.target.checked
                        ? [...values, id]
                        : values.filter((value) => value !== id),
                    )
                  }
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label>
            채널별 최소 전송 간격 (초)
            <input
              type="number"
              required
              min={1}
              max={3600}
              step={1}
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
            />
          </label>
          <label className="notification-check">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            수신처를 검토했고, 저장 이후의 작업 종료 알림을 활성화합니다.
          </label>
          <p>
            비활성 채널도 테스트 알림을 보낼 수 있습니다. 채널 저장은 이전 전송
            기록의 수신처를 바꾸지 않습니다.
          </p>
        </fieldset>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        {latest && (
          <section className="template-conflict">
            <p>
              현재 채널: {latest.name} · 버전 {latest.revision} ·{" "}
              {latest.enabled ? "활성" : "비활성"}
            </p>
            <p>입력은 유지됩니다. 최신 버전을 검토한 뒤 다시 저장하세요.</p>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setRevision(latest.revision);
                setLatest(null);
                setError("");
              }}
            >
              최신 버전으로 다시 검토
            </button>
          </section>
        )}
        <div className="modal-actions">
          <button type="button" disabled={busy} onClick={onClose}>
            취소
          </button>
          <button
            className="primary"
            disabled={
              busy || Boolean(latest) || !statuses.length || !destination
            }
          >
            {busy ? "저장 중…" : "저장"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ChannelHistory({
  channel,
  onClose,
}: {
  channel: Channel;
  onClose: () => void;
}) {
  type Version = {
    id: string;
    revision: number;
    action: string;
    snapshot: Channel;
    actor: { name: string };
    created_at: number;
  };
  const records = useRecords<Version>(
    "notification-history",
    "",
    {},
    undefined,
    `/notification-channels/${channel.id}/history`,
    false,
  );
  return (
    <Modal title={`${channel.name} 변경 이력`} onClose={onClose}>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          <ul className="notification-history">
            {records.items.map((row) => (
              <li key={row.id}>
                <strong>
                  버전 {row.revision} · {row.action}
                </strong>
                <p>
                  {row.snapshot.name} ·{" "}
                  {row.snapshot.enabled ? "활성" : "비활성"} · {row.actor.name}
                </p>
                <small>{date(row.created_at)}</small>
              </li>
            ))}
          </ul>
          <Pagination records={records} />
        </>
      )}
    </Modal>
  );
}

function ChannelTest({
  channel,
  onClose,
  onDeliveries,
}: {
  channel: Channel;
  onClose: () => void;
  onDeliveries: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [delivery, setDelivery] = useState("");
  const pending = useRef(false),
    id = useRef(crypto.randomUUID()),
    mounted = useMounted();
  async function submit() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ delivery_id: string }>(
        `/notification-channels/${channel.id}/test`,
        "POST",
        { expected_revision: channel.revision, request_id: id.current },
      );
      if (mounted.current) {
        changed();
        setDelivery(result.delivery_id);
      }
    } catch (error) {
      if (mounted.current) setError(message(error));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title="테스트 알림 전송"
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <p>
        {channel.name} · 버전 {channel.revision}
      </p>
      <p>
        저장된 수신처로 테스트 요청을 한 번 보냅니다. 작업 실행이나 채널 활성화
        상태는 바뀌지 않습니다.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {delivery && (
        <p role="status">
          테스트 알림이 전송 대기에 등록됐습니다. 실제 결과는 전송 이력에서
          확인하세요.
        </p>
      )}
      <div className="modal-actions">
        <button disabled={busy} onClick={onClose}>
          닫기
        </button>
        {delivery ? (
          <button
            className="primary"
            onClick={() => {
              onClose();
              onDeliveries();
            }}
          >
            전송 이력 보기
          </button>
        ) : (
          <button
            className="primary"
            disabled={busy || !channel.configured}
            onClick={() => void submit()}
          >
            {busy ? "등록 중…" : "테스트 알림 보내기"}
          </button>
        )}
      </div>
    </Modal>
  );
}

export function NotificationChannels({
  canAdmin,
  search,
  onSearch,
  status,
  onStatus,
  position,
  onDeliveries,
}: ListProps & { onDeliveries: () => void }) {
  const records = useRecords<Channel>(
    "notification-channels",
    search,
    { status },
    position,
    "/notification-channels",
  );
  const [metadata, setMetadata] = useState<{
      destinations: Destination[];
      alive: boolean;
    } | null>(null),
    [metaError, setMetaError] = useState(""),
    [load, setLoad] = useState(0);
  const [editor, setEditor] = useState<Channel | null | undefined>(undefined),
    [history, setHistory] = useState<Channel | null>(null),
    [test, setTest] = useState<Channel | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setMetaError("");
    api<{ destinations: Destination[]; alive: boolean }>(
      "/notifications",
      "GET",
      undefined,
      controller.signal,
    )
      .then((value) => {
        if (!controller.signal.aborted) setMetadata(value);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setMetaError(message(error));
      });
    return () => controller.abort();
  }, [load]);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>알림 채널</h2>
          <p className="subtle">
            최대25개 채널 · 인증정보는 화면과 전송 이력에 표시하지 않습니다.
          </p>
        </div>
        <button onClick={onDeliveries}>전송 이력 보기</button>
      </div>
      <div className="template-toolbar">
        <label>
          채널 검색
          <input
            maxLength={200}
            value={search}
            onChange={(e) => onSearch(e.target.value)}
          />
        </label>
        <select
          aria-label="채널 상태"
          value={status}
          onChange={(e) => onStatus(e.target.value)}
        >
          <option value="all">모든 채널</option>
          <option value="active">활성</option>
          <option value="disabled">비활성</option>
        </select>
        {canAdmin && (
          <button
            className="primary"
            disabled={!metadata?.destinations.length}
            onClick={() => setEditor(null)}
          >
            채널 만들기
          </button>
        )}
      </div>
      {metaError && (
        <div className="notification-notice">
          <p role="alert">{metaError}</p>
          <button onClick={() => setLoad((value) => value + 1)}>
            수신처 다시 확인
          </button>
        </div>
      )}
      {metadata && !metadata.destinations.length && (
        <p className="notification-notice">
          설치 관리자가 고정 수신처를 먼저 설정하면 알림 채널을 만들 수
          있습니다.
        </p>
      )}
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          <div className="template-cards">
            {records.items.map((channel) => (
              <article className="template-card" key={channel.id}>
                <h3>{channel.name}</h3>
                <p>
                  {channel.enabled ? "활성" : "비활성"} · 버전{" "}
                  {channel.revision} · 최소 {channel.interval_seconds}초 간격
                </p>
                <p>
                  수신처:{" "}
                  {metadata?.destinations.find(
                    (item) => item.id === channel.destination_id,
                  )?.name || channel.destination_id}
                </p>
                <p>
                  {channel.task_statuses.map((id) => taskNames[id]).join(" · ")}
                </p>
                {!channel.configured && <p>수신처 설정을 확인하세요.</p>}
                {channel.enabled &&
                  channel.configured &&
                  !channel.destination_review_current && (
                    <p>
                      수신처 설정이 변경됐습니다. 채널을 다시 검토해 저장하세요.
                    </p>
                  )}
                <div className="template-actions">
                  <button onClick={() => setHistory(channel)}>변경 이력</button>
                  {canAdmin && (
                    <>
                      <button onClick={() => setEditor(channel)}>수정</button>
                      <button
                        disabled={!channel.configured}
                        onClick={() => setTest(channel)}
                      >
                        테스트 알림
                      </button>
                    </>
                  )}
                </div>
              </article>
            ))}
          </div>
          {records.total === 0 && (
            <p className="notification-notice">
              일치하는 알림 채널이 없습니다.
            </p>
          )}
          <Pagination records={records} />
        </>
      )}
      {editor !== undefined && metadata && (
        <ChannelEditor
          channel={editor || undefined}
          destinations={metadata.destinations}
          onClose={() => setEditor(undefined)}
        />
      )}
      {history && (
        <ChannelHistory channel={history} onClose={() => setHistory(null)} />
      )}
      {test && (
        <ChannelTest
          channel={test}
          onClose={() => setTest(null)}
          onDeliveries={onDeliveries}
        />
      )}
    </section>
  );
}

function DeliveryRetry({
  record,
  onClose,
}: {
  record: Delivery;
  onClose: () => void;
}) {
  const [confirmed, setConfirmed] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const pending = useRef(false),
    mounted = useMounted(),
    retry = useRef<{ body: string; id: string } | null>(null);
  const requiresConfirmation =
    record.status === "unknown" || record.http_status != null;
  async function submit() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const body = {
      expected_attempts: record.attempts,
      confirm_possible_duplicate: confirmed,
    };
    const serialized = JSON.stringify(body);
    if (!retry.current || retry.current.body !== serialized)
      retry.current = { body: serialized, id: crypto.randomUUID() };
    try {
      await api(`/notification-deliveries/${record.id}/retry`, "POST", {
        ...body,
        request_id: retry.current.id,
      });
      if (mounted.current) {
        changed();
        onClose();
      }
    } catch (error) {
      if (mounted.current) setError(message(error));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title="알림 재전송 검토"
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <p>
        {record.payload.task_name || "테스트 알림"} ·{" "}
        {deliveryNames[record.status]} · 이전 시도 {record.attempts}회
      </p>
      <p>
        원래 승인한 수신처로 같은 알림을 다시 전송합니다. 최대3회이며, 이전 시도
        이력은 유지됩니다.
      </p>
      {requiresConfirmation && (
        <label className="notification-check">
          <input
            type="checkbox"
            checked={confirmed}
            disabled={busy}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          수신처가 이미 처리했을 가능성을 확인했고, 중복 전송 가능성을
          이해했습니다.
        </label>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="modal-actions">
        <button disabled={busy} onClick={onClose}>
          취소
        </button>
        <button
          className="primary"
          disabled={busy || (requiresConfirmation && !confirmed)}
          onClick={() => void submit()}
        >
          {busy ? "등록 중…" : "재전송 요청"}
        </button>
      </div>
    </Modal>
  );
}

function DeliveryDetail({
  initial,
  canAdmin,
  onClose,
  onTask,
}: {
  initial: Delivery;
  canAdmin: boolean;
  onClose: () => void;
  onTask: (id: string) => void;
}) {
  const [record, setRecord] = useState(initial),
    [error, setError] = useState(""),
    [retry, setRetry] = useState<Delivery | null>(null);
  const attempts = useRecords<{
    id: string;
    attempt: number;
    status: string;
    result_code?: string;
    http_status?: number;
    started_at: number;
    finished_at?: number;
  }>(
    "notification-attempts",
    "",
    {},
    undefined,
    `/notification-deliveries/${initial.id}/attempts`,
  );
  useEffect(() => {
    let controller: AbortController | null = null;
    let sequence = 0;
    const update = () => {
      controller?.abort();
      controller = new AbortController();
      const active = controller;
      const current = ++sequence;
      api<Delivery>(
        `/notification-deliveries/${initial.id}`,
        "GET",
        undefined,
        active.signal,
      )
        .then((value) => {
          if (!active.signal.aborted && sequence === current) {
            setRecord(value);
            setError("");
          }
        })
        .catch((error) => {
          if (!active.signal.aborted && sequence === current)
            setError(message(error));
        });
    };
    update();
    const timer = setInterval(update, 4000);
    window.addEventListener("aegis-records-changed", update);
    return () => {
      controller?.abort();
      clearInterval(timer);
      window.removeEventListener("aegis-records-changed", update);
    };
  }, [initial.id]);
  if (retry)
    return <DeliveryRetry record={retry} onClose={() => setRetry(null)} />;
  return (
    <Modal title="알림 전송 상세" onClose={onClose}>
      <h3>{record.payload.task_name || "테스트 알림"}</h3>
      <p>
        {deliveryNames[record.status]} · 전송 시도 {record.attempts}/3 ·{" "}
        {date(record.created_at)}
      </p>
      <p>
        {reasonNames[record.result_code || ""] ||
          "전송 결과를 기다리고 있습니다."}
        {record.http_status != null && ` HTTP ${record.http_status}`}
      </p>
      <p>
        채널 버전 {record.channel_revision} · 수신처 {record.destination_id}
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="template-actions">
        {record.task_id && (
          <button
            onClick={() => {
              onClose();
              onTask(record.task_id!);
            }}
          >
            원본 작업 보기
          </button>
        )}
        {canAdmin &&
          ["failed", "unknown", "blocked"].includes(record.status) &&
          record.attempts < 3 && (
            <button className="primary" onClick={() => setRetry(record)}>
              재전송 검토
            </button>
          )}
      </div>
      <h3>전송 시도 이력</h3>
      {(!attempts.ready || attempts.error) && (
        <RecordState records={attempts} />
      )}
      {attempts.ready && (
        <>
          <ul className="notification-history">
            {attempts.items.map((attempt) => (
              <li key={attempt.id}>
                <strong>
                  {attempt.attempt}회 · {deliveryNames[attempt.status]}
                </strong>
                <p>
                  {reasonNames[attempt.result_code || ""] ||
                    "전송 결과 확인 중"}
                  {attempt.http_status != null &&
                    ` HTTP ${attempt.http_status}`}
                </p>
                <small>{date(attempt.started_at)}</small>
              </li>
            ))}
          </ul>
          {attempts.total === 0 && <p>전송 시도 전입니다.</p>}
          <Pagination records={attempts} />
        </>
      )}
    </Modal>
  );
}

export function NotificationDeliveries({
  canAdmin,
  search,
  onSearch,
  status,
  onStatus,
  position,
  onChannels,
  onTask,
}: ListProps & { onChannels: () => void; onTask: (id: string) => void }) {
  const records = useRecords<Delivery>(
    "notification-deliveries",
    search,
    status !== "all" ? { status } : {},
    position,
    "/notification-deliveries",
  );
  const [detail, setDetail] = useState<Delivery | null>(null);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>알림 전송 이력</h2>
          <p className="subtle">
            수신처 수락은 HTTP 응답 기준입니다. 미확인 요청은 자동 재전송하지
            않습니다.
          </p>
        </div>
        <button onClick={onChannels}>알림 채널 보기</button>
      </div>
      <div className="template-toolbar">
        <label>
          작업·채널 검색
          <input
            value={search}
            maxLength={200}
            onChange={(e) => onSearch(e.target.value)}
          />
        </label>
        <select
          aria-label="알림 전송 상태"
          value={status}
          onChange={(e) => onStatus(e.target.value)}
        >
          <option value="all">모든 전송</option>
          {Object.entries(deliveryNames).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          {records.total ? (
            <div
              className="table-scroll"
              tabIndex={0}
              aria-label="알림 전송 목록"
            >
              <table>
                <thead>
                  <tr>
                    <th>원본</th>
                    <th>상태</th>
                    <th>시도</th>
                    <th>생성 시각</th>
                    <th>상세</th>
                  </tr>
                </thead>
                <tbody>
                  {records.items.map((record) => (
                    <tr key={record.id}>
                      <td>
                        {record.payload.task_name || "테스트 알림"}
                        <small>
                          {record.destination_id} · 채널 버전{" "}
                          {record.channel_revision}
                        </small>
                      </td>
                      <td>{deliveryNames[record.status]}</td>
                      <td>{record.attempts}/3</td>
                      <td>{date(record.created_at)}</td>
                      <td>
                        <button
                          onClick={() => setDetail(record)}
                          aria-label={`${record.payload.task_name || "테스트 알림"} 전송 상세`}
                        >
                          상세 보기
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="notification-notice">
              일치하는 알림 전송 기록이 없습니다.
            </p>
          )}
          <Pagination records={records} />
        </>
      )}
      {detail && (
        <DeliveryDetail
          key={detail.id}
          initial={detail}
          canAdmin={canAdmin}
          onClose={() => setDetail(null)}
          onTask={onTask}
        />
      )}
    </section>
  );
}
