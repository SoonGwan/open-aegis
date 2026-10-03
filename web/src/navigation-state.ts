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
];
export type ListPosition = { offset: number; snapshot: number | null };
export type ListState = ListPosition & {
  search: string;
  filter: string;
  archived: boolean;
};
export type NavigationState = { page: string; list: ListState };
export type HistoryMode = "push" | "replace";
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
    severity = query.get(`${page}_severity`);
  return {
    search: searchText(query.get(`${page}_q`)),
    filter:
      page === "tasks" &&
      TASK_STATUSES.includes(status as (typeof TASK_STATUSES)[number])
        ? status!
        : page === "findings" && severities.includes(severity || "")
          ? severity!
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
  ])
    query.delete(`${page}_${suffix}`);
  if (state.search) query.set(`${page}_q`, searchText(state.search));
  if (page === "tasks" && state.filter !== "all")
    query.set("tasks_status", state.filter);
  if (page === "findings" && state.filter !== "all")
    query.set("findings_severity", state.filter);
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
): string {
  const query = new URLSearchParams(search);
  const target = allowedPages.includes(page) ? page : "overview";
  query.set("page", target);
  writeList(query, target, fresh ? defaultList() : readList(query, target));
  return query.toString();
}
