import { test } from "node:test";
import assert from "node:assert/strict";
import {
  readTaskTodos,
  updateTaskTodosQuery,
  detailQuery,
  navigateQuery,
  updateTaskCollectionQuery,
  updateTaskChatQuery,
} from "../src/navigation-state.ts";
const empty = { search: "", offset: 0, snapshot: null };
const source =
  "page=tasks&tasks_q=source&tasks_offset=25&detail=task&detail_id=task-one";
function bookmark() {
  let q = updateTaskTodosQuery(source, {
    list: { ...empty, search: "한글 & ?" },
  });
  q = updateTaskTodosQuery(q, {
    list: { search: "한글 & ?", offset: 25, snapshot: 400 },
    todoId: "a".repeat(64),
  });
  q = updateTaskTodosQuery(q, { history: { ...empty, search: "검토자" } });
  return updateTaskTodosQuery(q, {
    history: { search: "검토자", offset: 50, snapshot: 800 },
  });
}
test("todo bookmark roundtrips independent list/history positions and surrounding task/chat state", () => {
  const old = bookmark();
  let q = updateTaskCollectionQuery(old, "events", { search: "task event" });
  q = updateTaskChatQuery(q, { search: "conversation", expanded: true });
  assert.deepEqual(readTaskTodos(q), {
    list: { search: "한글 & ?", offset: 25, snapshot: 400 },
    todoId: "a".repeat(64),
    history: { search: "검토자", offset: 50, snapshot: 800 },
  });
  assert.equal(new URLSearchParams(q).get("tasks_offset"), "25");
  assert.deepEqual(
    readTaskTodos(navigateQuery(q, ["tasks"], "tasks", false, true)),
    readTaskTodos(q),
  );
  assert.deepEqual(readTaskTodos(old), readTaskTodos(q));
});
test("changing one search resets only its position; changing selection resets its history", () => {
  const old = bookmark();
  const list = updateTaskTodosQuery(old, {
    list: { search: "new", offset: 25, snapshot: 400 },
  });
  assert.deepEqual(readTaskTodos(list).list, { ...empty, search: "new" });
  assert.deepEqual(readTaskTodos(list).history, readTaskTodos(old).history);
  const history = updateTaskTodosQuery(old, {
    history: { search: "new history", offset: 50, snapshot: 800 },
  });
  assert.deepEqual(readTaskTodos(history).history, {
    ...empty,
    search: "new history",
  });
  assert.deepEqual(readTaskTodos(history).list, readTaskTodos(old).list);
  const changed = updateTaskTodosQuery(old, { todoId: "b".repeat(64) });
  assert.deepEqual(readTaskTodos(changed).history, empty);
  assert.deepEqual(readTaskTodos(changed).list, readTaskTodos(old).list);
  const closed = updateTaskTodosQuery(old, { todoId: "" });
  assert.deepEqual(readTaskTodos(closed), {
    list: readTaskTodos(old).list,
    todoId: "",
    history: empty,
  });
  assert.equal(new URLSearchParams(closed).has("task_todo_history_q"), false);
});
test("closing/changing task or switching page removes todo state; old bookmark remains restorable", () => {
  const old = bookmark();
  for (const detail of [
    null,
    { kind: "task" as const, id: "other" },
    { kind: "finding" as const, id: "finding-one" },
  ]) {
    const q = detailQuery(old, detail);
    assert.deepEqual(readTaskTodos(q), {
      list: empty,
      todoId: "",
      history: empty,
    });
    assert.equal(
      [...new URLSearchParams(q).keys()].some((k) => k.startsWith("task_todo")),
      false,
    );
  }
  assert.deepEqual(
    readTaskTodos(navigateQuery(old, ["tasks", "assets"], "assets")),
    { list: empty, todoId: "", history: empty },
  );
  assert.equal(readTaskTodos(old).history.offset, 50);
  assert.equal(
    updateTaskTodosQuery("page=tasks", { todoId: "one" }),
    "page=tasks",
  );
});
test("malformed IDs, oversized searches and unsafe numeric bookmarks are normalized before requests", () => {
  for (const id of ["../../foreign", "x".repeat(81), "<script>"]) {
    const q = updateTaskTodosQuery(bookmark(), {
      todoId: id,
      history: { search: "stale", offset: 50, snapshot: 800 },
    });
    assert.equal(readTaskTodos(q).todoId, "");
    assert.deepEqual(readTaskTodos(q).history, empty);
    assert.equal(new URLSearchParams(q).has("task_todo_id"), false);
  }
  const q = detailQuery(
    source +
      "&task_todo_id=one&task_todos_offset=49&task_todos_snapshot=1e5&task_todo_history_offset=-25&task_todo_history_snapshot=9007199254740992",
    { kind: "task", id: "task-one" },
  );
  assert.deepEqual(readTaskTodos(q), {
    list: { ...empty, offset: 25 },
    todoId: "one",
    history: empty,
  });
  const bounded = updateTaskTodosQuery(q, {
    list: { search: "x".repeat(199) + "😀", offset: Infinity, snapshot: NaN },
  });
  assert.deepEqual(readTaskTodos(bounded).list, {
    ...empty,
    search: "x".repeat(199),
  });
  const unscoped = detailQuery(
    "page=tasks&task_todo_id=one&task_todos_q=stale&task_todo_history_offset=25",
    null,
  );
  assert.deepEqual(readTaskTodos(unscoped), {
    list: empty,
    todoId: "",
    history: empty,
  });
});

test("old item history callbacks cannot put their search/page into a newly selected item", async () => {
  const { todoScopeMatches } = await import("../src/navigation-state.ts");
  const old = bookmark(),
    previous = readTaskTodos(old);
  let current = updateTaskTodosQuery(old, { todoId: "b".repeat(64) });
  if (todoScopeMatches(current, "task-one", previous.todoId))
    current = updateTaskTodosQuery(current, { history: previous.history });
  assert.deepEqual(readTaskTodos(current).history, empty);
  assert.equal(todoScopeMatches(current, "task-one"), true);
  assert.equal(todoScopeMatches(current, "task-one", "b".repeat(64)), true);
  assert.equal(
    todoScopeMatches(
      detailQuery(current, { kind: "task", id: "other" }),
      "task-one",
    ),
    false,
  );
  assert.equal(todoScopeMatches(detailQuery(current, null), "task-one"), false);
  assert.equal(todoScopeMatches(current, "task-one", "a".repeat(64)), false);
});

test("a pre-render callback cannot restore old list/history conditions after their URL has changed", async () => {
  const { todoCollectionMatches } = await import("../src/navigation-state.ts");
  const old = bookmark(),
    previous = readTaskTodos(old);
  let current = updateTaskTodosQuery(old, {
    list: { ...previous.list, search: "new list" },
  });
  assert.equal(
    todoCollectionMatches(current, "task-one", "list", previous.list),
    false,
  );
  assert.equal(
    todoCollectionMatches(
      current,
      "task-one",
      "history",
      previous.history,
      previous.todoId,
    ),
    true,
  );
  current = updateTaskTodosQuery(old, {
    history: { ...previous.history, offset: 0, snapshot: null },
  });
  assert.equal(
    todoCollectionMatches(
      current,
      "task-one",
      "history",
      previous.history,
      previous.todoId,
    ),
    false,
  );
  assert.equal(
    todoCollectionMatches(current, "task-one", "list", previous.list),
    true,
  );
  assert.equal(
    todoCollectionMatches(old, "task-one", "list", previous.list),
    true,
  );
});
