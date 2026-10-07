import { test } from "node:test";
import assert from "node:assert/strict";
import { loadModelPending, storeModelPending, finishModelPending, clearModelPending, PendingModelError, type PendingStorage, type PendingModelRequest } from "../src/model-pending.ts";
class Memory implements PendingStorage {
  rows = new Map<string, string>();
  get length() { return this.rows.size; }
  key(index: number) { return [...this.rows.keys()][index] ?? null; }
  getItem(key: string) { return this.rows.get(key) ?? null; }
  setItem(key: string, value: string) { this.rows.set(key, value); }
  removeItem(key: string) { this.rows.delete(key); }
}
const request = (id = "owned-pending-request-001"): PendingModelRequest => ({ version: 1, actor: "owned-admin", path: "/model-profiles/profile-a/connection-test", method: "POST", body: { expected_revision: 1, request_id: id }, created_at: 1000 });
const read = (storage: PendingStorage, row = request(), clock = 1000) => loadModelPending(storage, row.actor, row.path, row.method, clock);

test("reload preserves exact request and original expiry without issuing or renewing it", () => {
  const storage = new Memory(), original = request();storeModelPending(storage, original);
  const recovered = read(storage, original, 5000)[0];assert.deepEqual(recovered, original);
  storeModelPending(storage, { ...recovered, created_at: 5000, body: { request_id: recovered.body.request_id, expected_revision: 1 } });
  assert.equal(read(storage, original, 5000)[0].created_at, 1000);
  assert.deepEqual(read(storage, original, 1000 + 24 * 60 * 60 * 1000), []);
});
test("two tabs keep distinct UUIDs and one result cannot clear the other request", () => {
  const storage = new Memory(), first = request(), second = request("owned-pending-request-002");
  storeModelPending(storage, first);storeModelPending(storage, second);assert.equal(read(storage).length, 2);
  finishModelPending(storage, first);assert.deepEqual(read(storage), [second]);
});
test("actor, task and operation histories remain separate and logout clears only that actor", () => {
  const storage = new Memory(), first = request(), other = { ...request(), actor: "other-admin" };
  const task = { ...request(), path: "/tasks/task-a/models/planner", method: "PUT" as const,
    body: { expected_revision: 0, expected_archive_revision: 0, profile_id: "profile-a", expected_profile_revision: 1, request_id: "owned-task-pending-001" } };
  const catalog = { ...request(), path: "/model-profiles/profile-a/catalog" };
  for (const row of [first, other, task, catalog]) storeModelPending(storage, row);
  assert.deepEqual(read(storage), [first]);assert.deepEqual(read(storage, task), [task]);
  clearModelPending(storage, first.actor);assert.deepEqual(read(storage), []);assert.deepEqual(read(storage, other), [other]);
});
test("changed same-ID body and altered stored context neither overwrite nor clear a receipt", () => {
  const storage = new Memory(), original = request();storeModelPending(storage, original);
  assert.throws(() => storeModelPending(storage, { ...original, body: { ...original.body, expected_revision: 2 } }), PendingModelError);
  assert.throws(() => finishModelPending(storage, { ...original, body: { ...original.body, expected_revision: 2 } }), PendingModelError);
  assert.deepEqual(read(storage), [original]);
  const key = storage.key(0)!;storage.setItem(key, JSON.stringify({ ...original, actor: "other-admin" }));
  assert.throws(() => finishModelPending(storage, original), PendingModelError);assert.equal(storage.length, 1);
});
for (const value of ["not-json", JSON.stringify({ version: 99 }), "x".repeat(4097)]) {
  test("corrupt or oversized persisted entry blocks recovery until explicit scoped cleanup", () => {
    const storage = new Memory(), original = request();storeModelPending(storage, original);storage.setItem(storage.key(0)!, value);
    assert.throws(() => read(storage), PendingModelError);assert.equal(storage.length, 1);
    clearModelPending(storage, original.actor, original.path, original.method);assert.deepEqual(read(storage), []);
  });
}
test("future timestamp and payload credentials are rejected without storing anything", () => {
  const storage = new Memory(), original = request();
  assert.throws(() => storeModelPending(storage, { ...original, body: { ...original.body, key: "must-never-store" } }), PendingModelError);
  assert.equal(storage.length, 0);
  storeModelPending(storage, { ...original, created_at: 100_000 });assert.throws(() => read(storage), PendingModelError);
});
test("storage quota failure is observable before any caller can dispatch the request", () => {
  const storage = new Memory();storage.setItem = () => { throw new Error("owned quota failure"); };
  assert.throws(() => storeModelPending(storage, request()), /request was not sent because it could not be retained/);assert.equal(storage.length, 0);
});
test("maximum pending receipts rejects a new UUID without discarding existing operations", () => {
  const storage = new Memory();for (let index = 0; index < 20; index++) storeModelPending(storage, request("owned-boundary-request-" + index));
  assert.throws(() => storeModelPending(storage, request("owned-boundary-overflow-001")), PendingModelError);
  assert.equal(read(storage).length, 20);
});
test("unsupported methods and target URLs never enter model-operation storage", () => {
  const storage = new Memory();assert.throws(() => storeModelPending(storage, { ...request(), method: "PUT" }), PendingModelError);
  assert.throws(() => storeModelPending(storage, { ...request(), path: "https://target.invalid/" }), PendingModelError);assert.equal(storage.length, 0);
});
