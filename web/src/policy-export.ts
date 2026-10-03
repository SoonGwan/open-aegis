export type PolicyTask = {
  id: string;
  approved_at?: number | null;
  checks: string[];
  execution_policy?: unknown;
  scope_snapshot: { authorization_rules?: unknown }[];
};

export function policyExportReason(task: PolicyTask): string | null {
  if (!task.checks.includes("api_authorization"))
    return "이 작업에는 API 권한 검증이 없습니다.";
  if (
    !task.approved_at ||
    !Number.isFinite(task.approved_at) ||
    task.approved_at <= 0
  )
    return "승인한 작업에서 정책을 내려받을 수 있습니다.";
  if (!task.execution_policy)
    return "이전 작업은 새 계획으로 승인한 뒤 정책을 내려받으세요.";
  if (
    !task.scope_snapshot.some(
      (asset) =>
        Array.isArray(asset.authorization_rules) &&
        asset.authorization_rules.length > 0,
    )
  )
    return "승인 범위에 API 권한 규칙이 없습니다.";
  return null;
}
