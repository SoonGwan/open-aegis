import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import Modal from "./components/Modal";
import { Pagination, RecordState, useRecords } from "./records";

export type ArchivableTask = {
  id: string;
  name: string;
  status: string;
  archived_at?: number | null;
  archive_revision?: number;
};
export const canArchive = (task: ArchivableTask) =>
  ["completed", "failed", "stopped", "interrupted", "rejected"].includes(
    task.status,
  );

export function TaskArchiveDialog({
  tasks,
  archived,
  onClose,
  onSaved,
}: {
  tasks: ArchivableTask[];
  archived: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const mounted = useRef(true),
    pending = useRef(false);
  const request = useRef({
    task_ids: tasks.map((task) => task.id),
    expected_revisions: Object.fromEntries(
      tasks.map((task) => [task.id, task.archive_revision || 0]),
    ),
    archived,
    request_id: crypto.randomUUID(),
  });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function save() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await api("/tasks/archive-assignment", "POST", request.current);
      if (mounted.current) {
        window.dispatchEvent(new Event("aegis-records-changed"));
        onSaved();
        onClose();
      }
    } catch (cause) {
      if (mounted.current)
        setError(
          cause instanceof Error
            ? cause.message
            : "저장하지 못했습니다. 다시 시도하세요.",
        );
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={archived ? "작업 보관" : "작업 복원"}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <p>
        {tasks.length}개 종료 작업의 목록 위치를{" "}
        {archived ? "보관함으로 옮깁니다" : "일반 목록으로 복원합니다"}. 실행
        결과·증거·승인 기록은 보존됩니다.
      </p>
      <ul>
        {tasks.map((task) => (
          <li key={task.id}>
            {task.name} · 보관 변경 버전 {task.archive_revision || 0}
          </li>
        ))}
      </ul>
      <p>
        응답을 받지 못하면 같은 요청으로 다시 시도할 수 있습니다. 버전이
        충돌하면 창을 닫고 선택을 해제한 뒤 현재 작업을 다시 선택하세요.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="modal-actions">
        <button disabled={busy} onClick={onClose}>
          취소
        </button>
        <button className="primary" disabled={busy} onClick={() => void save()}>
          {busy ? "저장 중…" : archived ? "보관하기" : "복원하기"}
        </button>
      </div>
    </Modal>
  );
}

function HistoryRows({ taskId }: { taskId: string }) {
  const records = useRecords<{
    id: string;
    revision: number;
    archived: boolean;
    actor: { name: string };
    created_at: number;
  }>(
    "task-archive-history",
    "",
    {},
    undefined,
    `/tasks/${taskId}/archive-history`,
  );
  return (
    <>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          {!records.items.length && <p>보관 변경 이력이 없습니다.</p>}
          <ul className="template-history">
            {records.items.map((row) => (
              <li key={row.id}>
                <strong>
                  {row.archived ? "보관" : "복원"} · 버전 {row.revision}
                </strong>
                <p>
                  {row.actor.name} ·{" "}
                  {new Date(row.created_at * 1000).toLocaleString("ko-KR")}
                </p>
              </li>
            ))}
          </ul>
          <Pagination records={records} />
        </>
      )}
    </>
  );
}
export function TaskArchiveHistory({ taskId }: { taskId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="detail-section">
      <button aria-expanded={open} onClick={() => setOpen(!open)}>
        작업 보관 이력 {open ? "접기" : "보기"}
      </button>
      {open && <HistoryRows taskId={taskId} />}
    </section>
  );
}
