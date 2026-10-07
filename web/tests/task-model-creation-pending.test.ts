import { test } from "node:test";
import assert from "node:assert/strict";
import { loadTaskCreationPending, storeTaskCreationPending, finishTaskCreationPending, clearTaskCreationPending, validTaskCreationBody, type PendingTaskCreation } from "../src/task-model-creation-pending.ts";
import type { PendingStorage } from "../src/model-pending.ts";
class Memory implements PendingStorage {
  rows = new Map<string, string>();get length() { return this.rows.size; }key(index: number) { return [...this.rows.keys()][index] ?? null; }
  getItem(key: string) { return this.rows.get(key) ?? null; }setItem(key: string, value: string) { this.rows.set(key, value); }removeItem(key: string) { this.rows.delete(key); }
}
const request = (id = "owned-task-model-creation-001"): PendingTaskCreation => ({ version: 1, actor: "owned-admin", created_at: 1000,
  body: { task: { name: "Owned task", goal: "Owned goal", asset_ids: ["asset-a", "asset-b"], checks: ["security_headers"], workers: 2, planner: "rules", remote_connection_id: null, worker_dependencies: { "asset-b": ["asset-a"] } },
    models: { planner: { profile_id: "owned-profile", expected_profile_revision: 1 } }, request_id: id } });
test("new document keeps nested original creation body and expiry through exact confirmation", () => {
  const storage = new Memory(), row = request();storeTaskCreationPending(storage, row);
  const recovered = loadTaskCreationPending(storage, row.actor, 3000)[0];assert.deepEqual(recovered, row);
  storeTaskCreationPending(storage, { ...recovered, created_at: 3000 });assert.equal(loadTaskCreationPending(storage, row.actor, 3000)[0].created_at, 1000);
  assert.deepEqual(loadTaskCreationPending(storage, row.actor, 1000 + 24 * 3600 * 1000), []);
});
test("distinct tabs and actors survive finishing one creation; logout clears only the actor", () => {
  const storage = new Memory(), first = request(), second = request("owned-task-model-creation-002"), other = { ...request(), actor: "other-admin" };
  for (const row of [first, second, other]) storeTaskCreationPending(storage, row);
  finishTaskCreationPending(storage, first);assert.deepEqual(loadTaskCreationPending(storage, first.actor, 1000), [second]);
  clearTaskCreationPending(storage, first.actor);assert.deepEqual(loadTaskCreationPending(storage, other.actor, 1000), [other]);
});
test("changed nested task/model body cannot overwrite or clear an existing creation ID", () => {
  const storage = new Memory(), row = request();storeTaskCreationPending(storage, row);
  const changed = { ...row, body: { ...row.body, task: { ...row.body.task, name: "Different valid task" } } };
  const revised = { ...row, body: { ...row.body, models: { planner: { profile_id: "owned-profile", expected_profile_revision: 2 } } } };
  for (const value of [changed, revised]) { assert.equal(validTaskCreationBody(value.body), true);assert.throws(() => storeTaskCreationPending(storage, value));assert.throws(() => finishTaskCreationPending(storage, value)); }
  assert.deepEqual(loadTaskCreationPending(storage, row.actor, 1000), [row]);
});
test("canonical object field order does not discard the original creation timestamp", () => {
  const storage = new Memory(), row = request();storeTaskCreationPending(storage, row);
  storeTaskCreationPending(storage, { ...row, created_at: 2000, body: { request_id: row.body.request_id, models: row.body.models, task: row.body.task } });
  assert.equal(loadTaskCreationPending(storage, row.actor, 2000)[0].created_at, 1000);
});
test("credential fields, arbitrary target URLs, invalid review versions and dependency cycles do not enter storage", () => {
  const row = request();
  const invalid = [ { ...row.body, key: "must-not-store" },
    { ...row.body, task: { ...row.body.task, endpoint: "https://target.invalid" } },
    { ...row.body, models: { planner: { profile_id: "owned-profile", expected_profile_revision: 0 } } },
    { ...row.body, models: { planner: { profile_id: "owned-profile", expected_profile_revision: true } } },
    { ...row.body, task: { ...row.body.task, worker_dependencies: { "asset-a": ["asset-b"], "asset-b": ["asset-a"] } } },
    { ...row.body, models: { unknown: { profile_id: "owned-profile", expected_profile_revision: 1 } } } ];
  for (const body of invalid) assert.equal(validTaskCreationBody(body), false);
});
test("malformed and oversized stored creation blocks until explicit actor-scoped cleanup", () => {
  for (const broken of ["not-json", "x".repeat(16385), JSON.stringify({ ...request(), created_at: 100_000 })]) {
    const storage = new Memory(), row = request();storeTaskCreationPending(storage, row);storage.setItem(storage.key(0)!, broken);
    assert.throws(() => loadTaskCreationPending(storage, row.actor, 1000));assert.equal(storage.length, 1);
    clearTaskCreationPending(storage, row.actor);assert.equal(storage.length, 0);
  }
});
test("write failure means no caller receives a durable creation request to dispatch", () => {
  const storage = new Memory();storage.setItem = () => { throw new Error("Owned quota"); };
  assert.throws(() => storeTaskCreationPending(storage, request()), /request was not sent because it could not be retained/);assert.equal(storage.length, 0);
});
test("pending creation bound preserves all twenty original UUIDs when refusing another", () => {
  const storage = new Memory();for (let index = 0; index < 20; index++) storeTaskCreationPending(storage, request("owned-create-boundary-" + index));
  assert.throws(() => storeTaskCreationPending(storage, request("owned-create-boundary-overflow")));assert.equal(storage.length, 20);
});
