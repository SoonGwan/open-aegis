export type PendingQuestion = { content: string; request_id: string; mode?: "rules" | "ai" };
type PendingStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
const key = (actorId: string, taskId: string) =>
  "aegis:pending-question:" + JSON.stringify([actorId, taskId]);
function valid(value: unknown): value is PendingQuestion {
  if (!value || typeof value !== "object") return false;
  const pending = value as PendingQuestion;
  return (
    (pending.mode === undefined || pending.mode === "rules" || pending.mode === "ai") &&
    typeof pending.content === "string" &&
    !!pending.content.trim() &&
    pending.content.length <= 2000 &&
    typeof pending.request_id === "string" &&
    /^[a-zA-Z0-9_-]{16,80}$/.test(pending.request_id)
  );
}
export function pendingStorage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}
export function readPending(
  storage: PendingStorage | null,
  actorId: string,
  taskId: string,
): PendingQuestion | null {
  try {
    const raw = storage?.getItem(key(actorId, taskId));
    if (!raw || raw.length > 12000) return null;
    const value = JSON.parse(raw);
    return value.version === 1 && valid(value)
      ? { content: value.content, request_id: value.request_id, ...(value.mode === undefined ? {} : {mode:value.mode}) }
      : null;
  } catch {
    return null;
  }
}
export function writePending(
  storage: PendingStorage | null,
  actorId: string,
  taskId: string,
  pending: PendingQuestion,
): boolean {
  try {
    if (!storage || !valid(pending)) return false;
    storage.setItem(
      key(actorId, taskId),
      JSON.stringify({ version: 1, ...pending }),
    );
    return true;
  } catch {
    return false;
  }
}
export function clearPending(
  storage: PendingStorage | null,
  actorId: string,
  taskId: string,
  requestId: string,
): boolean {
  try {
    const pending = readPending(storage, actorId, taskId);
    if (!storage || pending?.request_id !== requestId) return false;
    storage.removeItem(key(actorId, taskId));
    return true;
  } catch {
    return false;
  }
}
