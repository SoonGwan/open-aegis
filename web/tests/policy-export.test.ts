import { test } from "node:test";
import assert from "node:assert/strict";
import { policyExportReason } from "../src/policy-export.ts";

test("policy export explains approval, selection and legacy limitations", () => {
  const task = {
    id: "fixture",
    checks: ["api_authorization"],
    approved_at: 1,
    execution_policy: {},
    scope_snapshot: [{ authorization_rules: [{}] }],
  };
  assert.equal(policyExportReason(task), null);
  assert.match(policyExportReason({ ...task, checks: [] })!, /no API authorization checks/);
  assert.match(policyExportReason({ ...task, approved_at: 0 })!, /download policies from approved tasks/);
  assert.match(
    policyExportReason({ ...task, execution_policy: undefined })!,
    /For older tasks, approve a new plan/,
  );
  assert.match(
    policyExportReason({ ...task, scope_snapshot: [] })!,
    /No API authorization rules in the approved scope/,
  );
  assert.match(
    policyExportReason({ ...task, scope_snapshot: [{}] })!,
    /No API authorization rules in the approved scope/,
  );
  assert.match(
    policyExportReason({
      ...task,
      scope_snapshot: [{ authorization_rules: null }],
    })!,
    /No API authorization rules in the approved scope/,
  );
});
