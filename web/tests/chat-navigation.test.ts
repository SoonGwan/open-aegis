import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detailQuery,
  readTaskChat,
  readTaskCollection,
  updateTaskChatQuery,
} from "../src/navigation-state.ts";

test("chat bookmarks preserve task collections and list state while search resets only chat position", () => {
  let query = updateTaskChatQuery(
    "page=tasks&tasks_q=source&tasks_offset=25&detail=task&detail_id=one&task_events_q=independent&task_events_offset=50",
    { expanded: true, search: "북마크 & ?" },
  );
  query = updateTaskChatQuery(query, { offset: 25, snapshot: 123 });
  assert.deepEqual(readTaskChat(query), {
    expanded: true,
    search: "북마크 & ?",
    offset: 25,
    snapshot: 123,
  });
  const bookmark = query;
  query = updateTaskChatQuery(query, { search: "new" });
  assert.deepEqual(readTaskChat(query), {
    expanded: true,
    search: "new",
    offset: 0,
    snapshot: null,
  });
  assert.equal(readTaskChat(bookmark).offset, 25);
  assert.equal(readTaskCollection(query, "events").offset, 50);
  assert.equal(new URLSearchParams(query).get("tasks_q"), "source");
  assert.equal(new URLSearchParams(query).get("tasks_offset"), "25");
});

test("closing chat keeps its search and page, but closing or changing the task clears them", () => {
  const original =
    "page=tasks&detail=task&detail_id=one&task_chat_open=true&task_chat_q=fixture&task_chat_offset=25&task_chat_snapshot=123";
  const closed = updateTaskChatQuery(original, { expanded: false });
  assert.deepEqual(readTaskChat(closed), {
    expanded: false,
    search: "fixture",
    offset: 25,
    snapshot: 123,
  });
  assert.equal(
    readTaskChat(detailQuery(original, { kind: "task", id: "one" })).expanded,
    true,
  );
  for (const detail of [
    null,
    { kind: "task" as const, id: "two" },
    { kind: "finding" as const, id: "finding-one" },
  ]) {
    const query = detailQuery(original, detail);
    assert.deepEqual(readTaskChat(query), {
      expanded: false,
      search: "",
      offset: 0,
      snapshot: null,
    });
    assert.equal(
      [...new URLSearchParams(query).keys()].some((key) =>
        key.startsWith("task_chat_"),
      ),
      false,
    );
  }
  assert.equal(
    updateTaskChatQuery("page=tasks", { expanded: true, search: "invalid" }),
    "page=tasks",
  );
});

test("malformed chat bookmarks normalize before requests without splitting Unicode", () => {
  const query = detailQuery(
    "page=tasks&detail=task&detail_id=one&task_chat_open=1&task_chat_offset=49&task_chat_snapshot=9007199254740992",
    { kind: "task", id: "one" },
  );
  assert.deepEqual(readTaskChat(query), {
    expanded: false,
    search: "",
    offset: 25,
    snapshot: null,
  });
  const bounded = updateTaskChatQuery(query, {
    search: "x".repeat(199) + "😀",
    offset: Infinity,
    snapshot: NaN,
  });
  assert.deepEqual(readTaskChat(bounded), {
    expanded: false,
    search: "x".repeat(199),
    offset: 0,
    snapshot: null,
  });
  const maximum = updateTaskChatQuery(query, {
    offset: 10_000_000,
    snapshot: Number.MAX_SAFE_INTEGER,
  });
  assert.equal(readTaskChat(maximum).offset, 10_000_000);
  assert.equal(readTaskChat(maximum).snapshot, Number.MAX_SAFE_INTEGER);
});
