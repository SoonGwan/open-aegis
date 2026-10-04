import { test } from "node:test";
import assert from "node:assert/strict";
import {
  draftOf,
  changesOf,
  rebaseDraft,
  readTodoPending,
  writeTodoPending,
  clearTodoPending,
  type Todo,
} from "../src/todo-state.ts";
const row: Todo = {
  id: "todo",
  task_id: "root",
  revision: 1,
  title: "Review",
  description: "Original",
  status: "open",
  assignee_id: null,
  assignee_name: null,
  assignee_username: null,
  resolution_note: "",
};
function storage() {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (k: string) => values.get(k) || null,
    setItem: (k: string, v: string) => {
      values.set(k, v);
    },
    removeItem: (k: string) => {
      values.delete(k);
    },
  };
}
const pending = {
  request_id: "a".repeat(32),
  title: "Review",
  description: "Keep original retry payload",
  assignee_id: null,
};
test("lost creation response survives reopening and actor/task isolation; only matching response clears it", () => {
  const s = storage();
  assert.equal(writeTodoPending(s, "alice", "child", pending), true);
  assert.deepEqual(readTodoPending(s, "alice", "child"), pending);
  assert.equal(readTodoPending(s, "bob", "child"), null);
  assert.equal(readTodoPending(s, "alice", "other"), null);
  const newer = { ...pending, request_id: "b".repeat(32) };
  writeTodoPending(s, "alice", "child", newer);
  assert.equal(
    clearTodoPending(s, "alice", "child", pending.request_id),
    false,
  );
  assert.deepEqual(readTodoPending(s, "alice", "child"), newer);
  assert.equal(clearTodoPending(s, "alice", "child", newer.request_id), true);
  assert.equal(readTodoPending(s, "alice", "child"), null);
});
test("blocked or malformed persistence never authorizes dispatch", () => {
  assert.equal(writeTodoPending(null, "a", "t", pending), false);
  const s = storage();
  assert.equal(
    writeTodoPending(s, "a", "t", { ...pending, title: " " }),
    false,
  );
  const denied = {
    getItem: () => {
      throw Error("blocked");
    },
    setItem: () => {
      throw Error("quota");
    },
    removeItem: () => {
      throw Error("blocked");
    },
  };
  assert.equal(writeTodoPending(denied, "a", "t", pending), false);
  assert.equal(readTodoPending(denied, "a", "t"), null);
  s.values.set(
    "aegis:pending-todo:" + JSON.stringify(["a", "t"]),
    JSON.stringify({ ...pending, version: 2 }),
  );
  assert.equal(readTodoPending(s, "a", "t"), null);
});
test("rebase retains local title while preserving a concurrent assignment, status and reason", () => {
  const draft = { ...draftOf(row), title: "My correction" };
  const latest: Todo = {
    ...row,
    revision: 2,
    description: "Concurrent context",
    status: "done",
    resolution_note: "Colleague reviewed",
    assignee_id: "bob",
  };
  assert.deepEqual(rebaseDraft(draftOf(row), draft, latest), {
    ...draftOf(latest),
    title: "My correction",
  });
  assert.deepEqual(
    changesOf(draftOf(latest), rebaseDraft(draftOf(row), draft, latest)),
    { title: "My correction" },
  );
});
test("explicit local removal and state transition survive concurrent changes; no-op edits remain empty", () => {
  const base: Todo = {
    ...row,
    assignee_id: "alice",
    status: "done",
    resolution_note: "Initial reason",
  };
  const draft = {
    ...draftOf(base),
    assignee_id: null,
    status: "in_progress" as const,
    resolution_note: "",
  };
  const latest: Todo = {
    ...base,
    revision: 2,
    title: "Colleague title",
    assignee_id: "bob",
  };
  assert.deepEqual(rebaseDraft(draftOf(base), draft, latest), {
    ...draft,
    title: "Colleague title",
  });
  assert.deepEqual(changesOf(draftOf(row), draftOf(row)), {});
});

test("a new terminal decision sends its explicit reason even when text equals the previous reason", () => {
  const base = {
    ...draftOf(row),
    status: "done" as const,
    resolution_note: "Manual review",
  };
  assert.deepEqual(changesOf(base, { ...base, status: "cancelled" }), {
    status: "cancelled",
    resolution_note: "Manual review",
  });
});
