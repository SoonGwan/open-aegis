import { useCallback } from "react";
import {
  readDetail,
  readTaskCollection,
  type TaskCollectionKind,
  type TaskCollectionState,
  type HistoryMode,
  type ListPosition,
} from "./navigation-state";
import { useRecords, Pagination, RecordState } from "./records";

type Finding = {
  id: string;
  title: string;
  asset_name: string;
  severity: string;
  status: string;
};
type Observation = {
  id: string;
  url: string;
  asset_id: string;
  asset_name?: string | null;
  worker_id?: string;
  check?: string;
  tool_version?: number;
  scope_revision?: number;
  scope_url?: string;
  package_sha256?: string;
  created_at?: number;
  provenance?: { status: string; reason: string };
};
type Event = {
  seq: number;
  ts: number;
  level: string;
  message: string;
  detail: Record<string, unknown>;
};
const severity: Record<string, string> = {
  critical: "치명적",
  high: "높음",
  medium: "보통",
  low: "낮음",
  info: "정보",
};
const status: Record<string, string> = {
  open: "미조치",
  accepted: "위험 수용",
  resolved: "해결됨",
};

export function TaskRecords({
  taskId,
  onFinding,
  collections,
  onChange,
}: {
  taskId: string;
  onFinding: (id: string) => void;
  collections: Record<TaskCollectionKind, TaskCollectionState>;
  onChange: (
    kind: TaskCollectionKind,
    changes: Partial<TaskCollectionState>,
    mode?: HistoryMode,
  ) => void;
}) {
  return (
    <>
      <TaskCollection
        taskId={taskId}
        kind="findings"
        onFinding={onFinding}
        state={collections.findings}
        onChange={onChange}
      />
      <TaskCollection
        taskId={taskId}
        kind="observations"
        onFinding={onFinding}
        state={collections.observations}
        onChange={onChange}
      />
      <TaskCollection
        taskId={taskId}
        kind="events"
        onFinding={onFinding}
        state={collections.events}
        onChange={onChange}
      />
    </>
  );
}
function TaskCollection({
  taskId,
  kind,
  onFinding,
  state,
  onChange,
}: {
  taskId: string;
  kind: TaskCollectionKind;
  onFinding: (id: string) => void;
  state: TaskCollectionState;
  onChange: (
    kind: TaskCollectionKind,
    changes: Partial<TaskCollectionState>,
    mode?: HistoryMode,
  ) => void;
}) {
  const { search } = state;
  const changePosition = useCallback(
    (position: ListPosition, mode?: HistoryMode) => {
      const detail = readDetail(location.search);
      if (
        detail?.kind !== "task" ||
        detail.id !== taskId ||
        JSON.stringify(readTaskCollection(location.search, kind)) !==
          JSON.stringify(state)
      )
        return;
      onChange(kind, position, mode);
    },
    [taskId, kind, state, onChange],
  );
  const records = useRecords<Finding | Event | Observation>(
    kind,
    search,
    {},
    { ...state, onPositionChange: changePosition },
    `/tasks/${encodeURIComponent(taskId)}/${kind}`,
  );
  const name =
    kind === "findings"
      ? "작업의 발견 사항"
      : kind === "observations"
        ? "Worker 관찰 링크"
        : "작업 실행 기록";
  return (
    <section className="finding-collection" aria-label={name}>
      <h4 className="detail-heading">{name}</h4>
      <label className="task-record-search">
        {kind === "findings"
          ? "발견 제목·자산·심각도·상태로 검색"
          : kind === "observations"
            ? "링크·자산·작업으로 검색"
            : "메시지·수준으로 검색"}
        <input
          aria-label={`${name} 검색`}
          maxLength={200}
          value={search}
          onChange={(e) =>
            onChange(kind, { search: e.target.value }, "replace")
          }
        />
      </label>
      {kind === "observations" && (
        <p className="subtle">
          HTML의 범위 내 링크 관찰입니다. 링크를 방문하거나 실행을 승인하지
          않습니다. 출처 일치는 저장된 메타데이터 비교입니다.
        </p>
      )}
      <Pagination records={records} />
      {!records.ready ? (
        <RecordState records={records} />
      ) : records.items.length ? (
        records.items.map((record) =>
          kind === "findings" ? (
            <article className="finding-record" key={(record as Finding).id}>
              <button
                type="button"
                onClick={() => onFinding((record as Finding).id)}
              >
                {(record as Finding).title}
              </button>
              <p>
                {(record as Finding).asset_name} ·{" "}
                {severity[(record as Finding).severity] ||
                  (record as Finding).severity}{" "}
                ·{" "}
                {status[(record as Finding).status] ||
                  (record as Finding).status}
              </p>
            </article>
          ) : kind === "observations" ? (
            <ObservationRecord
              key={(record as Observation).id}
              record={record as Observation}
            />
          ) : (
            <article
              className={`finding-record execution-entry task-event-record ${(record as Event).level}`}
              key={(record as Event).seq}
            >
              <strong>{(record as Event).message}</strong>
              <small>
                {new Date((record as Event).ts * 1000).toLocaleString("ko-KR")}{" "}
                · {(record as Event).level}
              </small>
              {Object.keys((record as Event).detail).length > 0 && (
                <details>
                  <summary>기록 상세</summary>
                  <pre>{JSON.stringify((record as Event).detail, null, 2)}</pre>
                </details>
              )}
            </article>
          ),
        )
      ) : (
        <p className="subtle">
          {search ? "검색 결과가 없습니다." : `${name}이 없습니다.`}
        </p>
      )}
    </section>
  );
}

function ObservationRecord({ record }: { record: Observation }) {
  const matched = record.provenance?.status === "matched";
  return (
    <article className="finding-record">
      <code className="observation-url">{record.url}</code>
      <p>
        {record.asset_name || "자산 기록 없음"} ·{" "}
        {matched ? "출처 메타데이터 일치" : "출처 미확인"}
      </p>
      <small>
        {typeof record.created_at === "number"
          ? new Date(record.created_at * 1000).toLocaleString("ko-KR")
          : "관찰 시각 미확인"}
      </small>
      <p className="subtle">
        {record.provenance?.reason || "관찰 출처를 확인할 수 없습니다."}
      </p>
      <details>
        <summary>관찰 출처 상세</summary>
        <pre>
          {JSON.stringify(
            {
              asset_id: record.asset_id,
              worker_id: record.worker_id ?? null,
              check: record.check ?? null,
              tool_version: record.tool_version ?? null,
              scope_revision: record.scope_revision ?? null,
              scope_url: record.scope_url ?? null,
              package_sha256: record.package_sha256 ?? null,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </article>
  );
}
