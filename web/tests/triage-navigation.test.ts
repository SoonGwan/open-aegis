import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detailQuery,
  readFindingCollection,
  updateFindingCollectionQuery,
} from "../src/navigation-state.ts";
const start =
  "page=findings&findings_q=source&detail=finding&detail_id=one&finding_evidence_open=true&finding_evidence_offset=50&finding_retests_q=independent";

test("decision history bookmarks preserve other proof collections and source list", () => {
  let query = updateFindingCollectionQuery(start, "history", {
    expanded: true,
    search: "합성 %_ &",
  });
  query = updateFindingCollectionQuery(query, "history", {
    offset: 25,
    snapshot: 123,
  });
  assert.deepEqual(readFindingCollection(query, "history"), {
    expanded: true,
    search: "합성 %_ &",
    offset: 25,
    snapshot: 123,
  });
  query = updateFindingCollectionQuery(query, "history", { expanded: false });
  assert.equal(readFindingCollection(query, "history").offset, 25);
  query = updateFindingCollectionQuery(query, "history", { search: "next" });
  assert.deepEqual(readFindingCollection(query, "history"), {
    expanded: false,
    search: "next",
    offset: 0,
    snapshot: null,
  });
  assert.equal(readFindingCollection(query, "evidence").offset, 50);
  assert.equal(readFindingCollection(query, "retests").search, "independent");
  assert.equal(new URLSearchParams(query).get("findings_q"), "source");
});

test("history cannot leak into another finding, task or closed detail", () => {
  const original = updateFindingCollectionQuery(start, "history", {
    expanded: true,
  });
  assert.equal(
    readFindingCollection(
      detailQuery(original, { kind: "finding", id: "one" }),
      "history",
    ).expanded,
    true,
  );
  for (const detail of [
    null,
    { kind: "finding" as const, id: "two" },
    { kind: "task" as const, id: "task-one" },
  ]) {
    const query = detailQuery(original, detail);
    assert.deepEqual(readFindingCollection(query, "history"), {
      expanded: false,
      search: "",
      offset: 0,
      snapshot: null,
    });
    assert.equal(
      [...new URLSearchParams(query).keys()].some((key) =>
        key.startsWith("finding_history_"),
      ),
      false,
    );
  }
});

test("history positions and Unicode searches normalize before API requests", () => {
  const query = detailQuery(
    start +
      "&finding_history_open=true&finding_history_offset=49&finding_history_snapshot=NaN&finding_history_q=" +
      encodeURIComponent("x".repeat(199) + "😀"),
    { kind: "finding", id: "one" },
  );
  assert.deepEqual(readFindingCollection(query, "history"), {
    expanded: true,
    search: "x".repeat(199),
    offset: 25,
    snapshot: null,
  });
});
