import { useState } from "react";
import { useRecords, Pagination, RecordState } from "./records";

type Finding = {
  id: string;
  title: string;
  asset_name: string;
  severity: string;
  status: string;
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
}: {
  taskId: string;
  onFinding: (id: string) => void;
}) {
  return (
    <>
      <TaskCollection taskId={taskId} kind="findings" onFinding={onFinding} />
      <TaskCollection taskId={taskId} kind="events" onFinding={onFinding} />
    </>
  );
}
function TaskCollection({
  taskId,
  kind,
  onFinding,
}: {
  taskId: string;
  kind: "findings" | "events";
  onFinding: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const records = useRecords<Finding | Event>(
    kind,
    search,
    {},
    undefined,
    `/tasks/${encodeURIComponent(taskId)}/${kind}`,
  );
  const name = kind === "findings" ? "작업의 발견 사항" : "작업 실행 기록";
  return (
    <section className="finding-collection" aria-label={name}>
      <h4 className="detail-heading">{name}</h4>
      <label className="task-record-search">
        {kind === "findings"
          ? "발견 제목·자산·심각도·상태로 검색"
          : "메시지·수준으로 검색"}
        <input
          aria-label={`${name} 검색`}
          maxLength={200}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
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
