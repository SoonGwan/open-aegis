import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { MessageProvenance, type RecordedProvenance } from "../../src/MessageProvenance";
import "../../src/style.css";

const provenance: RecordedProvenance = {
  version:1, mode:"recorded_rules", observed_at:1791068400, finding_total:12,
  citations:[
    {label:"작업",kind:"task",id:"owned-task",title:"합성 완료 작업",
     snapshot:{status:"completed",assets:2,done:2,completed_checks:12,errors:0}},
    {label:"발견 1",kind:"finding",id:"owned-finding",title:"매우긴합성발견제목".repeat(8),
     snapshot:{severity:"high",asset_name:"소유한 합성 자산",remediation:"수정 안내 ".repeat(30)},
     evidence:{label:"증거 1",id:"owned-proof",task_id:"owned-task",asset_id:"owned-asset",
       check:"security_headers",created_at:1791068400,matching_count:2,truncated:true,
       excerpt:'{"synthetic_text":"<script>이것은 실행되지 않는 합성 문자열입니다</script>"}'.repeat(100).slice(0,4096)}},
    {label:"발견 2",kind:"finding",id:"missing-finding",title:"일치하는 증거가 없는 합성 발견",
     snapshot:{severity:"low",status:"open"},evidence:null},
  ],
};
function Review() {
  useEffect(()=>{const details=document.querySelector('details');if(details) details.open=true;},[]);
  const [width,setWidth]=useState(320);
  const [metrics,setMetrics]=useState("");
  if (new URLSearchParams(location.search).has("frame")) return <main style={{padding:12}}>
    <h1>답변 출처 합성 검수</h1>
    <article className="chat-message assistant"><p>[작업] 완료한 작업. [발견 1] 수정 우선순위 요약.</p>
      <MessageProvenance provenance={provenance} />
    </article>
    <article className="chat-message assistant"><p>과거 답변: 당시 출처 메타데이터 없음.</p><MessageProvenance /></article>
  </main>;
  return <main style={{padding:16}}><h1>답변 출처 너비 검수</h1>
    {[320,390,768].map(value=><button key={value} onClick={()=>{setWidth(value);setMetrics("");}}>{value}px</button>)}
    <button onClick={()=>{const root=document.querySelector("iframe")?.contentDocument?.documentElement;
      setMetrics(root ? `문서 너비 ${root.clientWidth} / scroll ${root.scrollWidth}` : "준비 중");}}>너비 측정</button>
    <p role="status">{metrics}</p>
    <iframe title="합성 출처 실제 문서" src="?frame=1" style={{width,height:1000,border:"2px solid black",boxSizing:"content-box",display:"block"}} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<Review />);
