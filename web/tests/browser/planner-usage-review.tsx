import { useState } from "react";
import { createRoot } from "react-dom/client";
import { PlannerUsage, type PlannerCall } from "../../src/PlannerUsage";
import "../../src/style.css";

const calls: PlannerCall[] = [
  {model:"owned-synthetic-model",outcome:"accepted",observed_at:1,
   tokens:{status:"reported",prompt_tokens:32,completion_tokens:16,total_tokens:48}},
  {model:"owned-synthetic-model",outcome:"invalid_plan",observed_at:1,
   tokens:{status:"partial",prompt_tokens:32,completion_tokens:null,total_tokens:null}},
  {model:"owned-synthetic-model",outcome:"request_failed",observed_at:1,
   tokens:{status:"missing",prompt_tokens:null,completion_tokens:null,total_tokens:null}},
  {model:"owned-synthetic-model",outcome:"accepted",observed_at:1,
   tokens:{status:"invalid",prompt_tokens:32,completion_tokens:16,total_tokens:49}},
];
function Review() {
  const [width,setWidth] = useState(390);
  const [metrics,setMetrics] = useState("");
  if (new URLSearchParams(location.search).has("frame")) return (
    <main style={{padding:12}}>
      <h1>합성 AI 사용량 표시</h1>
      {calls.map((call,index)=><PlannerUsage key={index} call={call} />)}
    </main>
  );
  return <main style={{padding:16}}>
    <h1>AI 계획 사용량 너비 검수</h1><p>실제 제공자 호출을 하지 않는 합성 표시입니다.</p>
    {[320,390,768].map(value=><button key={value} onClick={()=>{setWidth(value);setMetrics("");}}>{value}px</button>)}
    <button onClick={()=>{
      const root=document.querySelector("iframe")?.contentDocument?.documentElement;
      setMetrics(root ? `문서 너비 ${root.clientWidth} / scroll ${root.scrollWidth}` : "준비 중");
    }}>너비 측정</button><p role="status">{metrics}</p>
    <iframe title="합성 사용량 실제 문서" src="?frame=1" style={{width,height:1200,border:"2px solid black",boxSizing:"content-box",display:"block"}} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<Review />);
