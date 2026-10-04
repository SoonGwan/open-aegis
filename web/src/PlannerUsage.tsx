export type PlannerCall = {
  model: string;
  outcome: "accepted" | "invalid_plan" | "request_failed";
  observed_at: number;
  tokens: {
    status: "reported" | "partial" | "missing" | "invalid";
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  };
};

export function PlannerUsage({call}: {call: PlannerCall}) {
  const states = {
    reported: "제공자 보고값 · 형식 검증됨",
    partial: "일부 사용량만 보고됨",
    missing: "사용량이 보고되지 않음",
    invalid: "사용량 형식 또는 합계 불일치",
  };
  const outcomes = {
    accepted: "AI 계획 수용",
    invalid_plan: "계획 검증 실패 · 규칙 계획 사용",
    request_failed: "호출 응답 확인 실패 · 규칙 계획 사용",
  };
  return (
    <section className="planner-usage" aria-label="AI 계획 사용량">
      <h4 className="detail-heading">AI 계획 사용량</h4>
      <p>{call.model} · {outcomes[call.outcome]}</p>
      <p>{states[call.tokens.status]}</p>
      <dl>
        {([["입력",call.tokens.prompt_tokens], ["출력",call.tokens.completion_tokens],
          ["합계",call.tokens.total_tokens]] as const).map(([label,value]) => (
          <div key={label}><dt>{label} 토큰</dt><dd>{value === null ? "미확인" : value.toLocaleString("ko-KR")}</dd></div>
        ))}
      </dl>
      <p className="subtle">제공자가 반환한 값입니다. 청구 확인이나 비용 추정은 제공하지 않습니다.</p>
    </section>
  );
}
