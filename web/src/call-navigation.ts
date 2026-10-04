import type { HistoryMode, ListPosition } from "./navigation-state";
export const CALL_STATES = [
  "started",
  "observed",
  "committed",
  "uncommitted",
  "interrupted",
] as const;
export type CallListState = ListPosition & {
  search: string;
  source: string;
  state: string;
  taskId: string;
};
export type CallListChange = (
  changes: Partial<CallListState>,
  mode?: HistoryMode,
) => void;
function integer(value: string | null, maximum: number) {
  if (!value || !/^\d{1,16}$/.test(value)) return null;
  const number = Number(value);
  return Number.isSafeInteger(number) && number <= maximum ? number : null;
}
export function readCallList(search: string): CallListState {
  const query = new URLSearchParams(search);
  const text = (query.get("llm_calls_q") || "").slice(0, 200);
  const taskId = query.get("llm_calls_task") || "";
  return {
    search: /[\uD800-\uDBFF]$/.test(text) ? text.slice(0, -1) : text,
    source: ["planner", "conversation"].includes(
      query.get("llm_calls_source") || "",
    )
      ? query.get("llm_calls_source")!
      : "",
    state: CALL_STATES.includes(
      query.get("llm_calls_state") as (typeof CALL_STATES)[number],
    )
      ? query.get("llm_calls_state")!
      : "",
    taskId: /^[A-Za-z0-9_-]{1,80}$/.test(taskId) ? taskId : "",
    offset:
      Math.floor(
        (integer(query.get("llm_calls_offset"), 10_000_000) || 0) / 25,
      ) * 25,
    snapshot: integer(query.get("llm_calls_snapshot"), Number.MAX_SAFE_INTEGER),
  };
}
export function updateCallListQuery(
  search: string,
  changes: Partial<CallListState>,
): string {
  const previous = readCallList(search),
    next = { ...previous, ...changes };
  if (
    ["search", "source", "state", "taskId"].some(
      (key) =>
        key in changes &&
        next[key as keyof CallListState] !==
          previous[key as keyof CallListState],
    )
  ) {
    next.offset = 0;
    next.snapshot = null;
  }
  const query = new URLSearchParams(search);
  for (const field of ["q", "source", "state", "task", "offset", "snapshot"])
    query.delete("llm_calls_" + field);
  if (next.search) query.set("llm_calls_q", next.search);
  if (next.source) query.set("llm_calls_source", next.source);
  if (next.state) query.set("llm_calls_state", next.state);
  if (next.taskId) query.set("llm_calls_task", next.taskId);
  if (next.offset) query.set("llm_calls_offset", String(next.offset));
  if (next.snapshot !== null)
    query.set("llm_calls_snapshot", String(next.snapshot));
  // Validate changes as well as bookmarked input.
  const valid = readCallList(query.toString());
  for (const [field, value] of Object.entries({
    q: valid.search,
    source: valid.source,
    state: valid.state,
    task: valid.taskId,
    offset: valid.offset || "",
    snapshot: valid.snapshot,
  })) {
    query.delete("llm_calls_" + field);
    if (value !== null && value !== "")
      query.set("llm_calls_" + field, String(value));
  }
  return query.toString();
}
