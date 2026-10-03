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
