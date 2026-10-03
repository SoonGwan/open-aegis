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
  assert.match(policyExportReason({ ...task, checks: [] })!, /API 권한 검증/);
  assert.match(policyExportReason({ ...task, approved_at: 0 })!, /승인한 작업/);
  assert.match(
    policyExportReason({ ...task, execution_policy: undefined })!,
    /이전 작업/,
  );
  assert.match(
    policyExportReason({ ...task, scope_snapshot: [] })!,
    /규칙이 없습니다/,
  );
  assert.match(
    policyExportReason({ ...task, scope_snapshot: [{}] })!,
    /규칙이 없습니다/,
  );
  assert.match(
    policyExportReason({
      ...task,
      scope_snapshot: [{ authorization_rules: null }],
    })!,
    /규칙이 없습니다/,
  );
});
