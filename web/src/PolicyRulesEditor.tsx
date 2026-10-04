import { useEffect, useId, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  blankRule,
  draftsToRules,
  parseRules,
  parseSchema,
  rulesToDrafts,
  type RuleDraft,
} from "./policy-rules";

const example = JSON.stringify(
  {
    type: "object",
    required: ["tenant_id"],
    properties: { tenant_id: { type: "string" } },
  },
  null,
  2,
);

function SchemaField({
  row,
  change,
}: {
  row: RuleDraft;
  change: (values: Partial<RuleDraft>) => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  let error = "";
  try {
    parseSchema(row.schema);
  } catch {
    error = "유효한 JSON 객체 스키마를 입력하세요. 최대 UTF-8 16 KiB입니다.";
  }
  useEffect(() => {
    ref.current?.setCustomValidity(error);
  }, [error]);
  return (
    <div className="rule-wide">
      <label>
        응답 스키마 JSON
        <textarea
          ref={ref}
          required
          rows={6}
          value={row.schema}
          maxLength={16384}
          onChange={(event) => change({ schema: event.target.value })}
          placeholder={'{"type":"object","required":["tenant_id"]}'}
          aria-invalid={!!error}
          aria-describedby={`${id}-help${error && row.schema ? ` ${id}-error` : ""}`}
        />
      </label>
      <button type="button" onClick={() => change({ schema: example })}>
        스키마 예시 적용
      </button>
      <p id={`${id}-help`} className="subtle">
        예시는 현재 스키마 입력을 대체합니다. type·properties·required·items 등
        제한된 JSON Schema를 지원합니다. 상세 형식은 저장할 때 서버에서
        검사합니다.
      </p>
      {error && row.schema && (
        <p id={`${id}-error`} className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function PolicyRulesEditor({
  initial = [],
  disabled = false,
}: {
  initial?: unknown[];
  disabled?: boolean;
}) {
  const id = useId();
  const [state] = useState(() => {
    try {
      return {
        mode: "form" as const,
        drafts: rulesToDrafts(initial),
        json: JSON.stringify(initial, null, 2),
      };
    } catch {
      return {
        mode: "json" as const,
        drafts: [] as RuleDraft[],
        json: JSON.stringify(initial, null, 2),
      };
    }
  });
  const [mode, setMode] = useState<"form" | "json">(state.mode);
  const [drafts, setDrafts] = useState(state.drafts);
  const [json, setJson] = useState(state.json);
  const [switchError, setSwitchError] = useState("");
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const next = useRef(state.drafts.length);
  const paths = useRef(new Map<string, HTMLInputElement>());
  const add = useRef<HTMLButtonElement>(null);
  const advanced = useRef<HTMLTextAreaElement>(null);
  let jsonError = "";
  if (mode === "json") {
    try {
      parseRules(json);
    } catch {
      jsonError = "JSON 객체의 배열을 입력하세요. 규칙은 최대 20개입니다.";
    }
  }
  useEffect(() => {
    advanced.current?.setCustomValidity(jsonError);
  }, [jsonError, mode]);
  useEffect(() => {
    if (focusKey === null) return;
    (focusKey === "add" ? add.current : paths.current.get(focusKey))?.focus();
    setFocusKey(null);
  }, [focusKey, drafts]);
  function switchMode(target: "form" | "json") {
    if (target === mode) return;
    try {
      if (target === "json")
        setJson(JSON.stringify(draftsToRules(drafts), null, 2));
      else {
        const rows = rulesToDrafts(parseRules(json));
        setDrafts(rows);
        next.current = rows.length;
      }
      setMode(target);
      setSwitchError("");
    } catch (error) {
      setSwitchError(
        error instanceof SyntaxError
          ? "스키마 또는 규칙의 JSON 문법을 확인하세요."
          : (error as Error).message,
      );
    }
  }
  function change(key: string, values: Partial<RuleDraft>) {
    setSwitchError("");
    setDrafts((rows) =>
      rows.map((row) => (row.key === key ? { ...row, ...values } : row)),
    );
  }
  let serialized = "[]";
  try {
    serialized = JSON.stringify(draftsToRules(drafts));
  } catch {
    /* SchemaField blocks invalid submission. */
  }
  return (
    <details
      className="form-details policy-rule-editor"
      open={initial.length > 0}
    >
      <summary>API 권한 규칙 설정 (선택)</summary>
      <fieldset disabled={disabled} className="policy-editor-controls">
        <legend>GET 접근·응답 정책</legend>
        <p id={`${id}-intro`}>
          자산 범위 안의 GET 경로를 정의하세요. 테스트 계정은 서버의
          AEGIS_TEST_* 환경변수 이름으로 연결합니다. 인증 값을 입력하지 마세요.
        </p>
        <div className="rule-toolbar" role="group" aria-label="규칙 편집 방식">
          <button
            type="button"
            aria-pressed={mode === "form"}
            aria-describedby={switchError ? `${id}-switch-error` : undefined}
            onClick={() => switchMode("form")}
          >
            입력 폼
          </button>
          <button
            type="button"
            aria-pressed={mode === "json"}
            aria-describedby={switchError ? `${id}-switch-error` : undefined}
            onClick={() => switchMode("json")}
          >
            JSON 편집
          </button>
        </div>
        {switchError && (
          <p id={`${id}-switch-error`} className="form-error" role="alert">
            {switchError}
          </p>
        )}
        {mode === "json" ? (
          <label>
            권한 규칙 JSON
            <textarea
              name="rules"
              ref={advanced}
              value={json}
              rows={10}
              maxLength={524288}
              aria-invalid={!!jsonError}
              aria-describedby={`${id}-intro ${id}-help${jsonError ? ` ${id}-json-error` : ""}${switchError ? ` ${id}-switch-error` : ""}`}
              onChange={(event) => {
                setJson(event.target.value);
                setSwitchError("");
              }}
            />
          </label>
        ) : (
          <>
            <input type="hidden" name="rules" value={serialized} />
            <p className="subtle">규칙 {drafts.length}개 / 최대 20개</p>
            {drafts.map((row, index) => (
              <fieldset key={row.key} className="policy-rule-card">
                <legend>규칙 {index + 1}</legend>
                <div className="policy-rule-grid">
                  <label>
                    GET 경로
                    <input
                      ref={(element) => {
                        if (element) paths.current.set(row.key, element);
                        else paths.current.delete(row.key);
                      }}
                      value={row.path}
                      required
                      maxLength={1000}
                      pattern="/(?!/)[^?#]*"
                      onChange={(event) =>
                        change(row.key, { path: event.target.value })
                      }
                      placeholder="/api/account"
                    />
                  </label>
                  <label>
                    테스트 역할
                    <input
                      value={row.role}
                      required
                      maxLength={80}
                      onChange={(event) =>
                        change(row.key, { role: event.target.value })
                      }
                      placeholder="예: customer-a-test"
                    />
                  </label>
                  <label>
                    예상 접근 결과
                    <select
                      value={row.allowed ? "allow" : "deny"}
                      onChange={(event) =>
                        change(row.key, {
                          allowed: event.target.value === "allow",
                        })
                      }
                    >
                      <option value="deny">거절 (401/403)</option>
                      <option value="allow">허용 (2xx)</option>
                    </select>
                  </label>
                  <label>
                    테스트 계정 환경변수
                    <input
                      value={row.credential}
                      maxLength={100}
                      pattern="AEGIS_TEST_[A-Z0-9_]+"
                      onChange={(event) =>
                        change(row.key, { credential: event.target.value })
                      }
                      placeholder="비우면 인증 없이 요청"
                      aria-describedby={`${id}-intro`}
                    />
                  </label>
                  <label className="checkbox-label rule-wide">
                    <input
                      type="checkbox"
                      checked={row.schemaEnabled}
                      onChange={(event) =>
                        change(row.key, { schemaEnabled: event.target.checked })
                      }
                    />
                    응답 스키마 확인
                  </label>
                  {row.schemaEnabled && (
                    <SchemaField
                      row={row}
                      change={(values) => change(row.key, values)}
                    />
                  )}
                  <label className="checkbox-label rule-wide">
                    <input
                      type="checkbox"
                      checked={row.ownerEnabled}
                      onChange={(event) =>
                        change(row.key, { ownerEnabled: event.target.checked })
                      }
                    />
                    소유권 필드 확인
                  </label>
                  {row.ownerEnabled && (
                    <>
                      <label>
                        소유권 JSON Pointer
                        <input
                          value={row.pointer}
                          required
                          maxLength={256}
                          onChange={(event) =>
                            change(row.key, { pointer: event.target.value })
                          }
                          placeholder="/tenant_id"
                        />
                      </label>
                      <label>
                        기대 소유권 값
                        <input
                          value={row.expected}
                          required
                          maxLength={200}
                          onChange={(event) =>
                            change(row.key, { expected: event.target.value })
                          }
                          placeholder="예: synthetic-customer-a"
                        />
                      </label>
                      <p className="subtle rule-wide">
                        응답의 지정 필드를 이 문자열과 비교합니다. 기대 값은
                        자산과 보고서에 저장되므로 비밀번호·토큰을 넣지 마세요.
                      </p>
                    </>
                  )}
                </div>
                <button
                  type="button"
                  aria-label={`규칙 ${index + 1} 삭제`}
                  onClick={() => {
                    const remaining = drafts.filter(
                      (item) => item.key !== row.key,
                    );
                    setDrafts(remaining);
                    setFocusKey(
                      remaining[index]?.key ??
                        remaining[index - 1]?.key ??
                        "add",
                    );
                  }}
                >
                  <Trash2 size={15} />
                  규칙 삭제
                </button>
              </fieldset>
            ))}
            <button
              type="button"
              ref={add}
              disabled={drafts.length >= 20}
              onClick={() => {
                const row = blankRule(`rule-${next.current++}`);
                setDrafts((rows) => [...rows, row]);
                setFocusKey(row.key);
              }}
            >
              <Plus size={15} />
              규칙 추가
            </button>
          </>
        )}
        {jsonError && (
          <p id={`${id}-json-error`} className="form-error" role="alert">
            {jsonError}
          </p>
        )}
        <p id={`${id}-help`} className="subtle">
          경로 범위·스키마·소유권 형식의 최종 검사는 서버에서 수행합니다. 정책을
          수정하면 기존 승인 대기 계획을 다시 만들어야 합니다.
        </p>
      </fieldset>
    </details>
  );
}
