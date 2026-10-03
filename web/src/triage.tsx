import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useRecords, Pagination, RecordState } from "./records";
import {
  readDetail,
  readFindingCollection,
  type FindingCollectionKind,
  type FindingCollectionState,
  type HistoryMode,
  type ListPosition,
} from "./navigation-state";

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
  historyState,
  onHistoryChange,
}: {
  finding: TriageFinding;
  canOperate: boolean;
  onUpdated: (value: TriageFinding) => void;
  onReload: () => void;
  historyState: FindingCollectionState;
  onHistoryChange: (
    kind: FindingCollectionKind,
    changes: Partial<FindingCollectionState>,
    mode?: HistoryMode,
  ) => void;
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
  const [error, setError] = useState("");
  const [directoryError, setDirectoryError] = useState("");
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
      <FindingHistory
        findingId={finding.id}
        state={historyState}
        onChange={onHistoryChange}
      />
    </section>
  );
}

function FindingHistory({
  findingId,
  state,
  onChange,
}: {
  findingId: string;
  state: FindingCollectionState;
  onChange: (
    kind: FindingCollectionKind,
    changes: Partial<FindingCollectionState>,
    mode?: HistoryMode,
  ) => void;
}) {
  const { search, expanded } = state;
  const changePosition = useCallback(
    (position: ListPosition, mode?: HistoryMode) => {
      const detail = readDetail(location.search);
      if (
        detail?.kind !== "finding" ||
        detail.id !== findingId ||
        JSON.stringify(readFindingCollection(location.search, "history")) !==
          JSON.stringify(state)
      )
        return;
      onChange("history", position, mode);
    },
    [findingId, state, onChange],
  );
  const records = useRecords<History>(
    expanded ? "finding_history" : null,
    search,
    {},
    { ...state, onPositionChange: changePosition },
    `/findings/${encodeURIComponent(findingId)}/history`,
  );
  return (
    <section className="finding-collection" aria-label="발견 사항 변경 이력">
      <h4 className="detail-heading">변경 이력</h4>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => onChange("history", { expanded: !expanded })}
      >
        {expanded ? "변경 이력 접기" : "변경 이력 보기"}
      </button>
      {expanded && (
        <div className="finding-collection-content">
          <label>
            사유·작성자로 검색
            <input
              aria-label="변경 이력 검색"
              maxLength={200}
              value={search}
              onChange={(event) =>
                onChange("history", { search: event.target.value }, "replace")
              }
            />
          </label>
          <Pagination records={records} />
          {!records.ready ? (
            <RecordState records={records} />
          ) : records.items.length ? (
            <ol className="triage-history">
              {records.items.map((entry) => (
                <li key={entry.id}>
                  <strong>
                    {actions[entry.action] || entry.action} · {entry.actor.name}
                    {entry.actor.username && ` (${entry.actor.username})`}
                  </strong>
                  <time
                    dateTime={new Date(entry.created_at * 1000).toISOString()}
                  >
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
            <p className="subtle">
              {search
                ? "검색 결과가 없습니다."
                : "기록된 변경 이력이 없습니다. 이전 버전의 이력은 소급 생성하지 않습니다."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
