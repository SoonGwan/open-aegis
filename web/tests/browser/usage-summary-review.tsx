import { useState } from "react";
import { createRoot } from "react-dom/client";
import { UsageSummary } from "../../src/UsageSummary";
import "../../src/style.css";

let failNext = false;
let holdNext = false;
const pending: (()=>void)[] = [];
const pendingLabels: string[] = [];
const recentRequests: string[] = [];
function showRequests() {
  const output=document.getElementById('summary-fixture-requests');
  if(output) output.textContent=`대기: ${pendingLabels.join(', ') || '없음'} · 최근 요청: ${recentRequests.slice(-6).join(', ')}`;
}
const originalFetch = window.fetch.bind(window);
window.fetch = async (input,init) => {
  if (!String(input).startsWith("/api/llm/usage")) return originalFetch(input,init);
  const days = new URL(String(input),location.origin).searchParams.get("days");
  const zero = days === "7";
  const missing = days === "30";
  const body = failNext ? {detail:"합성 집계 조회 실패"} : {
    calls:zero ? 0 : missing ? 1 : 2102,
    usage_states:{reported:zero || missing ? 0 : 2100,partial:zero || missing ? 0 : 1,missing:zero ? 0 : 1,invalid:0},
    outcomes:{accepted:zero || missing ? 0 : 2101,invalid_plan:0,request_failed:zero ? 0 : 1,unknown_outcome:0},
    reported_tokens:{prompt_tokens:zero || missing ? null : "18915118434956081100",
      completion_tokens:zero || missing ? null : "0",total_tokens:zero || missing ? null : "18915118434956081100"},
  };
  const response = new Response(JSON.stringify(body),{status:failNext ? 503 : 200,headers:{"Content-Type":"application/json"}});
  const label=`${days || 'all'} HTTP ${response.status}`;
  recentRequests.push(label);
  if(recentRequests.length>6) recentRequests.shift();
  failNext=false;
  if(holdNext) {holdNext=false;return new Promise(resolve=>{
    pending.push(()=>resolve(response));pendingLabels.push(label);showRequests();
  });}
  showRequests();
  return response;
};
function Review() {
  const [width,setWidth] = useState(390);
  const [metrics,setMetrics] = useState("");
  if(new URLSearchParams(location.search).has("frame")) return <main style={{padding:12}}>
    <h1>합성 사용량 집계 검수</h1>
    <button onClick={()=>{failNext=true;}}>다음 조회 오류</button>
    <button onClick={()=>{holdNext=true;}}>다음 조회 지연</button>
    <button onClick={()=>{pending.shift()?.();pendingLabels.shift();showRequests();}}>이전 조회 해제</button>
    <p id="summary-fixture-requests" role="status">대기: 없음</p>
    <UsageSummary />
  </main>;
  return <main style={{padding:16}}><h1>집계 너비 검수</h1>
    {[320,390,768].map(value=><button key={value} onClick={()=>{setWidth(value);setMetrics("");}}>{value}px</button>)}
    <button onClick={()=>{const root=document.querySelector("iframe")?.contentDocument?.documentElement;
      setMetrics(root ? `문서 너비 ${root.clientWidth} / scroll ${root.scrollWidth}` : "준비 중");}}>너비 측정</button>
    <p role="status">{metrics}</p><iframe title="합성 집계 문서" src="?frame=1"
      style={{width,height:900,boxSizing:"content-box",border:"2px solid black",display:"block"}} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<Review />);
