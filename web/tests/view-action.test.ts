import { test } from "node:test";
import assert from "node:assert/strict";
import { ViewScope, runViewAction } from "../src/view-action.ts";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function harness() {
  const scope = new ViewScope();
  const modalScope = new ViewScope();
  const routeCurrent = scope.capture();
  const modalCurrent = modalScope.capture();
  const request = deferred<{ id: string }>();
  const refresh = deferred<void>();
  const effects: string[] = [];
  let refreshStarted!: () => void;
  const refreshing = new Promise<void>((resolve) => {
    refreshStarted = resolve;
  });
  const action = runViewAction({
    execute: () => request.promise,
    reconcile: async () => {
      effects.push("refresh");
      refreshStarted();
      await refresh.promise;
      effects.push("records-changed");
    },
    isCurrent: () => routeCurrent() && modalCurrent(),
    success: (_value, current) =>
      effects.push(current ? "success" : "previous-success"),
    failure: (_error, current) =>
      effects.push(current ? "local-error" : "previous-error"),
  }).then((result) => {
    if (result) effects.push("close-and-navigate");
    return result;
  });
  return { scope, modalScope, request, refresh, effects, refreshing, action };
}

test("current action refreshes committed data and permits its own navigation", async () => {
  const h = harness();
  h.request.resolve({ id: "replacement" });
  await h.refreshing;
  assert.deepEqual(h.effects, ["refresh"]);
  h.refresh.resolve();
  assert.deepEqual(await h.action, { id: "replacement" });
  assert.deepEqual(h.effects, [
    "refresh",
    "records-changed",
    "success",
    "close-and-navigate",
  ]);
});
test("late success reconciles data but cannot close or redirect a different view", async () => {
  const h = harness();
  h.scope.invalidate();
  h.request.resolve({ id: "replacement" });
  await h.refreshing;
  h.refresh.resolve();
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, [
    "refresh",
    "records-changed",
    "previous-success",
  ]);
});
test("navigation during post-commit refresh invalidates the completion too", async () => {
  const h = harness();
  h.request.resolve({ id: "replacement" });
  await h.refreshing;
  h.scope.invalidate();
  h.refresh.resolve();
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, [
    "refresh",
    "records-changed",
    "previous-success",
  ]);
});
test("Back to the same view does not revive an old request's navigation", async () => {
  const h = harness();
  h.scope.invalidate(); // Leave.
  h.scope.invalidate(); // Return to the identical URL.
  h.request.resolve({ id: "replacement" });
  await h.refreshing;
  h.refresh.resolve();
  assert.equal(await h.action, undefined);
  assert.equal(h.effects.includes("close-and-navigate"), false);
});
test("late failure stays out of the newer view's local error and retry state", async () => {
  const h = harness();
  h.scope.invalidate();
  h.request.reject(new Error("held failure"));
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, ["previous-error"]);
});
test("current failure retains local recovery without success or navigation", async () => {
  const h = harness();
  h.request.reject(new Error("held failure"));
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, ["local-error"]);
});

test("closing and reopening a local modal invalidates success without a URL change", async () => {
  const h = harness();
  h.modalScope.invalidate();
  h.modalScope.invalidate();
  h.request.resolve({ id: "saved-note" });
  await h.refreshing;
  h.refresh.resolve();
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, [
    "refresh",
    "records-changed",
    "previous-success",
  ]);
});
test("a closed modal's late error does not enter the replacement modal's error state", async () => {
  const h = harness();
  h.modalScope.invalidate();
  h.request.reject(new Error("old-modal-error"));
  assert.equal(await h.action, undefined);
  assert.deepEqual(h.effects, ["previous-error"]);
});
