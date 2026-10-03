export type RuleDraft = {
  key: string;
  path: string;
  role: string;
  allowed: boolean;
  credential: string;
  schemaEnabled: boolean;
  schema: string;
  ownerEnabled: boolean;
  pointer: string;
  expected: string;
};

export function blankRule(key: string): RuleDraft {
  return {
    key,
    path: "",
    role: "",
    allowed: false,
    credential: "",
    schemaEnabled: false,
    schema: "",
    ownerEnabled: false,
    pointer: "",
    expected: "",
  };
}

export function parseRules(text: string): Record<string, unknown>[] {
  const value: unknown = JSON.parse(text || "[]");
  if (
    !Array.isArray(value) ||
    value.length > 20 ||
    value.some((row) => !row || typeof row !== "object" || Array.isArray(row))
  )
    throw new Error("규칙 JSON은 최대 20개 객체를 담은 배열이어야 합니다.");
  return value;
}

export function rulesToDrafts(rows: unknown[]): RuleDraft[] {
  return parseRules(JSON.stringify(rows)).map((row, index) => {
    const allowed = [
      "path",
      "role",
      "expected_allowed",
      "credential_env",
      "response_schema",
      "ownership",
    ];
    const owner = row.ownership as Record<string, unknown> | null | undefined;
    if (
      Object.keys(row).some((key) => !allowed.includes(key)) ||
      typeof row.path !== "string" ||
      typeof row.role !== "string" ||
      typeof row.expected_allowed !== "boolean" ||
      (row.credential_env !== undefined &&
        typeof row.credential_env !== "string") ||
      (row.response_schema != null &&
        (typeof row.response_schema !== "object" ||
          Array.isArray(row.response_schema))) ||
      (owner != null &&
        (typeof owner !== "object" ||
          Array.isArray(owner) ||
          Object.keys(owner).some(
            (key) => !["pointer", "expected"].includes(key),
          ) ||
          typeof owner.pointer !== "string" ||
          typeof owner.expected !== "string"))
    )
      throw new Error(
        "폼으로 표시할 수 없는 필드가 있습니다. JSON 편집에서 원본을 확인하세요.",
      );
    return {
      ...blankRule(`rule-${index}`),
      path: row.path,
      role: row.role,
      allowed: row.expected_allowed,
      credential: (row.credential_env as string) || "",
      schemaEnabled: row.response_schema != null,
      schema:
        row.response_schema == null
          ? ""
          : JSON.stringify(row.response_schema, null, 2),
      ownerEnabled: owner != null,
      pointer: (owner?.pointer as string) || "",
      expected: (owner?.expected as string) || "",
    };
  });
}

export function parseSchema(text: string): Record<string, unknown> {
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("응답 스키마는 JSON 객체여야 합니다.");
  if (new TextEncoder().encode(JSON.stringify(value)).length > 16384)
    throw new Error("응답 스키마는 UTF-8 JSON 16 KiB 이하여야 합니다.");
  return value as Record<string, unknown>;
}

export function draftsToRules(drafts: RuleDraft[]) {
  return drafts.map((row) => ({
    path: row.path,
    role: row.role,
    expected_allowed: row.allowed,
    credential_env: row.credential,
    response_schema: row.schemaEnabled ? parseSchema(row.schema) : null,
    ownership: row.ownerEnabled
      ? { pointer: row.pointer, expected: row.expected }
      : null,
  }));
}
