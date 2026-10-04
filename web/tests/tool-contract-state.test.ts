import { test } from "node:test";
import assert from "node:assert/strict";
import {
  toolContractsMatch,
  type ToolManifest,
} from "../src/tool-contract-state.ts";
const current: ToolManifest = {
  format: "aegis-tools-v1",
  package_sha256: "a".repeat(64),
  checks: [
    {
      id: "security_headers",
      version: 1,
      method: "GET",
      permissions: ["base-response"],
      result_format: "aegis-check-result-v1",
      max_result_bytes: 524288,
      max_findings: 128,
      max_observations: 0,
    },
    {
      id: "endpoint_inventory",
      version: 1,
      method: "GET",
      permissions: ["base-response", "observe-links"],
      result_format: "aegis-check-result-v1",
      max_result_bytes: 524288,
      max_findings: 128,
      max_observations: 100,
    },
  ],
};
test("selected tool contracts match independently of object field order", () => {
  const snapshot = structuredClone(current);
  snapshot.checks = [
    Object.fromEntries(
      Object.entries(snapshot.checks[1]).reverse(),
    ) as (typeof snapshot.checks)[1],
  ];
  assert.equal(
    toolContractsMatch(snapshot, ["endpoint_inventory"], current),
    true,
  );
  assert.equal(
    toolContractsMatch(
      current,
      ["security_headers", "endpoint_inventory"],
      current,
    ),
    true,
  );
});
test("approval guidance rejects missing, changed and mismatched contracts", () => {
  assert.equal(
    toolContractsMatch(undefined, ["security_headers"], current),
    false,
  );
  assert.equal(
    toolContractsMatch(current, ["security_headers"], undefined),
    false,
  );
  for (const field of ["format", "package_sha256"] as const) {
    const changed = structuredClone(current);
    changed[field] = "different";
    assert.equal(
      toolContractsMatch(
        changed,
        ["security_headers", "endpoint_inventory"],
        current,
      ),
      false,
    );
  }
  for (const update of [
    { version: 2 },
    { max_findings: 129 },
    { permissions: ["shell"] },
    { method: "POST" },
  ]) {
    const changed = structuredClone(current);
    Object.assign(changed.checks[0], update);
    assert.equal(
      toolContractsMatch(
        changed,
        ["security_headers", "endpoint_inventory"],
        current,
      ),
      false,
    );
  }
  assert.equal(
    toolContractsMatch(
      current,
      ["endpoint_inventory", "security_headers"],
      current,
    ),
    false,
  );
  assert.equal(
    toolContractsMatch(
      current,
      ["security_headers", "security_headers"],
      current,
    ),
    false,
  );
  assert.equal(toolContractsMatch(current, [], current), false);
  const extra = { ...current, unexpected: "reject" };
  assert.equal(toolContractsMatch(extra, ["security_headers", "endpoint_inventory"], current), false);
});
