import { test } from "node:test";
import assert from "node:assert/strict";
import { readCallList, updateCallListQuery } from "../src/call-navigation.ts";
test("call bookmarks roundtrip independent filters, page and watermark", () => {
  let query = updateCallListQuery(
    "page=settings&tasks_q=keep&detail=task&detail_id=one",
    {
      search: "합성 %_ &",
      source: "conversation",
      state: "uncommitted",
      taskId: "one",
    },
  );
  query = updateCallListQuery(query, { offset: 25, snapshot: 123 });
  assert.deepEqual(readCallList(query), {
    search: "합성 %_ &",
    source: "conversation",
    state: "uncommitted",
    taskId: "one",
    offset: 25,
    snapshot: 123,
  });
  assert.equal(new URLSearchParams(query).get("tasks_q"), "keep");
  for (const change of [
    { search: "next" },
    { state: "interrupted" },
    { source: "planner" },
    { taskId: "two" },
  ]) {
    const state = readCallList(updateCallListQuery(query, change));
    assert.equal(state.offset, 0);
    assert.equal(state.snapshot, null);
  }
  assert.equal(
    readCallList(updateCallListQuery(query, { search: "합성 %_ &" })).offset,
    25,
  );
});
test("hostile bookmark positions and filters do not reach call API", () => {
  const result = readCallList(
    "llm_calls_source=all&llm_calls_state=bogus&llm_calls_task=%3Cbad%3E&llm_calls_offset=10000001&llm_calls_snapshot=9007199254740992&llm_calls_q=" +
      encodeURIComponent("x".repeat(199) + "😀"),
  );
  assert.deepEqual(result, {
    search: "x".repeat(199),
    source: "",
    state: "",
    taskId: "",
    offset: 0,
    snapshot: null,
  });
  assert.equal(
    readCallList("llm_calls_offset=49&llm_calls_snapshot=0").offset,
    25,
  );
  assert.equal(readCallList("llm_calls_snapshot=0").snapshot, 0);
  assert.equal(
    readCallList(
      updateCallListQuery("", {
        state: "bogus",
        offset: -25,
        snapshot: Infinity,
      }),
    ).state,
    "",
  );
});
