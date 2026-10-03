import { useEffect, useRef, useState } from "react";
import { api } from "./api";

export type TriageFinding = {
  id: string;
  status: string;
  triage_revision?: number;
  assignee_id?: string | null;
  assignee_name?: string;
  assignee_username?: string;
  acceptance_reason?: string;
  resolution_reason?: string;
};
type Person = { id: string; name: string; username: string };
type History = {
  id: string;
  action: string;
  created_at: number;
  reason: string;
  actor: { name: string; username?: string };
  changes: Record<string, { before: unknown; after: unknown }>;
};
type Page<T> = {
  items: T[];
  total: number;
  has_more: boolean;
  snapshot?: number;
};
const statuses: Record<string, string> = {
  open: "미조치",
  accepted: "위험 수용",
  resolved: "해결",
};
const actions: Record<string, string> = {
  triage: "조치 변경",
  detected: "최초 발견",
  observed: "추가 관찰",
  reopened: "재발견",
  retest: "재검증",
};
const fields: Record<string, string> = {
  status: "상태",
  assignee_id: "담당자 ID",
  assignee_name: "담당자",
  assignee_username: "계정",
  acceptance_reason: "수용 사유",
  resolution_reason: "해결 사유",
};

export function FindingTriage({
  finding,
  canOperate,
  onUpdated,
  onReload,
}: {
  finding: TriageFinding;
  canOperate: boolean;
  onUpdated: (value: TriageFinding) => void;
  onReload: () => void;
}) {
  const [status, setStatus] = useState(finding.status);
  const [owner, setOwner] = useState(finding.assignee_id || "");
  const [acceptance, setAcceptance] = useState(finding.acceptance_reason || "");
  const [resolution, setResolution] = useState(finding.resolution_reason || "");
  const [search, setSearch] = useState(""),
    [ownerOffset, setOwnerOffset] = useState(0);
  const [people, setPeople] = useState<Page<Person>>({
    items: [],
    total: 0,
    has_more: false,
  });
  const [offset, setOffset] = useState(0),
    [snapshot, setSnapshot] = useState<number>();
  const [entries, setEntries] = useState<Page<History>>({
    items: [],
    total: 0,
    has_more: false,
  });
  const [error, setError] = useState(""),
    [historyError, setHistoryError] = useState("");
  const [directoryError, setDirectoryError] = useState(""),
    [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(
    finding.assignee_id
      ? {
          id: finding.assignee_id,
          name: finding.assignee_name || "",
          username: finding.assignee_username || "",
        }
      : null,
  );
  useEffect(() => {
    if (!canOperate) return;
    const controller = new AbortController();
    setDirectoryError("");
    const timer = setTimeout(() => {
      api<Page<Person>>(
        `/assignees?${new URLSearchParams({ search, offset: String(ownerOffset), limit: "25" })}`,
        "GET",
        undefined,
        controller.signal,
      )
        .then((data) => {
          if (!controller.signal.aborted) setPeople(data);
        })
        .catch((e) => {
          if (!controller.signal.aborted) setDirectoryError(e.message);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search, ownerOffset, canOperate]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setHistoryError("");
    const query = new URLSearchParams({ limit: "25", offset: String(offset) });
    if (snapshot !== undefined) query.set("snapshot", String(snapshot));
    api<Page<History>>(
      `/findings/${finding.id}/history?${query}`,
      "GET",
      undefined,
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) setEntries(data);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setHistoryError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [finding.id, offset, snapshot]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const value = await api<TriageFinding>(
        `/findings/${finding.id}`,
        "PATCH",
        {
          expected_revision: finding.triage_revision || 1,
          status,
          assignee_id: owner || null,
          acceptance_reason: acceptance,
          resolution_reason: resolution,
        },
      );
      onUpdated(value);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  const options =
    selectedPerson && !people.items.some((p) => p.id === selectedPerson.id)
      ? [selectedPerson, ...people.items]
      : people.items;
  return (
    <section className="triage-panel" aria-label="발견 사항 조치 기록">
      <h4 className="detail-heading">담당자와 조치</h4>
      {canOperate ? (
        <form onSubmit={save} className="triage-form">
          <label>
            조치 상태
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={busy}
            >
              {Object.entries(statuses).map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            담당자 검색
            <input
              value={search}
              maxLength={100}
              onChange={(e) => {
                setSearch(e.target.value);
                setOwnerOffset(0);
              }}
              placeholder="이름 또는 계정"
              disabled={busy}
            />
          </label>
          <label>
            담당자
            <select
              value={owner}
              disabled={busy}
              onChange={(e) => {
                setOwner(e.target.value);
                setSelectedPerson(
                  options.find((p) => p.id === e.target.value) || null,
                );
              }}
            >
              <option value="">미지정</option>
              {options.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.username}
                </option>
              ))}
            </select>
          </label>
          {directoryError && <p role="alert">{directoryError}</p>}
          <div className="triage-paging">
            <button
              type="button"
              disabled={busy || ownerOffset === 0}
              onClick={() => setOwnerOffset((v) => Math.max(0, v - 25))}
            >
              담당자 이전
            </button>
            <span>{people.total}명</span>
            <button
              type="button"
              disabled={busy || !people.has_more}
              onClick={() => setOwnerOffset((v) => v + 25)}
            >
              담당자 다음
            </button>
          </div>
          <label>
            위험 수용 사유
            <textarea
              value={acceptance}
              onChange={(e) => setAcceptance(e.target.value)}
              required={status === "accepted"}
              maxLength={4000}
              rows={3}
              disabled={busy}
            />
          </label>
          <label>
            해결 사유
            <textarea
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              required={status === "resolved"}
              maxLength={4000}
              rows={3}
              disabled={busy}
            />
          </label>
          <p className="subtle">
            수동 해결은 조치 기록입니다. 실제 해결 여부는 승인된 재검증으로
            확인하세요.
          </p>
          {error && (
            <div role="alert">
              <p>{error}</p>
              <button type="button" onClick={onReload} disabled={busy}>
                최신 기록 다시 불러오기
              </button>
              <p className="subtle">
                다시 불러오면 작성 중인 내용은 최신 기록으로 바뀝니다.
              </p>
            </div>
          )}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "저장 중…" : "조치 기록 저장"}
          </button>
        </form>
      ) : (
        <div className="triage-readonly">
          <p>담당자: {finding.assignee_name || "미지정"}</p>
          <p>상태: {statuses[finding.status] || finding.status}</p>
          <p>수용 사유: {finding.acceptance_reason || "없음"}</p>
          <p>해결 사유: {finding.resolution_reason || "없음"}</p>
        </div>
      )}
      <h4 className="detail-heading">변경 이력 · {entries.total}개</h4>
      {historyError && <p role="alert">{historyError}</p>}
      {loading ? (
        <p role="status">이력을 불러오는 중…</p>
      ) : entries.items.length ? (
        <ol className="triage-history">
          {entries.items.map((entry) => (
            <li key={entry.id}>
              <strong>
                {actions[entry.action] || entry.action} · {entry.actor.name}
                {entry.actor.username && ` (${entry.actor.username})`}
              </strong>
              <time>
                {new Date(entry.created_at * 1000).toLocaleString("ko-KR")}
              </time>
              <p>{entry.reason}</p>
              {Object.entries(entry.changes)
                .filter(([key]) => key !== "assignee_id")
                .map(([key, value]) => (
                  <p key={key}>
                    {fields[key] || key}:{" "}
                    {statuses[String(value.before)] ||
                      String(value.before ?? "없음")}{" "}
                    →{" "}
                    {statuses[String(value.after)] ||
                      String(value.after ?? "없음")}
                  </p>
                ))}
            </li>
          ))}
        </ol>
      ) : (
        !historyError && (
          <p className="subtle">
            기록된 변경 이력이 없습니다. 이전 버전의 이력은 소급 생성하지
            않습니다.
          </p>
        )
      )}
      <div className="triage-paging">
        <button
          type="button"
          disabled={loading || offset === 0}
          onClick={() => setOffset((v) => Math.max(0, v - 25))}
        >
          이력 이전
        </button>
        <span>
          {Math.floor(offset / 25) + 1} /{" "}
          {Math.max(1, Math.ceil(entries.total / 25))}
        </span>
        <button
          type="button"
          disabled={loading || !entries.has_more}
          onClick={() => {
            setSnapshot(entries.snapshot);
            setOffset((v) => v + 25);
          }}
        >
          이력 다음
        </button>
      </div>
    </section>
  );
}
