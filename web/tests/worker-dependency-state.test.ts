import { test } from "node:test";
import assert from "node:assert/strict";
import {
  selectWorkerAsset,
  validateWorkerDependencies,
  WorkerDependencyError,
  type WorkerSelection,
} from "../src/worker-dependency-state.ts";
const asset = (id: string) => ({
  id,
  name: `Asset ${id}`,
  url: `https://owned.invalid/${id}/`,
});

test("deselection atomically removes both inbound and outbound edges; reselect does not resurrect them", () => {
  const state: WorkerSelection = {
    selected: Object.fromEntries(["a", "b", "c"].map((id) => [id, asset(id)])),
    dependencies: { b: ["a"], c: ["a", "b"] },
  };
  const next = selectWorkerAsset(state, asset("b"), false);
  assert.deepEqual(next.dependencies, { c: ["a"] });
  assert.deepEqual(state.dependencies, { b: ["a"], c: ["a", "b"] });
  assert.deepEqual(selectWorkerAsset(next, asset("b"), true).dependencies, {
    c: ["a"],
  });
});
test("picking an unrelated asset preserves cross-page selection metadata and relationships", () => {
  const state: WorkerSelection = {
    selected: { a: asset("a"), b: asset("b") },
    dependencies: { b: ["a"] },
  };
  const next = selectWorkerAsset(state, asset("c"), true);
  assert.deepEqual(next.selected.a, asset("a"));
  assert.deepEqual(next.dependencies, { b: ["a"] });
  const literal = selectWorkerAsset(
    { selected: {}, dependencies: {} },
    asset("__proto__"),
    true,
  );
  assert.ok(Object.hasOwn(literal.selected, "__proto__"));
  assert.equal(Object.getPrototypeOf(literal.selected), Object.prototype);
});
test("valid independent, chain and join declarations match server contract", () => {
  for (const graph of [{}, { b: ["a"], c: ["a", "b"] }])
    validateWorkerDependencies(["a", "b", "c"], graph);
  validateWorkerDependencies(["constructor"], {});
});
test("cyclic declarations name a focus target; invalid shapes, foreign and duplicate edges are refused", () => {
  assert.throws(
    () => validateWorkerDependencies(["a", "b"], { a: ["b"], b: ["a"] }),
    (e: unknown) => e instanceof WorkerDependencyError && e.child === "a",
  );
  for (const value of [
    null,
    [],
    { a: ["a"] },
    { b: ["foreign"] },
    { b: ["a", "a"] },
    { b: "a" },
    { unknown: [] },
  ])
    assert.throws(
      () => validateWorkerDependencies(["a", "b"], value),
      WorkerDependencyError,
    );
});
test("asset and edge caps are enforced before submitting a plan", () => {
  const ids = Array.from({ length: 20 }, (_, i) => String(i));
  const pairs = ids.flatMap((child, i) =>
    ids.slice(0, i).map((parent) => [child, parent]),
  );
  const graph = (count: number) => {
    const result: Record<string, string[]> = {};
    for (const [child, parent] of pairs.slice(0, count))
      (result[child] ||= []).push(parent);
    return result;
  };
  validateWorkerDependencies(ids, graph(40));
  assert.throws(
    () => validateWorkerDependencies(ids, graph(41)),
    WorkerDependencyError,
  );
  assert.throws(
    () => validateWorkerDependencies([], {}),
    WorkerDependencyError,
  );
  const state: WorkerSelection = {
    selected: Object.fromEntries(ids.map((id) => [id, asset(id)])),
    dependencies: {},
  };
  assert.equal(selectWorkerAsset(state, asset("extra"), true), state);
});
