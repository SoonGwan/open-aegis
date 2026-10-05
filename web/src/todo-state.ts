export type TodoStatus = "open" | "in_progress" | "done" | "cancelled";
export type Todo = {
  automatic_origin?:{format:string;source_task_id:string;root_task_id:string;cells:{observation_id:string;check:string}[];fingerprint:string};
  id: string;
  task_id: string;
  revision: number;
  title: string;
  description: string;
  status: TodoStatus;
  assignee_id: string | null;
  assignee_name: string | null;
  assignee_username: string | null;
  resolution_note: string;
  check_ids?: string[];
};
export type TodoDraft = Pick<
  Todo,
  "title" | "description" | "status" | "assignee_id" | "resolution_note"
> & { check_ids: string[] };
export type TodoCreation = Pick<
  TodoDraft,
  "title" | "description" | "assignee_id"
> & { request_id: string; check_ids?: string[] };
export const draftOf = (row: Todo): TodoDraft => ({
  title: row.title,
  description: row.description,
  status: row.status,
  assignee_id: row.assignee_id,
  resolution_note: row.resolution_note,
  check_ids: row.check_ids || [],
});
const fields = [
  "title",
  "description",
  "status",
  "assignee_id",
  "resolution_note",
  "check_ids",
] as const;
/** Only apply deliberate local edits; preserve unrelated changes made by other people. */
export function changesOf(
  base: TodoDraft,
  draft: TodoDraft,
): Partial<TodoDraft> {
  const changes: Partial<TodoDraft> = Object.fromEntries(
    fields
      .filter((key) =>
        key === "check_ids"
          ? JSON.stringify([...base.check_ids].sort()) !==
            JSON.stringify([...draft.check_ids].sort())
          : base[key] !== draft[key],
      )
      .map((key) => [key, draft[key]]),
  );
  if (
    base.status !== draft.status &&
    (draft.status === "done" || draft.status === "cancelled")
  )
    changes.resolution_note = draft.resolution_note;
  return changes;
}
export function rebaseDraft(
  base: TodoDraft,
  draft: TodoDraft,
  latest: Todo,
): TodoDraft {
  return { ...draftOf(latest), ...changesOf(base, draft) };
}
type PendingStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
const key = (actor: string, task: string) =>
  "aegis:pending-todo:" + JSON.stringify([actor, task]);
function valid(value: unknown): value is TodoCreation {
  if (!value || typeof value !== "object") return false;
  const p = value as TodoCreation;
  return (
    typeof p.title === "string" &&
    !!p.title.trim() &&
    p.title.length <= 200 &&
    typeof p.description === "string" &&
    p.description.length <= 4000 &&
    (p.assignee_id === null ||
      (typeof p.assignee_id === "string" &&
        p.assignee_id.length > 0 &&
        p.assignee_id.length <= 80)) &&
    (p.check_ids === undefined ||
      (Array.isArray(p.check_ids) &&
        p.check_ids.length <= 6 &&
        new Set(p.check_ids).size === p.check_ids.length &&
        p.check_ids.every(
          (id) => typeof id === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(id),
        ))) &&
    typeof p.request_id === "string" &&
    /^[a-f0-9]{32}$/.test(p.request_id)
  );
}
export function readTodoPending(
  storage: PendingStorage | null,
  actor: string,
  task: string,
): TodoCreation | null {
  try {
    const raw = storage?.getItem(key(actor, task));
    if (!raw || raw.length > 30000) return null;
    const p = JSON.parse(raw);
    return p.version === 1 && valid(p)
      ? {
          title: p.title,
          description: p.description,
          assignee_id: p.assignee_id,
          request_id: p.request_id,
          ...(p.check_ids === undefined ? {} : { check_ids: p.check_ids }),
        }
      : null;
  } catch {
    return null;
  }
}
export function writeTodoPending(
  storage: PendingStorage | null,
  actor: string,
  task: string,
  value: TodoCreation,
): boolean {
  try {
    if (!storage || !valid(value)) return false;
    storage.setItem(key(actor, task), JSON.stringify({ ...value, version: 1 }));
    return true;
  } catch {
    return false;
  }
}
export function clearTodoPending(
  storage: PendingStorage | null,
  actor: string,
  task: string,
  requestId: string,
): boolean {
  try {
    if (
      !storage ||
      readTodoPending(storage, actor, task)?.request_id !== requestId
    )
      return false;
    storage.removeItem(key(actor, task));
    return true;
  } catch {
    return false;
  }
}
