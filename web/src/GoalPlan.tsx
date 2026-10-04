import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import { pendingStorage } from "./chat-pending";
import { PlannerUsage, type PlannerCall } from "./PlannerUsage";
import { WorkerDependencies } from "./WorkerDependencies";

type Objective = {
  id: string;
  title: string;
  rationale: string;
  asset_ids: string[];
  checks: string[];
  expected_evidence: string;
  missing_inputs: string[];
};
export type GoalPlan = {
  goal: string;
  mode: string;
  fingerprint: string;
  execution?: "objective_pairs";
  decomposition: {
    objectives: Objective[];
    worker_dependencies: Record<string, string[]>;
  };
  draft_id?: string;
};
type Draft = GoalPlan & {
  basis: { assets: { id: string; name: string; url: string }[] };
  id: string;
  state: string;
  accepted_task_id?: string;
  llm_usage?: PlannerCall | null;
};
type Input = { request_id: string; goal: string; mode: "rules" | "ai" };
const key = (actor: string, task: string) =>
  "aegis:goal-draft:" + JSON.stringify([actor, task]);
function read(actor: string, task: string): Input | null {
  try {
    const raw = pendingStorage()?.getItem(key(actor, task));
    if (!raw || raw.length > 12000) return null;
    const value = JSON.parse(raw) as Input;
    if (
      typeof value.goal !== "string" ||
      !value.goal.trim() ||
      value.goal.length > 2000 ||
      !/^[a-f0-9]{32}$/.test(value.request_id) ||
      !["rules", "ai"].includes(value.mode)
    )
      return null;
    return { request_id: value.request_id, goal: value.goal, mode: value.mode };
  } catch {
    return null;
  }
}

export function GoalPlanSummary({
  plan,
  names,
  assets = [],
}: {
  plan?: GoalPlan;
  names: Record<string, string>;
  assets?: { id: string; name: string; url?: string }[];
}) {
  if (!plan) return null;
  return (
    <section
      className="next-plan observation-execution"
      aria-label="목표 분해 계획"
    >
      <h4>목표 분해 계획</h4>
      <p>
        {plan.mode === "ai"
          ? "AI 목표 분해 초안"
          : plan.mode === "rules_fallback"
            ? "AI 초안을 확인하지 못해 등록 도구별 규칙 초안으로 복구했습니다."
            : "등록 도구별 규칙 초안 · 자연어 의미 분석은 수행하지 않았습니다."}
      </p>
      <p>
        기대 근거와 설명은 검토할 계획이며 검증된 사실이나 목표 달성 판정이
        아닙니다.
      </p>
      <p>
        {plan.execution === "objective_pairs"
          ? "각 과제에 지정한 자산과 검사의 조합만 실행합니다. 여러 과제가 요청한 동일 조합은 한 번 실행하고 결과를 함께 사용합니다."
          : "이전 계획은 선택한 자산 × 선택한 도구의 전체 조합을 검사합니다. 과제별로 적힌 조합보다 넓을 수 있으므로 승인 범위와 결과표를 함께 검토하세요."}
      </p>
      {plan.decomposition.objectives.map((row) => (
        <article key={row.id}>
          <h5>{row.title}</h5>
          <p>{row.rationale}</p>
          <p>
            자산:{" "}
            {row.asset_ids
              .map((id) => assets.find((a) => a.id === id)?.name || id)
              .join(", ")}
          </p>
          <p>검사: {row.checks.map((c) => names[c] || c).join(", ")}</p>
          <p>기대 근거(미검증): {row.expected_evidence}</p>
          {!!row.missing_inputs.length && (
            <p>필요한 입력·추가 확인: {row.missing_inputs.join(" · ")}</p>
          )}
        </article>
      ))}
      <WorkerDependencies
        dependencies={plan.decomposition.worker_dependencies}
        assets={assets}
      />
    </section>
  );
}

export function GoalDraftPanel({
  taskId,
  actorId,
  initialGoal,
  names,
  busy,
  canOperate,
  captureView,
  onAccept,
}: {
  taskId: string;
  actorId: string;
  initialGoal: string;
  names: Record<string, string>;
  busy: boolean;
  canOperate: boolean;
  captureView: () => () => boolean;
  onAccept: (
    id: string,
    fingerprint: string,
    onFailure: (message: string) => void,
  ) => Promise<unknown>;
}) {
  const [pending, setPending] = useState(() => read(actorId, taskId));
  const [goal, setGoal] = useState(pending?.goal || initialGoal),
    [mode, setMode] = useState<"rules" | "ai">(pending?.mode || "rules");
  const [draft, setDraft] = useState<Draft | null>(null),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const active = useRef(true),
    locked = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  async function generate() {
    if (locked.current || busy || !canOperate || !goal.trim()) return;
    const request = pending || {
      request_id: crypto.randomUUID().replaceAll("-", ""),
      goal: goal.trim(),
      mode,
    };
    try {
      const storage = pendingStorage();
      if (!storage) throw new Error();
      storage.setItem(key(actorId, taskId), JSON.stringify(request));
    } catch {
      setError(
        "초안 요청 복구 정보를 저장하지 못했습니다. 브라우저 저장소를 확인하세요.",
      );
      return;
    }
    locked.current = true;
    setSaving(true);
    setPending(request);
    setError("");
    const view = captureView(),
      session = captureSession();
    try {
      const result = await api<Draft>(
        "/tasks/" + encodeURIComponent(taskId) + "/goal-plans",
        "POST",
        request,
      );
      if (active.current && view() && session()) setDraft(result);
    } catch (err) {
      if (active.current && view() && session()) {
        if (err instanceof ApiError && err.status === 409 && !draft) {
          try {
            pendingStorage()?.removeItem(key(actorId, taskId));
          } catch {
            /* Same-request replay remains safe. */
          }
          setPending(null);
        }
        setError(err instanceof Error ? err.message : "초안 조회 실패");
      }
    } finally {
      locked.current = false;
      if (active.current) setSaving(false);
    }
  }
  async function accept() {
    if (locked.current || busy || !canOperate || draft?.state !== "ready")
      return;
    locked.current = true;
    setSaving(true);
    setError("");
    try {
      await onAccept(draft.id, draft.fingerprint, (message) => {
        if (active.current) setError(message);
      });
    } finally {
      locked.current = false;
      if (active.current) setSaving(false);
    }
  }
  function reset() {
    if (saving || busy || (pending && !draft)) return;
    try {
      pendingStorage()?.removeItem(key(actorId, taskId));
    } catch {
      setError("저장한 요청 정보를 정리하지 못했습니다.");
      return;
    }
    setPending(null);
    setDraft(null);
    setError("");
  }
  return (
    <section
      className="next-plan observation-execution goal-draft"
      aria-label="목표 계획 초안"
    >
      <h4>목표를 검증 과제로 나누기</h4>
      <p>
        목표를 과제·자산·도구·필요한 입력으로 정리합니다. 초안 생성은 대상
        요청이나 실행 승인이 아닙니다.
      </p>
      <fieldset disabled={busy || saving || !!pending || !canOperate}>
        <legend>초안 입력</legend>
        <label>
          검증 목표
          <textarea
            maxLength={2000}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
        </label>
        <label>
          초안 방식
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as "rules" | "ai")}
          >
            <option value="rules">규칙 · 등록 도구별 검토 목록</option>
            <option value="ai">AI · 자연어 목표 분해</option>
          </select>
        </label>
      </fieldset>
      <p>
        AI 방식은 입력한 목표·자산 이름/유형/ID·공유 할 일·관찰 유형을 설정된
        제공자에게 전송하며 호출 비용이 발생할 수 있습니다. URL 원문·응답·인증
        값은 자동 전송하지 않습니다.
      </p>
      {error && <p role="alert">{error}</p>}
      {pending && !draft && (
        <p role="status">
          저장한 요청 ID로 미확인 결과를 확인합니다. 같은 요청은 제공자를 다시
          호출하지 않습니다.
        </p>
      )}
      <button
        type="button"
        disabled={busy || saving || !canOperate || !goal.trim()}
        onClick={() => void generate()}
      >
        {saving
          ? "처리 중…"
          : pending
            ? "같은 요청으로 초안 확인"
            : "목표 초안 만들기"}
      </button>
      {draft?.state === "ready" && (
        <>
          <GoalPlanSummary
            plan={draft}
            names={names}
            assets={draft.basis.assets}
          />
          {draft.llm_usage && <PlannerUsage call={draft.llm_usage} />}
          <p>
            반영하면 별도의 승인 대기 작업이 생깁니다. 기존 작업은 유지됩니다.
            실행 전에 선택한 범위·도구·의존 관계를 검토하세요.
          </p>
          <button
            type="button"
            disabled={busy || saving || !canOperate}
            onClick={() => void accept()}
          >
            {draft.accepted_task_id
              ? "반영된 계획 확인"
              : "검토한 초안을 승인 대기 계획으로 반영"}
          </button>
        </>
      )}
      {draft?.state === "generating" && (
        <p role="status">
          이 요청의 생성 완료를 확인할 수 없습니다. 같은 요청으로 상태를
          확인하세요. 재시작 복구는 제공자를 다시 호출하지 않습니다.
        </p>
      )}
      {draft?.state === "interrupted" && (
        <p role="alert">
          초안 저장이 중단되었습니다. 이전 호출 결과를 확정할 수 없어 같은
          요청으로 AI를 재호출하지 않습니다. 새 초안을 준비할 수 있습니다.
        </p>
      )}
      {(!pending ||
        draft?.state === "ready" ||
        draft?.state === "interrupted") && (
        <button
          type="button"
          disabled={busy || saving || !canOperate}
          onClick={reset}
        >
          새 초안 준비
        </button>
      )}
      {!canOperate && (
        <p>관리자 또는 운영자가 초안을 만들고 반영할 수 있습니다.</p>
      )}
    </section>
  );
}

export function GoalProgress({
  taskId,
  captureView,
  onFinding,
  onTask,
  actorId, canOperate, busy, onRetest,
}: {
  taskId: string;
  captureView: () => () => boolean;
  onFinding: (id: string) => void;
  onTask: (id: string) => void;
  actorId:string; canOperate:boolean; busy:boolean;
  onRetest:(path:string,requestId:string,onFailure:(message:string)=>void)=>Promise<boolean>;
}) {
  const [rows, setRows] = useState<
    { id: string; title: string; completed: number; expected: number }[] | null
  >(null);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const active = useRef(true),
    locked = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  async function load() {
    if (locked.current) return;
    locked.current = true;
    setLoading(true);
    setError("");
    const view = captureView(),
      session = captureSession();
    try {
      const result = await api<{
        objectives: {
          id: string;
          title: string;
          completed: number;
          expected: number;
        }[];
      }>("/tasks/" + encodeURIComponent(taskId) + "/goal-progress");
      if (active.current && view() && session()) setRows(result.objectives);
    } catch (err) {
      if (active.current && view() && session())
        setError(err instanceof Error ? err.message : "조회 실패");
    } finally {
      locked.current = false;
      if (active.current) setLoading(false);
    }
  }
  return (
    <section className="next-plan" aria-label="목표 과제의 검사 진행률">
      <h4>과제별 검사 진행률</h4>
      <p>
        연결된 도구·자산의 실행 완료만 집계합니다. 자연어 목표 달성이나 기대
        근거의 사실성을 판정하지 않습니다.
      </p>
      <button type="button" disabled={loading} onClick={() => void load()}>
        {loading ? "조회 중…" : "과제 검사 결과 확인"}
      </button>
      {error && <p role="alert">{error}</p>}
      {rows?.map((row) => (
        <article key={row.id}>
          <p>{row.title} · 검사 완료 {row.completed}/{row.expected}</p>
          <GoalObjectiveFindings taskId={taskId} objectiveId={row.id} title={row.title}
            captureView={captureView} onFinding={onFinding} onTask={onTask} actorId={actorId} canOperate={canOperate} busy={busy} onRetest={onRetest} />
        </article>
      ))}
    </section>
  );
}

type GoalFindingPage = {
  items: { id: string; title: string; asset_name: string; check: string;
    status: string; evidence_count: number; retests_count: number;
    latest_retest: { task_id: string; conclusion: string; triage_effect: string } | null }[];
  total: number; limit: number; offset: number; snapshot: number; has_more: boolean;
};
function GoalObjectiveFindings({taskId,objectiveId,title,captureView,onFinding,onTask,actorId,canOperate,busy,onRetest}: {
  taskId:string; objectiveId:string; title:string; captureView:()=>()=>boolean;
  onFinding:(id:string)=>void; onTask:(id:string)=>void;
  actorId:string;canOperate:boolean;busy:boolean;
  onRetest:(path:string,requestId:string,onFailure:(message:string)=>void)=>Promise<boolean>;
}) {
  const [page,setPage]=useState<GoalFindingPage|null>(null);
  const [search,setSearch]=useState("");
  const [applied,setApplied]=useState("");
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  const active=useRef(true),locked=useRef(false);
  useEffect(()=>{active.current=true;return()=>{active.current=false;};},[]);
  async function load(offset=0,snapshot?:number,query=search) {
    if(locked.current)return;
    locked.current=true;setLoading(true);setError("");
    const view=captureView(),session=captureSession();
    try {
      const params=new URLSearchParams({limit:"25",offset:String(offset),search:query});
      if(snapshot!==undefined)params.set("snapshot",String(snapshot));
      const result=await api<GoalFindingPage>("/tasks/"+encodeURIComponent(taskId)+"/goal-objectives/"+encodeURIComponent(objectiveId)+"/findings?"+params);
      if(active.current&&view()&&session()){setPage(result);setApplied(query);}
    } catch(err) {
      if(active.current&&view()&&session())setError(err instanceof Error?err.message:"근거 조회 실패");
    } finally {locked.current=false;if(active.current)setLoading(false);}
  }
  return <section className="goal-objective-evidence" aria-label={title+" 근거와 재검증"}>
    <button type="button" disabled={loading} onClick={()=>void load()}>
      {loading?"조회 중…":"근거·재검증 확인"}
    </button>
    {error&&<p role="alert">{error}</p>}
    {page&&<>
      <p>이 작업에서 기록한 증거가 일치하는 발견과 해당 발견의 별도 승인 재검증입니다. 재검증 결과는 원래 목표의 완료율을 변경하지 않습니다.</p>
      <form aria-label={title+" 발견 검색"} onSubmit={e=>{e.preventDefault();void load();}}>
        <label>발견 제목 검색<input value={search} maxLength={200} disabled={loading} onChange={e=>setSearch(e.target.value)} /></label>
        <button type="submit" disabled={loading}>검색</button>
      </form>
      <p role="status">{page.total?`${page.offset+1}–${page.offset+page.items.length} / 전체 ${page.total}개`:"일치하는 발견이 없습니다. 발견이 없다는 사실만으로 목표 달성을 판정하지 않습니다."}</p>
      {page.items.map(row=><article key={row.id}>
        <p><strong>{row.title}</strong> · {row.asset_name} · 원본 증거 {row.evidence_count}개</p>
        <p>연결된 재검증 {row.retests_count}개{row.latest_retest?" · 최근 결과: "+({resolved:"해결 확인",reproduced:"재현",inconclusive:"판정 불가"} as Record<string,string>)[row.latest_retest.conclusion]:""}</p>
        {row.latest_retest?.triage_effect==="conflict"&&<p>재검증 조치 충돌 기록을 확인하세요. 자동 조치 상태 변경은 적용하지 않았습니다.</p>}
        <button type="button" onClick={()=>onFinding(row.id)} aria-label={row.title+" 발견·재검증 이력 열기"}>발견·재검증 이력 열기</button>
        {canOperate&&<GoalRetestButton actorId={actorId} taskId={taskId} objectiveId={objectiveId} findingId={row.id} busy={busy} onRetest={onRetest} />}
        {row.latest_retest&&<button type="button" onClick={()=>onTask(row.latest_retest!.task_id)} aria-label={row.title+" 최근 재검증 작업 열기"}>최근 재검증 작업 열기</button>}
      </article>)}
      <nav aria-label={title+" 근거 목록 페이지"}>
        <button type="button" disabled={loading||page.offset===0} onClick={()=>void load(Math.max(0,page.offset-page.limit),page.snapshot,applied)}>이전</button>
        <button type="button" disabled={loading||!page.has_more} onClick={()=>void load(page.offset+page.limit,page.snapshot,applied)}>다음</button>
        <button type="button" disabled={loading} onClick={()=>void load(0,undefined,applied)}>최신 목록</button>
      </nav>
    </>}
  </section>;
}

function GoalRetestButton({actorId,taskId,objectiveId,findingId,busy,onRetest}:{
  actorId:string;taskId:string;objectiveId:string;findingId:string;busy:boolean;
  onRetest:(path:string,requestId:string,onFailure:(message:string)=>void)=>Promise<boolean>;
}) {
  const storageKey="aegis:goal-retest:"+JSON.stringify([actorId,taskId,objectiveId,findingId]);
  const [pending,setPending]=useState(()=>{try{const value=pendingStorage()?.getItem(storageKey);return value&&/^[a-f0-9]{32}$/.test(value)?value:null;}catch{return null;}});
  const [saving,setSaving]=useState(false),[error,setError]=useState("");
  const locked=useRef(false),active=useRef(true);
  useEffect(()=>{active.current=true;return()=>{active.current=false;};},[]);
  async function create(){
    if(locked.current||busy)return;
    locked.current=true;setSaving(true);setError("");
    try {
      const requestId=pending||crypto.randomUUID().replaceAll("-","");
      const storage=pendingStorage();if(!storage)throw new Error("복구 저장소를 사용할 수 없습니다.");
      storage.setItem(storageKey,requestId);setPending(requestId);
      const path="/tasks/"+encodeURIComponent(taskId)+"/goal-objectives/"+encodeURIComponent(objectiveId)+"/findings/"+encodeURIComponent(findingId)+"/retest";
      const success=await onRetest(path,requestId,message=>{if(active.current)setError(message);});
      if(success){storage.removeItem(storageKey);if(active.current)setPending(null);}
    }catch(err){if(active.current)setError(err instanceof Error?err.message:"재검증 계획 생성 실패");}
    finally{locked.current=false;if(active.current)setSaving(false);}
  }
  return <>
    <button type="button" disabled={busy||saving} onClick={()=>void create()}>{saving?"처리 중…":pending?"같은 목표 재검증 요청 확인":"이 과제의 재검증 계획 만들기"}</button>
    {error&&<p role="alert">{error}</p>}
    {pending&&<p>저장한 요청으로 기존 계획을 확인합니다. 실행은 별도 승인이 필요합니다.</p>}
  </>;
}

export type GoalRetestRef = {source_task_id:string;source_task_name:string;objective_title:string;finding_id:string;objective_id:string};
export function GoalRetestOrigin({origin,onTask,onFinding}:{origin?:GoalRetestRef;onTask:(id:string)=>void;onFinding:(id:string)=>void}){
  if(!origin)return null;
  return <section className="next-plan goal-objective-evidence" aria-label="목표 재검증의 원래 과제">
    <h4>원래 목표와 과제</h4>
    <p>{origin.source_task_name} · {origin.objective_title}</p>
    <p>이 과제에서 만든 발견 재검증입니다. 현재 실행 범위를 별도로 승인하며 원래 목표의 완료율이나 목표 달성 판정을 변경하지 않습니다.</p>
    <button type="button" onClick={()=>onTask(origin.source_task_id)}>원래 목표 작업 열기</button>
    <button type="button" onClick={()=>onFinding(origin.finding_id)}>원래 발견 열기</button>
  </section>;
}
