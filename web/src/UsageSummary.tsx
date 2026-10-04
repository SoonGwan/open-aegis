import { useEffect, useState } from "react";
import { api, captureSession } from "./api";

type Summary = {
  calls: number;
  usage_states: Record<"reported"|"partial"|"missing"|"invalid",number>;
  outcomes: Record<"accepted"|"invalid_plan"|"request_failed"|"unknown_outcome",number>;
  reported_tokens: Record<"prompt_tokens"|"completion_tokens"|"total_tokens",string|null>;
};
const count = (value:string|null) => value === null ? "미확인" : value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
export function UsageSummary() {
  const [days,setDays] = useState("");
  const [retry,setRetry] = useState(0);
  const [data,setData] = useState<Summary|null>(null);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  useEffect(()=>{
    const controller = new AbortController();
    const current = captureSession();
    let active = true;
    setLoading(true);setData(null);setError("");
    void api<Summary>("/llm/usage"+(days ? "?days="+days : ""),"GET",undefined,controller.signal)
      .then(value=>{if(active && current()) setData(value);})
      .catch(e=>{if(active && current() && !controller.signal.aborted) setError((e as Error).message);})
      .finally(()=>{if(active && current()) setLoading(false);});
    return ()=>{active=false;controller.abort();};
  },[days,retry]);
  return <section className="panel settings-panel usage-summary" aria-label="AI 계획 사용량 집계">
    <div className="panel-head"><h3>AI 계획 사용량</h3>
      <label>조회 기간 <select value={days} onChange={e=>setDays(e.target.value)}>
        <option value="">전체 기록</option><option value="7">최근 7일</option><option value="30">최근 30일</option>
      </select></label>
    </div>
    <p className="subtle">작업별 마지막 계획 호출을 집계합니다. 과거 메타데이터 없는 기록은 제외합니다.</p>
    {loading ? <p role="status">사용량을 불러오는 중…</p> : error ? <p className="form-error" role="alert">{error}</p> : data && <>
      <div className="setting-row"><span>기록된 계획 호출</span><strong>{data.calls.toLocaleString("ko-KR")}개</strong></div>
      <div className="setting-row"><span>형식 검증 / 일부 / 누락 / 오류</span><strong>
        {data.usage_states.reported} / {data.usage_states.partial} / {data.usage_states.missing} / {data.usage_states.invalid}
      </strong></div>
      <div className="setting-row"><span>계획 수용 / 계획 거절 / 응답 실패</span><strong>
        {data.outcomes.accepted} / {data.outcomes.invalid_plan} / {data.outcomes.request_failed}
      </strong></div>
      {data.outcomes.unknown_outcome > 0 && <p>확인되지 않은 결과: {data.outcomes.unknown_outcome}개</p>}
      {([["입력 토큰",data.reported_tokens.prompt_tokens],["출력 토큰",data.reported_tokens.completion_tokens],
        ["합계 토큰",data.reported_tokens.total_tokens]] as const).map(([label,value])=><div className="setting-row" key={label}>
        <span>{label}</span><strong>{count(value)}</strong></div>)}
      <p className="subtle">형식과 합계가 검증된 보고값만 합산합니다. 계획이 거절된 호출도 포함됩니다. 청구 확인·비용 추정은 제공하지 않습니다.</p>
    </>}
    <button type="button" disabled={loading} onClick={()=>setRetry(value=>value+1)}>{error ? "다시 조회" : "새로 조회"}</button>
  </section>;
}
