import { useState } from "react";
import { createRoot } from "react-dom/client";
import { CallHistory, type ProviderCall } from "../../src/CallHistory";
import { useNavigation } from "../../src/navigation";
import "../../src/style.css";
const all: ProviderCall[] = Array.from({ length: 29 }, (_, i) => ({
  id: "synthetic-call-" + i,
  source: i % 2 ? "planner" : "conversation",
  state: i === 0 ? "interrupted" : i === 1 ? "started" : "uncommitted",
  task_id: "synthetic-task",
  actor_id: null,
  model: "synthetic-model-" + "long-".repeat(15),
  provider_origin: "https://provider-fixture.invalid",
  started_at: 1700000000 + i,
  observed_at: 1700000001 + i,
  settled_at: i !== 1 ? 1700000002 + i : undefined,
  outcome: i < 2 ? "unknown" : "accepted",
  tokens: {
    status: i < 2 ? "missing" : "reported",
    prompt_tokens: i < 2 ? null : 20,
    completion_tokens: i < 2 ? null : 10,
    total_tokens: i < 2 ? null : 30,
  },
  cost: {
    status: i < 2 ? "usage_unavailable" : "estimated",
    amount: i < 2 ? null : "0.00005",
    quote: {
      currency: "USD",
      model: "synthetic-model",
      provider: "https://provider-fixture.invalid",
      source_url: "https://price-fixture.invalid/" + "long/".repeat(25),
      as_of: "2026-01-01",
      input_per_million: "1.25",
      output_per_million: "2.5",
    },
  },
}));
let persistentFailure=false;
let fail = false,
  hold = false;
const pending: (() => void)[] = [];
function showPending(){ const output=document.getElementById("pending-calls"); if(output) output.textContent=`보류된 조회: ${pending.length}`; }
const realFetch = window.fetch.bind(window);
window.fetch = async (input, init) => {
  if (!String(input).startsWith("/api/llm/calls"))
    return realFetch(input, init);
  const query = new URL(String(input), location.origin).searchParams;
  const search = query.get("search") || "",
    source = query.get("source"),
    state = query.get("state"),
    task = query.get("task_id");
  const matches = all.filter(
    (call) =>
      (!source || call.source === source) &&
      (!state || call.state === state) &&
      (!task || call.task_id === task) &&
      [call.id, call.model, call.task_id].some((value) =>
        value.includes(search),
      ),
  );
  const offset = Number(query.get("offset") || 0);
  const response = new Response(
    JSON.stringify(
      (fail || persistentFailure)
        ? { detail: "합성 호출 이력 오류" }
        : {
            items: matches.slice(offset, offset + 25),
            total: matches.length,
            limit: 25,
            offset,
            snapshot: 29,
            has_more: offset + 25 < matches.length,
          },
    ),
    {
      status: (fail || persistentFailure) ? 503 : 200,
      headers: { "Content-Type": "application/json" },
    },
  );
  fail = false;
  if (hold) {
    hold = false;
    return new Promise((resolve) => {pending.push(() => {resolve(response);showPending()});showPending();});
  }
  return response;
};
function Review() {
  const navigation = useNavigation(["settings", "tasks"]);
  const [width, setWidth] = useState(390),
    [metrics, setMetrics] = useState(""),
    [task, setTask] = useState("");
  if (new URLSearchParams(location.search).has("frame"))
    return (
      <main style={{ padding: 12 }}>
        <h1>합성 호출 이력 검수</h1>
        <button
          onClick={() => {
            fail = true;
          }}
        >
          다음 조회 오류
        </button>
        <button
          onClick={() => {
            hold = true;
          }}
        >
          다음 조회 지연
        </button>
        <button onClick={() => pending.shift()?.()}>이전 조회 해제</button>
        <button onClick={()=>{persistentFailure=true}}>서버 오류 유지</button><button onClick={()=>{persistentFailure=false}}>서버 복구</button>
        <button onClick={navigation.back}>이전 탐색</button>
        <button onClick={navigation.forward}>다음 탐색</button>
        <p id="pending-calls" role="status">보류된 조회: 0</p>
        <p role="status">선택 작업: {task || "없음"}</p>
        <CallHistory
          state={navigation.callList}
          onChange={navigation.updateCallList}
          onTask={setTask}
        />
      </main>
    );
  return (
    <main style={{ padding: 16 }}>
      <h1>호출 이력 너비 검수</h1>
      {[320, 390, 768].map((value) => (
        <button key={value} onClick={() => setWidth(value)}>
          {value}px
        </button>
      ))}
      <button
        onClick={() => {
          const root =
            document.querySelector("iframe")?.contentDocument?.documentElement;
          setMetrics(
            root
              ? `문서 너비 ${root.clientWidth} / scroll ${root.scrollWidth}`
              : "준비 중",
          );
        }}
      >
        너비 측정
      </button>
      <button
        onClick={() => {
          document
            .querySelector("iframe")
            ?.contentDocument?.querySelectorAll("details")
            .forEach((detail) => {
              detail.open = true;
            });
        }}
      >
        문서 상세 펼치기
      </button>
      <p role="status">{metrics}</p>
      <iframe
        title="합성 호출 이력 문서"
        src="?frame=1&page=settings"
        style={{
          display: "block",
          width,
          height: 950,
          border: "2px solid black",
        }}
      />
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Review />);
