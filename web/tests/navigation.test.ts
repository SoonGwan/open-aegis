import { test } from "node:test";
import assert from "node:assert/strict";
import {
  readNavigation,
  updateListQuery,
  navigateQuery,
} from "../src/navigation-state.ts";
const pages = [
  "overview",
  "assets",
  "tasks",
  "findings",
  "traffic",
  "approvals",
  "reports",
  "graph",
  "settings",
  "notes",
  "schedules",
  "observations",
];

test("a bookmarked query restores search, filter and insertion watermark", () => {
  const state = readNavigation(
    "?page=findings&findings_q=CSP+검토&findings_severity=low&findings_offset=50&findings_snapshot=12345",
    pages,
  );
  assert.deepEqual(state, {
    page: "findings",
    list: {
      search: "CSP 검토",
      filter: "low",
      archived: false,
      offset: 50,
      snapshot: 12345,
    },
  });
});
test("screen scopes preserve each other and graph links", () => {
  const original =
    "page=assets&assets_q=한글&assets_archived=true&assets_offset=25&assets_snapshot=80&tasks_q=retry&tasks_status=failed&tasks_offset=50&tasks_snapshot=120&graph_asset=asset-1&graph_node=evidence%3Aproof-1";
  const tasks = navigateQuery(original, pages, "tasks");
  assert.equal(readNavigation(tasks, pages).list.offset, 50);
  assert.equal(readNavigation(tasks, pages).list.filter, "failed");
  const back = navigateQuery(tasks, pages, "assets");
  assert.deepEqual(readNavigation(back, pages).list, {
    search: "한글",
    filter: "all",
    archived: true,
    offset: 25,
    snapshot: 80,
  });
  assert.equal(new URLSearchParams(back).get("graph_node"), "evidence:proof-1");
});
test("changing search, status, or archive starts a new first page", () => {
  const initial =
    "page=tasks&tasks_q=old&tasks_status=failed&tasks_offset=50&tasks_snapshot=99";
  const query = updateListQuery(initial, pages, { search: "new" });
  assert.deepEqual(readNavigation(query, pages).list, {
    search: "new",
    filter: "failed",
    archived: false,
    offset: 0,
    snapshot: null,
  });
  const filtered = updateListQuery(initial, pages, { filter: "queued" });
  assert.equal(readNavigation(filtered, pages).list.filter, "queued");
  assert.equal(readNavigation(filtered, pages).list.offset, 0);
  const archived = updateListQuery(
    "page=assets&assets_offset=25&assets_snapshot=99",
    pages,
    { archived: true },
  );
  assert.equal(readNavigation(archived, pages).list.archived, true);
  assert.equal(readNavigation(archived, pages).list.snapshot, null);
});
test("pagination and mutation refresh preserve search and fixed filters", () => {
  const initial = "page=tasks&tasks_q=retry&tasks_status=interrupted";
  const second = updateListQuery(initial, pages, { offset: 25, snapshot: 901 });
  assert.equal(readNavigation(second, pages).list.search, "retry");
  assert.equal(readNavigation(second, pages).list.filter, "interrupted");
  const latest = updateListQuery(second, pages, { snapshot: null });
  assert.equal(readNavigation(latest, pages).list.offset, 25);
  assert.equal(readNavigation(latest, pages).list.snapshot, null);
});
test("new-plan navigation opens a fresh approval list without clearing other screens", () => {
  const initial =
    "page=tasks&tasks_q=incident&tasks_offset=25&approvals_q=old&approvals_offset=75&approvals_snapshot=10";
  const fresh = navigateQuery(initial, pages, "approvals", true);
  assert.deepEqual(readNavigation(fresh, pages).list, {
    search: "",
    filter: "all",
    archived: false,
    offset: 0,
    snapshot: null,
  });
  assert.equal(new URLSearchParams(fresh).get("tasks_q"), "incident");
});
test("malformed pages, filters, and integer positions cannot reach list requests", () => {
  assert.equal(readNavigation("page=not-a-page", pages).page, "overview");
  for (const raw of [
    "-25",
    "NaN",
    "Infinity",
    "1e5",
    "25.5",
    "10000001",
    "999999999999999999999",
  ]) {
    assert.equal(
      readNavigation("page=tasks&tasks_offset=" + raw, pages).list.offset,
      0,
    );
  }
  for (const raw of ["-1", "1.25", "NaN", "9007199254740992"]) {
    assert.equal(
      readNavigation("page=tasks&tasks_snapshot=" + raw, pages).list.snapshot,
      null,
    );
  }
  assert.equal(
    readNavigation("page=tasks&tasks_offset=49", pages).list.offset,
    25,
  );
  assert.equal(
    readNavigation("page=tasks&tasks_snapshot=0", pages).list.snapshot,
    0,
  );
  assert.equal(
    readNavigation(
      "page=findings&findings_severity=script&findings_status=failed",
      pages,
    ).list.filter,
    "all",
  );
  assert.equal(
    readNavigation("page=tasks&tasks_status=stopping", pages).list.filter,
    "stopping",
  );
  assert.equal(
    readNavigation("page=assets&assets_archived=yes", pages).list.archived,
    false,
  );
});
test("literal Unicode and URL punctuation round-trip; long search cannot split a surrogate", () => {
  const search = "계정 + & % _ ' OR 1=1 😀";
  assert.equal(
    readNavigation(updateListQuery("page=assets", pages, { search }), pages)
      .list.search,
    search,
  );
  const bounded = readNavigation(
    updateListQuery("page=assets", pages, { search: "a".repeat(199) + "😀" }),
    pages,
  ).list.search;
  assert.equal(bounded, "a".repeat(199));
});
test("canonicalization drops defaults and normalizes invalid bookmarked inputs", () => {
  const query = navigateQuery(
    "page=tasks&tasks_status=INVALID&tasks_offset=26&tasks_snapshot=-1&tasks_q=abc&unrelated=keep",
    pages,
    "tasks",
  );
  const parsed = new URLSearchParams(query);
  assert.equal(parsed.get("tasks_offset"), "25");
  assert.equal(parsed.has("tasks_status"), false);
  assert.equal(parsed.has("tasks_snapshot"), false);
  assert.equal(parsed.get("unrelated"), "keep");
});

test("notes and schedule bookmarks preserve nested-list filters independently", () => {
  const notes = updateListQuery("page=notes", pages, {
    search: "복구 메모",
    offset: 25,
    snapshot: 90,
  });
  // Search changes always reset a previous position; a later page move retains it.
  const notePage = updateListQuery(notes, pages, { offset: 25, snapshot: 90 });
  const schedules = updateListQuery(
    navigateQuery(notePage, pages, "schedules"),
    pages,
    { filter: "false", search: "주간 검증" },
  );
  assert.equal(
    new URLSearchParams(schedules).get("schedules_enabled"),
    "false",
  );
  assert.equal(readNavigation(schedules, pages).list.filter, "false");
  assert.equal(
    readNavigation(navigateQuery(schedules, pages, "notes"), pages).list.offset,
    25,
  );
  assert.equal(
    readNavigation("page=schedules&schedules_enabled=maybe", pages).list.filter,
    "all",
  );
});

test("observation bookmarks restore independently from the asset preview", () => {
  const original =
    "page=observations&observations_q=포털&observations_offset=25&observations_snapshot=701&assets_q=운영&assets_offset=50";
  assert.equal(readNavigation(original, pages).list.offset, 25);
  const assets = navigateQuery(original, pages, "assets");
  assert.equal(readNavigation(assets, pages).list.offset, 50);
  const restored = navigateQuery(assets, pages, "observations");
  assert.equal(readNavigation(restored, pages).list.search, "포털");
  const fresh = navigateQuery(assets, pages, "observations", true);
  assert.equal(readNavigation(fresh, pages).list.search, "");
  assert.equal(readNavigation(fresh, pages).list.snapshot, null);
});

test("detail bookmarks preserve the source list and close without losing its position", async () => {
  const { readDetail, detailQuery } =
    await import("../src/navigation-state.ts");
  const original =
    "page=tasks&tasks_q=loopback&tasks_status=completed&tasks_offset=25&tasks_snapshot=99&graph_task=source";
  const task = detailQuery(original, { kind: "task", id: "task-123" });
  assert.deepEqual(readDetail(task), { kind: "task", id: "task-123" });
  assert.deepEqual(
    readNavigation(task, pages),
    readNavigation(original, pages),
  );
  const finding = detailQuery(task, { kind: "finding", id: "finding_123" });
  assert.deepEqual(readDetail(finding), { kind: "finding", id: "finding_123" });
  assert.equal(new URLSearchParams(finding).get("graph_task"), "source");
  assert.equal(detailQuery(finding, null), original);
  assert.equal(readDetail(navigateQuery(task, pages, "findings")), null);
  assert.deepEqual(
    readDetail(navigateQuery(task, pages, "tasks", false, true)),
    readDetail(task),
  );
});

test("malformed detail IDs cannot become API paths; canonicalization removes invalid bookmarks", async () => {
  const { readDetail, detailQuery } =
    await import("../src/navigation-state.ts");
  for (const id of [
    "",
    "../private",
    "task/id",
    "task?x=1",
    "한글",
    "x".repeat(81),
  ]) {
    const input = new URLSearchParams({
      page: "tasks",
      detail: "task",
      detail_id: id,
    }).toString();
    assert.equal(readDetail(input), null);
    assert.equal(
      new URLSearchParams(
        navigateQuery(input, pages, "tasks", false, true),
      ).has("detail_id"),
      false,
    );
  }
  assert.equal(readDetail("detail=traffic&detail_id=id"), null);
  assert.equal(readDetail("detail=task"), null);
  assert.equal(readDetail("detail_id=id"), null);
  assert.equal(
    readDetail(detailQuery("page=tasks", { kind: "task", id: "/invalid" })),
    null,
  );
  assert.deepEqual(readDetail("detail=finding&detail_id=" + "a".repeat(80)), {
    kind: "finding",
    id: "a".repeat(80),
  });
});

test("template bookmarks restore archive/search/page and preserve task navigation", () => {
  const allowed=[...pages,"templates"];
  const original="page=templates&templates_status=archived&templates_q=배포&templates_offset=25&templates_snapshot=500&tasks_status=failed&tasks_offset=50";
  const state=readNavigation(original,allowed);
  assert.equal(state.list.filter,"archived");assert.equal(state.list.search,"배포");assert.equal(state.list.offset,25);assert.equal(state.list.snapshot,500);
  const tasks=navigateQuery(original,allowed,"tasks");assert.equal(readNavigation(tasks,allowed).list.filter,"failed");
  const back=navigateQuery(tasks,allowed,"templates");assert.deepEqual(readNavigation(back,allowed),state);
  const active=updateListQuery(back,allowed,{filter:"active"});assert.equal(readNavigation(active,allowed).list.filter,"active");assert.equal(readNavigation(active,allowed).list.offset,0);
  const all=updateListQuery(active,allowed,{filter:"all"});assert.equal(readNavigation(all,allowed).list.filter,"all");
  assert.equal(readNavigation("page=templates&templates_status=invalid",allowed).list.filter,"active");
});
