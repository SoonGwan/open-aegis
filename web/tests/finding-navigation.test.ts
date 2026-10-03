import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detailQuery,
  navigateQuery,
  readFindingCollection,
  updateFindingCollectionQuery,
} from "../src/navigation-state.ts";
const start =
  "page=findings&findings_q=source&detail=finding&detail_id=proof-1";
test("finding collection bookmarks preserve independent searches and page watermarks", () => {
  let query = updateFindingCollectionQuery(start, "evidence", {
    expanded: true,
    search: "도구 %_&",
    offset: 50,
    snapshot: 100,
  });
  // A changed search starts at the first page; a subsequent page move keeps it.
  assert.equal(readFindingCollection(query, "evidence").offset, 0);
  query = updateFindingCollectionQuery(query, "evidence", {
    offset: 50,
    snapshot: 100,
  });
  query = updateFindingCollectionQuery(query, "retests", {
    expanded: true,
    search: "판정 불가",
  });
  query = updateFindingCollectionQuery(query, "retests", {
    offset: 25,
    snapshot: 80,
  });
  assert.deepEqual(readFindingCollection(query, "evidence"), {
    search: "도구 %_&",
    expanded: true,
    offset: 50,
    snapshot: 100,
  });
  assert.deepEqual(readFindingCollection(query, "retests"), {
    search: "판정 불가",
    expanded: true,
    offset: 25,
    snapshot: 80,
  });
  assert.equal(new URLSearchParams(query).get("findings_q"), "source");
  assert.equal(detailQuery(query, { kind: "finding", id: "proof-1" }), query);
});
test("collapse preserves the list, search resets it, and latest removes its watermark", () => {
  let query = updateFindingCollectionQuery(start, "evidence", {
    expanded: true,
  });
  query = updateFindingCollectionQuery(query, "evidence", {
    offset: 25,
    snapshot: 999,
  });
  query = updateFindingCollectionQuery(query, "evidence", { expanded: false });
  assert.deepEqual(readFindingCollection(query, "evidence"), {
    search: "",
    expanded: false,
    offset: 25,
    snapshot: 999,
  });
  query = updateFindingCollectionQuery(query, "evidence", { search: "next" });
  assert.deepEqual(readFindingCollection(query, "evidence"), {
    search: "next",
    expanded: false,
    offset: 0,
    snapshot: null,
  });
});
test("changing or closing a detail clears collections without dropping the background list", () => {
  const query = updateFindingCollectionQuery(start, "evidence", {
    expanded: true,
    search: "old",
  });
  for (const target of [
    null,
    { kind: "task", id: "task-1" },
    { kind: "finding", id: "proof-2" },
  ] as const) {
    const changed = detailQuery(query, target);
    assert.equal(readFindingCollection(changed, "evidence").expanded, false);
    assert.equal(
      [...new URLSearchParams(changed).keys()].some((k) =>
        k.startsWith("finding_evidence_"),
      ),
      false,
    );
    assert.equal(new URLSearchParams(changed).get("findings_q"), "source");
  }
  assert.equal(
    readFindingCollection(
      navigateQuery(query, ["findings", "tasks"], "tasks"),
      "evidence",
    ).expanded,
    false,
  );
});
test("malformed nested positions and long surrogate searches normalize before API requests", () => {
  const query =
    start +
    "&finding_evidence_open=invalid&finding_evidence_offset=-1&finding_evidence_snapshot=9007199254740992&finding_evidence_q=" +
    encodeURIComponent("a".repeat(199) + "😀");
  const normalized = detailQuery(query, { kind: "finding", id: "proof-1" });
  assert.deepEqual(readFindingCollection(normalized, "evidence"), {
    expanded: false,
    search: "a".repeat(199),
    offset: 0,
    snapshot: null,
  });
  assert.equal(
    readFindingCollection(start + "&finding_evidence_offset=49", "evidence")
      .offset,
    25,
  );
  assert.equal(
    readFindingCollection(
      start + "&finding_evidence_offset=10000001",
      "evidence",
    ).offset,
    0,
  );
  assert.equal(
    readFindingCollection(
      "detail=task&detail_id=x&finding_evidence_open=true",
      "evidence",
    ).expanded,
    false,
  );
});
