import { useEffect, useState } from "react";
import { api, captureSession } from "./api";

type Summary = {
  source: "planner"|"conversation"|"all";
  ledger?: "persisted"|"attempts";
  attempt_states?: Record<"started"|"observed"|"committed"|"uncommitted"|"interrupted",number>|null;
  calls: number;
  source_counts: Record<"planner"|"conversation",number>;
  costs?: {
    states: Record<string,number>;
    totals: {currency:string; amount:string; calls:number}[];
  };
  usage_states: Record<"reported"|"partial"|"missing"|"invalid",number>;
  outcomes: Record<"accepted"|"invalid_plan"|"invalid_answer"|"request_failed"|"unknown_outcome",number>;
  reported_tokens: Record<"prompt_tokens"|"completion_tokens"|"total_tokens",string|null>;
};
const count = (value:string|null) => value === null ? "미확인" : value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
export function UsageSummary() {
  const [days,setDays] = useState("");
  const [source,setSource] = useState("all");
  const [ledger,setLedger] = useState("persisted");
  const [retry,setRetry] = useState(0);
  const [data,setData] = useState<Summary|null>(null);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  useEffect(()=>{
    const controller = new AbortController();
    const current = captureSession();
    let active = true;
    setLoading(true);setData(null);setError("");
    void api<Summary>("/llm/usage?source="+source+"&ledger="+ledger+(days ? "&days="+days : ""),"GET",undefined,controller.signal)
      .then(value=>{
        if(value.source !== source || !value.source_counts || (ledger === "attempts" && (value.ledger !== ledger || !value.attempt_states))) {
          throw new Error("서버와 화면의 사용량 형식이 다릅니다. 같은 릴리스로 업데이트한 뒤 다시 조회하세요.");
        }
        if(active && current()) setData(value);
      })
      .catch(e=>{if(active && current() && !controller.signal.aborted) setError((e as Error).message);})
      .finally(()=>{if(active && current()) setLoading(false);});
    return ()=>{active=false;controller.abort();};
  },[days,source,ledger,retry]);
  return <section className="panel settings-panel usage-summary" aria-label="AI 사용량 집계">
    <div className="panel-head"><h3>AI 사용량</h3>
      <label>집계 기준 <select value={ledger} onChange={e=>setLedger(e.target.value)}>
        <option value="persisted">저장된 계획·답변</option><option value="attempts">호출 시도 기록</option>
      </select></label>
      <label>호출 종류 <select value={source} onChange={e=>setSource(e.target.value)}>
        <option value="all">계획 + 대화</option><option value="planner">계획</option><option value="conversation">대화</option>
      </select></label>
      <label>조회 기간 <select value={days} onChange={e=>setDays(e.target.value)}>
        <option value="">전체 기록</option><option value="7">최근 7일</option><option value="30">최근 30일</option>
      </select></label>
    </div>
    <p className="subtle">{ledger === "persisted" ?
      "작업별 마지막 계획 호출과 저장된 AI 대화 답변을 집계합니다. 사용량 기록이 없는 과거 데이터와 저장되지 않은 호출은 제외합니다." :
      "새 호출의 시도 기록을 시작 시각으로 집계합니다. 답변·계획에 저장하지 못한 호출도 포함합니다. 도입 전 과거 호출은 소급하지 않으며 실제 제공자 청구와 비교해야 합니다."}</p>
    {loading ? <p role="status">사용량을 불러오는 중…</p> : error ? <p className="form-error" role="alert">{error}</p> : data && <>
      <div className="setting-row"><span>기록된 호출</span><strong>{data.calls.toLocaleString("ko-KR")}개</strong></div>
      <div className="setting-row"><span>계획 / 대화</span><strong>{data.source_counts.planner} / {data.source_counts.conversation}</strong></div>
      {ledger === "attempts" && data.attempt_states && <>
        <div className="setting-row"><span>호출 중 / 응답 관찰·저장 미확정</span><strong>{data.attempt_states.started} / {data.attempt_states.observed}</strong></div>
        <div className="setting-row"><span>결과 저장 / 미저장 / 재시작 중단</span><strong>{data.attempt_states.committed} / {data.attempt_states.uncommitted} / {data.attempt_states.interrupted}</strong></div>
        <p className="subtle">수용은 응답 형식 검증 결과입니다. 결과 미저장·중단도 청구가 발생할 수 있으며, 미확인 사용량은 0으로 계산하지 않습니다.</p>
      </>}
      <div className="setting-row"><span>형식 검증 / 일부 / 누락 / 오류</span><strong>
        {data.usage_states.reported} / {data.usage_states.partial} / {data.usage_states.missing} / {data.usage_states.invalid}
      </strong></div>
      <div className="setting-row"><span>수용 / 계획 거절 / 대화 거절 / 응답 실패</span><strong>
        {data.outcomes.accepted} / {data.outcomes.invalid_plan} / {data.outcomes.invalid_answer} / {data.outcomes.request_failed}
      </strong></div>
      {data.outcomes.unknown_outcome > 0 && <p>확인되지 않은 결과: {data.outcomes.unknown_outcome}개</p>}
      {([["입력 토큰",data.reported_tokens.prompt_tokens],["출력 토큰",data.reported_tokens.completion_tokens],
        ["합계 토큰",data.reported_tokens.total_tokens]] as const).map(([label,value])=><div className="setting-row" key={label}>
        <span>{label}</span><strong>{count(value)}</strong></div>)}
      <p className="subtle">형식과 합계가 검증된 보고값만 합산합니다. 계획·대화가 거절된 호출도 포함됩니다.</p>
      <h4 className="detail-heading">토큰 비용 추정</h4>
      {data.costs ? <>
        <div className="setting-row"><span>계산 가능 / 미확인</span><strong>{data.costs.states.estimated} / {data.calls-data.costs.states.estimated}개</strong></div>
        {data.costs.totals.map(total=><div className="setting-row" key={total.currency}>
          <span>{total.currency} · {total.calls}개 호출</span><strong>{total.amount}</strong>
        </div>)}
        {data.costs.totals.length === 0 && <p className="subtle">계산 가능한 가격·사용량 기록이 없습니다. 비용은 미확인입니다.</p>}
        {data.costs.states.invalid_configuration > 0 && <p className="form-error">가격 설정 오류: {data.costs.states.invalid_configuration}개 호출</p>}
        {data.costs.states.invalid_record > 0 && <p className="form-error">비용 기록 검증 오류: {data.costs.states.invalid_record}개 호출</p>}
      </> : <p className="subtle">이 서버 응답에는 비용 집계가 없습니다.</p>}
      <p className="subtle">호출 당시 설정한 입력·출력 단가로 추정한 부분 합계입니다. 통화별로 표시하며 가격·사용량이 없는 호출, 캐시·추가 요금·할인·세금은 반영하지 않습니다. 실제 청구와 비교하세요.</p>
    </>}
    <button type="button" disabled={loading} onClick={()=>setRetry(value=>value+1)}>{error ? "다시 조회" : "새로 조회"}</button>
  </section>;
}
