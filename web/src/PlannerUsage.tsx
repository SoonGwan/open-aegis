import { t as uiText, getFormatLocale } from "./i18n-core.ts";
import { CallCost, type CallCostRecord } from "./CallCost";

export type PlannerCall = {
  model: string;
  outcome: "accepted" | "invalid_plan" | "request_failed";
  observed_at: number;
  cost?: CallCostRecord;
  tokens: {
    status: "reported" | "partial" | "missing" | "invalid";
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  };
};

export function PlannerUsage({call}: {call: PlannerCall}) {
  const states = {
    reported: uiText("제공자 보고값 · 형식 검증됨"),
    partial: uiText("일부 사용량만 보고됨"),
    missing: uiText("사용량이 보고되지 않음"),
    invalid: uiText("사용량 형식 또는 합계 불일치"),
  };
  const outcomes = {
    accepted: uiText("AI 계획 수용"),
    invalid_plan: uiText("계획 검증 실패 · 규칙 계획 사용"),
    request_failed: uiText("호출 응답 확인 실패 · 규칙 계획 사용"),
  };
  return (
    <section className="planner-usage" aria-label={uiText("AI 계획 사용량")}>
      <h4 className="detail-heading">{uiText("AI 계획 사용량")}</h4>
      <p>{call.model} · {outcomes[call.outcome]}</p>
      <p>{states[call.tokens.status]}</p>
      <dl>
        {([[uiText("입력"),call.tokens.prompt_tokens], [uiText("출력"),call.tokens.completion_tokens],
          [uiText("합계"),call.tokens.total_tokens]] as const).map(([label,value]) => (
          <div key={label}><dt>{label} {uiText(" 토큰")}</dt><dd>{value === null ? uiText("미확인") : value.toLocaleString(getFormatLocale())}</dd></div>
        ))}
      </dl>
      <CallCost cost={call.cost} />
      <p className="subtle">{uiText("제공자가 반환한 값입니다. 실제 청구를 확인한 기록은 아닙니다.")}</p>
    </section>
  );
}
