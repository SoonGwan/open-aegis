import { t as uiText, localizeLabels } from "./i18n-core.ts";
export type CallCostRecord = {
  status: string;
  amount: string|null;
  quote: {
    currency:string; model:string; provider:string; source_url:string;
    as_of:string; input_per_million:string; output_per_million:string;
  }|null;
};

const states: Record<string,string> = localizeLabels({
  usage_unavailable:"보고 사용량이 없어 비용 미확인",
  unconfigured:"가격 설정 없음 · 비용 미확인",
  model_unpriced:"모델·제공자의 가격 없음 · 비용 미확인",
  invalid_configuration:"가격 설정 오류 · 비용 미확인",
});

export function CallCost({cost}: {cost?:CallCostRecord}) {
  return <div className="call-cost">
    <p>{cost?.status === "estimated" && cost.quote ?
      uiText("토큰 비용 추정: {0} {1}", [cost.quote.currency, cost.amount]) :
      states[cost?.status || ""] || uiText("비용 기록 없음 · 미확인")}</p>
    {cost?.quote && <details>
      <summary>{uiText("호출 당시 가격 근거")}</summary>
      <p>{cost.quote.model} · {cost.quote.currency} {uiText(" · 기준일 ")}{cost.quote.as_of}</p>
      <p>{uiText("100만 토큰당 입력 ")}{cost.quote.input_per_million} {uiText(" / 출력 ")}{cost.quote.output_per_million}</p>
      <p>{uiText("제공자: ")}{cost.quote.provider}</p>
      <p>{uiText("설정한 가격 출처: ")}{cost.quote.source_url}</p>
      <p>{uiText("운영자가 설정한 단일 입력·출력 단가입니다. 캐시·구간별 요율·추가 요금·할인·세금은 반영하지 않습니다. 실제 청구와 비교하세요.")}</p>
    </details>}
  </div>;
}
