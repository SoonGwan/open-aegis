import { useEffect, useState } from "react";
import { api, captureSession } from "./api";

type Summary = {
  source: "planner"|"conversation"|"all";
  calls: number;
  source_counts: Record<"planner"|"conversation",number>;
  usage_states: Record<"reported"|"partial"|"missing"|"invalid",number>;
  outcomes: Record<"accepted"|"invalid_plan"|"invalid_answer"|"request_failed"|"unknown_outcome",number>;
  reported_tokens: Record<"prompt_tokens"|"completion_tokens"|"total_tokens",string|null>;
};
const count = (value:string|null) => value === null ? "미확인" : value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
export function UsageSummary() {
  const [days,setDays] = useState("");
  const [source,setSource] = useState("all");
  const [retry,setRetry] = useState(0);
  const [data,setData] = useState<Summary|null>(null);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  useEffect(()=>{
    const controller = new AbortController();
    const current = captureSession();
    let active = true;
    setLoading(true);setData(null);setError("");
    void api<Summary>("/llm/usage?source="+source+(days ? "&days="+days : ""),"GET",undefined,controller.signal)
      .then(value=>{
        if(value.source !== source || !value.source_counts) {
          throw new Error("서버와 화면의 사용량 형식이 다릅니다. 같은 릴리스로 업데이트한 뒤 다시 조회하세요.");
        }
        if(active && current()) setData(value);
      })
      .catch(e=>{if(active && current() && !controller.signal.aborted) setError((e as Error).message);})
      .finally(()=>{if(active && current()) setLoading(false);});
    return ()=>{active=false;controller.abort();};
  },[days,source,retry]);
  return <section className="panel settings-panel usage-summary" aria-label="AI 사용량 집계">
    <div className="panel-head"><h3>AI 사용량</h3>
      <label>호출 종류 <select value={source} onChange={e=>setSource(e.target.value)}>
        <option value="all">계획 + 대화</option><option value="planner">계획</option><option value="conversation">대화</option>
      </select></label>
      <label>조회 기간 <select value={days} onChange={e=>setDays(e.target.value)}>
        <option value="">전체 기록</option><option value="7">최근 7일</option><option value="30">최근 30일</option>
      </select></label>
    </div>
    <p className="subtle">작업별 마지막 계획 호출과 저장된 AI 대화 답변을 집계합니다. 사용량 기록이 없는 과거 데이터와 저장되지 않은 호출은 제외합니다.</p>
    {loading ? <p role="status">사용량을 불러오는 중…</p> : error ? <p className="form-error" role="alert">{error}</p> : data && <>
      <div className="setting-row"><span>기록된 호출</span><strong>{data.calls.toLocaleString("ko-KR")}개</strong></div>
      <div className="setting-row"><span>계획 / 대화</span><strong>{data.source_counts.planner} / {data.source_counts.conversation}</strong></div>
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
      <p className="subtle">형식과 합계가 검증된 보고값만 합산합니다. 계획·대화가 거절된 호출도 포함됩니다. 청구 확인·비용 추정은 제공하지 않습니다.</p>
    </>}
    <button type="button" disabled={loading} onClick={()=>setRetry(value=>value+1)}>{error ? "다시 조회" : "새로 조회"}</button>
  </section>;
}
