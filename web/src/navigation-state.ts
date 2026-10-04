/** URL state is data: only reviewed filters and bounded integer positions reach the API. */
export const TASK_STATUSES = [
  "pending",
  "queued",
  "running",
  "stopping",
  "completed",
  "failed",
  "stopped",
  "interrupted",
  "rejected",
] as const;
const severities = ["critical", "high", "medium", "low", "info"];
export const LIST_PAGES = [
  "assets",
  "tasks",
  "findings",
  "traffic",
  "approvals",
  "reports",
  "notes",
  "schedules",
  "observations",
];
export type ListPosition = { offset: number; snapshot: number | null };
export type ListState = ListPosition & {
  search: string;
  filter: string;
  archived: boolean;
};
export type NavigationState = { page: string; list: ListState };
export type HistoryMode = "push" | "replace";
export type DetailState = { kind: "task" | "finding"; id: string };
export function readDetail(search: string): DetailState | null {
  const query = new URLSearchParams(search);
  const kind = query.get("detail"),
    id = query.get("detail_id");
  return (kind === "task" || kind === "finding") &&
    id &&
    /^[A-Za-z0-9_-]{1,80}$/.test(id)
    ? { kind, id }
    : null;
}
export function detailQuery(
  search: string,
  detail: DetailState | null,
): string {
  const query = new URLSearchParams(search);
  const previous = readDetail(search);
  if (
    detail?.kind !== "task" ||
    previous?.kind !== "task" ||
    previous.id !== detail.id
  )
    clearTaskCollections(query);
  if (
    detail?.kind !== "finding" ||
    previous?.kind !== "finding" ||
    previous.id !== detail.id
  )
    clearFindingCollections(query);
  query.delete("detail");
  query.delete("detail_id");
  if (detail) {
    query.set("detail", detail.kind);
    query.set("detail_id", detail.id);
  }
  const valid = readDetail(query.toString());
  if (!valid) {
    query.delete("detail");
    query.delete("detail_id");
  }
  if (valid?.kind === "finding") {
    for (const kind of findingCollectionKinds)
      writeFindingCollection(
        query,
        kind,
        readFindingCollection(query.toString(), kind),
      );
  } else clearFindingCollections(query);
  if (valid?.kind === "task") {
    for (const kind of taskCollectionKinds)
      writeTaskCollection(
        query,
        kind,
        readTaskCollection(query.toString(), kind),
      );
    writeTaskChat(query, readTaskChat(query.toString()));
    writeTaskWorker(query, readTaskWorker(query.toString()));
  } else clearTaskCollections(query);
  return query.toString();
}
export const taskCollectionKinds = ["findings", "events", "observations"] as const;
export type TaskCollectionKind = (typeof taskCollectionKinds)[number];
export type TaskCollectionState = ListPosition & { search: string };
function clearTaskCollections(query: URLSearchParams) {
  clearTaskWorker(query);
  for (const kind of taskCollectionKinds)
    for (const field of ["q", "offset", "snapshot"])
      query.delete(`task_${kind}_${field}`);
  for (const field of ["q", "open", "offset", "snapshot"])
    query.delete(`task_chat_${field}`);
}
export type TaskWorkerState = {
  assetId: string;
  expanded: boolean;
  events: TaskCollectionState;
  observations: TaskCollectionState;
};
function clearTaskWorker(query: URLSearchParams) {
  query.delete("task_worker_asset");
  query.delete("task_worker_open");
  for (const kind of ["events", "observations"])
    for (const field of ["q", "offset", "snapshot"])
      query.delete(`task_worker_${kind}_${field}`);
}
export function readTaskWorker(search: string): TaskWorkerState {
  const query = new URLSearchParams(search);
  const value = query.get("task_worker_asset") || "";
  const assetId = readDetail(search)?.kind === "task" && /^[A-Za-z0-9_-]{1,80}$/.test(value) ? value : "";
  const collection = (kind: string): TaskCollectionState => ({
    search: assetId ? searchText(query.get(`task_worker_${kind}_q`)) : "",
    offset: assetId ? Math.floor((integer(query.get(`task_worker_${kind}_offset`), 10_000_000) || 0) / 25) * 25 : 0,
    snapshot: assetId ? integer(query.get(`task_worker_${kind}_snapshot`), Number.MAX_SAFE_INTEGER) : null,
  });
  return { assetId, expanded: Boolean(assetId) && query.get("task_worker_open") === "true",
    events: collection("events"), observations: collection("observations") };
}
function writeTaskWorker(query: URLSearchParams, state: TaskWorkerState) {
  clearTaskWorker(query);
  if (!state.assetId) return;
  query.set("task_worker_asset", state.assetId);
  if (state.expanded) query.set("task_worker_open", "true");
  for (const kind of ["events", "observations"] as const) {
    const row = state[kind], prefix = `task_worker_${kind}_`;
    if (row.search) query.set(prefix + "q", searchText(row.search));
    if (row.offset) query.set(prefix + "offset", String(row.offset));
    if (row.snapshot !== null) query.set(prefix + "snapshot", String(row.snapshot));
  }
}
export function updateTaskWorkerQuery(search: string, changes: Partial<TaskWorkerState>): string {
  const detail = readDetail(search);
  if (detail?.kind !== "task") return detailQuery(search, detail);
  const query = new URLSearchParams(search), previous = readTaskWorker(search);
  const next = { ...previous, ...changes };
  if (next.assetId !== previous.assetId) {
    next.expanded = false;
    next.events = { search: "", offset: 0, snapshot: null };
    next.observations = { search: "", offset: 0, snapshot: null };
  } else for (const kind of ["events", "observations"] as const) {
    if (next[kind].search !== previous[kind].search) next[kind] = { ...next[kind], offset: 0, snapshot: null };
  }
  writeTaskWorker(query, next);
  return detailQuery(query.toString(), detail);
}
export type TaskChatState = TaskCollectionState & { expanded: boolean };
export function readTaskChat(search: string): TaskChatState {
  const query = new URLSearchParams(search);
  if (readDetail(search)?.kind !== "task")
    return { search: "", expanded: false, offset: 0, snapshot: null };
  return {
    search: searchText(query.get("task_chat_q")),
    expanded: query.get("task_chat_open") === "true",
    offset:
      Math.floor(
        (integer(query.get("task_chat_offset"), 10_000_000) || 0) / 25,
      ) * 25,
    snapshot: integer(query.get("task_chat_snapshot"), Number.MAX_SAFE_INTEGER),
  };
}
function writeTaskChat(query: URLSearchParams, state: TaskChatState) {
  for (const field of ["q", "open", "offset", "snapshot"])
    query.delete(`task_chat_${field}`);
  if (state.search) query.set("task_chat_q", searchText(state.search));
  if (state.expanded) query.set("task_chat_open", "true");
  if (state.offset) query.set("task_chat_offset", String(state.offset));
  if (state.snapshot !== null)
    query.set("task_chat_snapshot", String(state.snapshot));
}
export function updateTaskChatQuery(
  search: string,
  changes: Partial<TaskChatState>,
): string {
  const detail = readDetail(search);
  if (detail?.kind !== "task") return detailQuery(search, detail);
  const query = new URLSearchParams(search);
  const previous = readTaskChat(search);
  const next = { ...previous, ...changes };
  if ("search" in changes && changes.search !== previous.search) {
    next.offset = 0;
    next.snapshot = null;
  }
  writeTaskChat(query, next);
  return detailQuery(query.toString(), detail);
}
export function readTaskCollection(
  search: string,
  kind: TaskCollectionKind,
): TaskCollectionState {
  const query = new URLSearchParams(search);
  if (readDetail(search)?.kind !== "task")
    return { search: "", offset: 0, snapshot: null };
  const prefix = `task_${kind}_`;
  return {
    search: searchText(query.get(prefix + "q")),
    offset:
      Math.floor(
        (integer(query.get(prefix + "offset"), 10_000_000) || 0) / 25,
      ) * 25,
    snapshot: integer(query.get(prefix + "snapshot"), Number.MAX_SAFE_INTEGER),
  };
}
function writeTaskCollection(
  query: URLSearchParams,
  kind: TaskCollectionKind,
  state: TaskCollectionState,
) {
  const prefix = `task_${kind}_`;
  for (const field of ["q", "offset", "snapshot"]) query.delete(prefix + field);
  if (state.search) query.set(prefix + "q", searchText(state.search));
  if (state.offset) query.set(prefix + "offset", String(state.offset));
  if (state.snapshot !== null)
    query.set(prefix + "snapshot", String(state.snapshot));
}
export function updateTaskCollectionQuery(
  search: string,
  kind: TaskCollectionKind,
  changes: Partial<TaskCollectionState>,
): string {
  const detail = readDetail(search);
  if (detail?.kind !== "task") return detailQuery(search, detail);
  const query = new URLSearchParams(search);
  const previous = readTaskCollection(search, kind);
  const next = { ...previous, ...changes };
  if ("search" in changes && changes.search !== previous.search) {
    next.offset = 0;
    next.snapshot = null;
  }
  writeTaskCollection(query, kind, next);
  return detailQuery(query.toString(), detail);
}
export const findingCollectionKinds = [
  "evidence",
  "retests",
  "history",
] as const;
export type FindingCollectionKind = (typeof findingCollectionKinds)[number];
export type FindingCollectionState = ListPosition & {
  search: string;
  expanded: boolean;
};
function clearFindingCollections(query: URLSearchParams) {
  for (const kind of findingCollectionKinds)
    for (const field of ["q", "open", "offset", "snapshot"])
      query.delete(`finding_${kind}_${field}`);
}
export function readFindingCollection(
  search: string,
  kind: FindingCollectionKind,
): FindingCollectionState {
  const query = new URLSearchParams(search);
  if (readDetail(search)?.kind !== "finding")
    return { search: "", expanded: false, offset: 0, snapshot: null };
  const prefix = `finding_${kind}_`;
  return {
    search: searchText(query.get(prefix + "q")),
    expanded: query.get(prefix + "open") === "true",
    offset:
      Math.floor(
        (integer(query.get(prefix + "offset"), 10_000_000) || 0) / 25,
      ) * 25,
    snapshot: integer(query.get(prefix + "snapshot"), Number.MAX_SAFE_INTEGER),
  };
}
function writeFindingCollection(
  query: URLSearchParams,
  kind: FindingCollectionKind,
  state: FindingCollectionState,
) {
  const prefix = `finding_${kind}_`;
  for (const field of ["q", "open", "offset", "snapshot"])
    query.delete(prefix + field);
  if (state.search) query.set(prefix + "q", state.search);
  if (state.expanded) query.set(prefix + "open", "true");
  if (state.offset) query.set(prefix + "offset", String(state.offset));
  if (state.snapshot !== null)
    query.set(prefix + "snapshot", String(state.snapshot));
}
export function updateFindingCollectionQuery(
  search: string,
  kind: FindingCollectionKind,
  changes: Partial<FindingCollectionState>,
): string {
  if (readDetail(search)?.kind !== "finding")
    return detailQuery(search, readDetail(search));
  const query = new URLSearchParams(search);
  const previous = readFindingCollection(search, kind);
  const next = { ...previous, ...changes };
  if ("search" in changes && changes.search !== previous.search) {
    next.offset = 0;
    next.snapshot = null;
  }
  writeFindingCollection(query, kind, next);
  return detailQuery(query.toString(), readDetail(search));
}
export const defaultList = (): ListState => ({
  search: "",
  filter: "all",
  archived: false,
  offset: 0,
  snapshot: null,
});
function integer(raw: string | null, maximum: number): number | null {
  if (raw === null || !/^\d{1,16}$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) && value <= maximum ? value : null;
}
function searchText(raw: string | null) {
  const value = (raw || "").slice(0, 200);
  // Do not split a surrogate pair when bounding a pasted/bookmarked query.
  return /[\uD800-\uDBFF]$/.test(value) ? value.slice(0, -1) : value;
}
export function readList(query: URLSearchParams, page: string): ListState {
  if (!LIST_PAGES.includes(page)) return defaultList();
  const status = query.get(`${page}_status`),
    severity = query.get(`${page}_severity`),
    enabled = query.get("schedules_enabled");
  return {
    search: searchText(query.get(`${page}_q`)),
    filter:
      page === "tasks" &&
      TASK_STATUSES.includes(status as (typeof TASK_STATUSES)[number])
        ? status!
        : page === "findings" && severities.includes(severity || "")
          ? severity!
          : page === "schedules" && ["true", "false"].includes(enabled || "")
            ? enabled!
            : "all",
    archived: page === "assets" && query.get("assets_archived") === "true",
    offset:
      Math.floor((integer(query.get(`${page}_offset`), 10_000_000) || 0) / 25) *
      25,
    snapshot: integer(query.get(`${page}_snapshot`), Number.MAX_SAFE_INTEGER),
  };
}
export function readNavigation(
  search: string,
  allowedPages: readonly string[],
): NavigationState {
  const query = new URLSearchParams(search);
  const requested = query.get("page");
  const page =
    requested && allowedPages.includes(requested) ? requested : "overview";
  return { page, list: readList(query, page) };
}
export function writeList(
  query: URLSearchParams,
  page: string,
  state: ListState,
) {
  if (!LIST_PAGES.includes(page)) return;
  for (const suffix of [
    "q",
    "status",
    "severity",
    "archived",
    "offset",
    "snapshot",
    "enabled",
  ])
    query.delete(`${page}_${suffix}`);
  if (state.search) query.set(`${page}_q`, searchText(state.search));
  if (page === "tasks" && state.filter !== "all")
    query.set("tasks_status", state.filter);
  if (page === "findings" && state.filter !== "all")
    query.set("findings_severity", state.filter);
  if (page === "schedules" && state.filter !== "all")
    query.set("schedules_enabled", state.filter);
  if (page === "assets" && state.archived) query.set("assets_archived", "true");
  if (state.offset) query.set(`${page}_offset`, String(state.offset));
  if (state.snapshot !== null)
    query.set(`${page}_snapshot`, String(state.snapshot));
}
export function updateListQuery(
  search: string,
  allowedPages: readonly string[],
  changes: Partial<ListState>,
): string {
  const query = new URLSearchParams(search);
  const current = readNavigation(search, allowedPages);
  const state = { ...current.list, ...changes };
  if (
    ("search" in changes && changes.search !== current.list.search) ||
    ("filter" in changes && changes.filter !== current.list.filter) ||
    ("archived" in changes && changes.archived !== current.list.archived)
  ) {
    state.offset = 0;
    state.snapshot = null;
  }
  query.set("page", current.page);
  writeList(query, current.page, state);
  // Normalize caller-supplied changes with the same contract as bookmarks.
  writeList(query, current.page, readList(query, current.page));
  return query.toString();
}
export function navigateQuery(
  search: string,
  allowedPages: readonly string[],
  page: string,
  fresh = false,
  preserveDetail = false,
): string {
  const query = new URLSearchParams(search);
  const target = allowedPages.includes(page) ? page : "overview";
  query.set("page", target);
  writeList(query, target, fresh ? defaultList() : readList(query, target));
  return detailQuery(
    query.toString(),
    preserveDetail ? readDetail(search) : null,
  );
}
