import { test } from "node:test";
import assert from "node:assert/strict";
import {
  readPending,
  writePending,
  clearPending,
} from "../src/chat-pending.ts";
function storage() {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
    removeItem: (key: string) => {
      data.delete(key);
    },
  };
}
const pending = {
  content: "응답 유실 복구 질문",
  request_id: "0123456789abcdef0123456789abcdef",
};
test("unacknowledged questions survive a new reader and stay scoped to actor and task", () => {
  const saved = storage();
  assert.equal(writePending(saved, "actor", "task", pending), true);
  assert.deepEqual(readPending(saved, "actor", "task"), pending);
  assert.equal(readPending(saved, "other-actor", "task"), null);
  assert.equal(readPending(saved, "actor", "other-task"), null);
  assert.equal(clearPending(saved, "actor", "task", pending.request_id), true);
  assert.equal(readPending(saved, "actor", "task"), null);
});
test("late acknowledgements cannot discard a newer intent", () => {
  const saved = storage();
  writePending(saved, "actor", "task", pending);
  const next = { content: "new question", request_id: "another-request-0001" };
  writePending(saved, "actor", "task", next);
  assert.equal(clearPending(saved, "actor", "task", pending.request_id), false);
  assert.deepEqual(readPending(saved, "actor", "task"), next);
});
test("denied, full, malformed and incompatible storage does not crash recovery", () => {
  const denied = {
    getItem: () => {
      throw new Error("denied");
    },
    setItem: () => {
      throw new Error("full");
    },
    removeItem: () => {
      throw new Error("denied");
    },
  };
  assert.equal(readPending(denied, "actor", "task"), null);
  assert.equal(writePending(denied, "actor", "task", pending), false);
  assert.equal(
    clearPending(denied, "actor", "task", pending.request_id),
    false,
  );
  assert.equal(writePending(null, "actor", "task", pending), false);
  const saved = storage();
  writePending(saved, "actor", "task", pending);
  const key = [...saved.data.keys()][0];
  for (const value of [
    "broken",
    "null",
    "x".repeat(12001),
    JSON.stringify({ version: 2, ...pending }),
    JSON.stringify({ version: 1, ...pending, content: " " }),
    JSON.stringify({ version: 1, ...pending, content: "x".repeat(2001) }),
    JSON.stringify({ version: 1, ...pending, request_id: "bad/id" }),
  ]) {
    saved.data.set(key, value);
    assert.equal(readPending(saved, "actor", "task"), null);
  }
  writePending(saved, "actor", "task", pending);
  const cannotClear = { ...saved, removeItem: denied.removeItem };
  assert.equal(
    clearPending(cannotClear, "actor", "task", pending.request_id),
    false,
  );
  assert.deepEqual(readPending(saved, "actor", "task"), pending);
});
