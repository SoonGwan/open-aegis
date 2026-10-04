import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detailQuery,
  readTaskCollection,
  updateTaskCollectionQuery,
} from "../src/navigation-state.ts";

test("task finding and event positions restore independently and preserve source list", () => {
  let query = detailQuery("page=tasks&tasks_q=fixture&tasks_offset=25", {
    kind: "task",
    id: "task-one",
  });
  query = updateTaskCollectionQuery(query, "events", {
    search: "한글 & ?",
    offset: 50,
    snapshot: 123,
  });
  // A new search starts at zero; setting page position is a separate interaction.
  query = updateTaskCollectionQuery(query, "events", {
    offset: 50,
    snapshot: 123,
  });
  query = updateTaskCollectionQuery(query, "findings", { search: "high" });
  query = updateTaskCollectionQuery(query, "findings", {
    offset: 25,
    snapshot: 456,
  });
  assert.deepEqual(readTaskCollection(query, "events"), {
    search: "한글 & ?",
    offset: 50,
    snapshot: 123,
  });
  assert.deepEqual(readTaskCollection(query, "findings"), {
    search: "high",
    offset: 25,
    snapshot: 456,
  });
  assert.equal(new URLSearchParams(query).get("tasks_q"), "fixture");
  assert.equal(new URLSearchParams(query).get("tasks_offset"), "25");
  const previous = query;
  query = updateTaskCollectionQuery(query, "events", { search: "new" });
  assert.deepEqual(readTaskCollection(query, "events"), {
    search: "new",
    offset: 0,
    snapshot: null,
  });
  assert.equal(readTaskCollection(previous, "events").offset, 50);
  assert.equal(readTaskCollection(query, "findings").offset, 25);
});

test("task collection state cannot leak into another detail or a closed modal", () => {
  const original =
    "page=tasks&detail=task&detail_id=one&task_events_q=fixture&task_events_offset=25";
  assert.equal(
    readTaskCollection(
      detailQuery(original, { kind: "task", id: "one" }),
      "events",
    ).search,
    "fixture",
  );
  for (const detail of [
    null,
    { kind: "task" as const, id: "two" },
    { kind: "finding" as const, id: "finding-one" },
  ]) {
    const query = detailQuery(original, detail);
    assert.equal(new URLSearchParams(query).has("task_events_q"), false);
    assert.deepEqual(readTaskCollection(query, "events"), {
      search: "",
      offset: 0,
      snapshot: null,
    });
    assert.equal(new URLSearchParams(query).get("page"), "tasks");
  }
  assert.equal(
    updateTaskCollectionQuery("page=tasks", "events", { search: "no-detail" }),
    "page=tasks",
  );
});

test("invalid bookmark positions normalize before requests and search preserves Unicode bounds", () => {
  const original =
    "page=tasks&detail=task&detail_id=one&task_events_offset=49&task_events_snapshot=1e5&task_findings_offset=-25";
  const query = detailQuery(original, { kind: "task", id: "one" });
  assert.deepEqual(readTaskCollection(query, "events"), {
    search: "",
    offset: 25,
    snapshot: null,
  });
  assert.equal(new URLSearchParams(query).has("task_findings_offset"), false);
  const bounded = updateTaskCollectionQuery(query, "events", {
    search: "x".repeat(199) + "😀",
    offset: Infinity,
    snapshot: NaN,
  });
  assert.equal(readTaskCollection(bounded, "events").search, "x".repeat(199));
  assert.equal(readTaskCollection(bounded, "events").snapshot, null);
  assert.equal(readTaskCollection(bounded, "events").offset, 0);
});

test("observation source keeps its list and independent task pages in URL", () => {
  let query = detailQuery(
    "page=observations&observations_q=source&observations_offset=25",
    { kind: "task", id: "source-task" },
  );
  query = updateTaskCollectionQuery(query, "observations", {
    search: "owned & ?",
  });
  query = updateTaskCollectionQuery(query, "observations", {
    offset: 25,
    snapshot: 987,
  });
  query = updateTaskCollectionQuery(query, "events", { search: "events" });
  assert.deepEqual(readTaskCollection(query, "observations"), {
    search: "owned & ?",
    offset: 25,
    snapshot: 987,
  });
  assert.equal(readTaskCollection(query, "events").search, "events");
  assert.equal(new URLSearchParams(query).get("observations_offset"), "25");
  const closed = detailQuery(query, null);
  assert.equal(new URLSearchParams(closed).get("observations_q"), "source");
  assert.equal(new URLSearchParams(closed).has("task_observations_q"), false);
  assert.equal(
    readTaskCollection(
      detailQuery(query, { kind: "task", id: "other" }),
      "observations",
    ).offset,
    0,
  );
});
