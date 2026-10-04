export type CallCostRecord = {
  status: string;
  amount: string|null;
  quote: {
    currency:string; model:string; provider:string; source_url:string;
    as_of:string; input_per_million:string; output_per_million:string;
  }|null;
};

const states: Record<string,string> = {
  usage_unavailable:"보고 사용량이 없어 비용 미확인",
  unconfigured:"가격 설정 없음 · 비용 미확인",
  model_unpriced:"모델·제공자의 가격 없음 · 비용 미확인",
  invalid_configuration:"가격 설정 오류 · 비용 미확인",
};

export function CallCost({cost}: {cost?:CallCostRecord}) {
  return <div className="call-cost">
    <p>{cost?.status === "estimated" && cost.quote ?
      `토큰 비용 추정: ${cost.quote.currency} ${cost.amount}` :
      states[cost?.status || ""] || "비용 기록 없음 · 미확인"}</p>
    {cost?.quote && <details>
      <summary>호출 당시 가격 근거</summary>
      <p>{cost.quote.model} · {cost.quote.currency} · 기준일 {cost.quote.as_of}</p>
      <p>100만 토큰당 입력 {cost.quote.input_per_million} / 출력 {cost.quote.output_per_million}</p>
      <p>제공자: {cost.quote.provider}</p>
      <p>설정한 가격 출처: {cost.quote.source_url}</p>
      <p>운영자가 설정한 단일 입력·출력 단가입니다. 캐시·구간별 요율·추가 요금·할인·세금은 반영하지 않습니다. 실제 청구와 비교하세요.</p>
    </details>}
  </div>;
}
