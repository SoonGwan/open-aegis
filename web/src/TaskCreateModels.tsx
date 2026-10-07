import { t as uiText, localizeLabels, getFormatLocale } from "./i18n-core.ts";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, captureSession } from "./api";
import Modal from "./components/Modal";
import { AssetPicker } from "./records";
import { RemoteExecutionPicker } from "./RemoteExecution";
import { validateWorkerDependencies } from "./worker-dependency-state";
import { loadTaskCreationPending, storeTaskCreationPending, finishTaskCreationPending, clearTaskCreationPending, type PendingTaskCreation, type TaskCreationDraft, type InitialModels } from "./task-model-creation-pending";

type Profile = { id: string; name: string; model: string; revision: number; enabled: boolean; configuration_available: boolean; destination_review_current: boolean; admin_review_current: boolean };
const purposes = ["planner", "conversation"] as const, labels = localizeLabels({ planner: "검증 순서 계획", conversation: "기록 기반 대화" });
const eligible = (profile: Profile) => profile.enabled && profile.configuration_available && profile.destination_review_current && profile.admin_review_current;
const message = (value: unknown) => value instanceof Error ? value.message : uiText("작업 생성 요청을 확인하지 못했습니다.");
const empty = (): TaskCreationDraft => ({ name: "", goal: uiText("등록된 자산의 보안 설정과 접근 권한을 검증합니다."), asset_ids: [], checks: [], workers: 3, planner: "rules", remote_connection_id: null, worker_dependencies: {} });
function Contents({ request }: { request: PendingTaskCreation }) {
  return <><p>{uiText("작성 ")}{new Date(request.created_at).toLocaleString(getFormatLocale())} {uiText(" · 요청 ")}{request.body.request_id}</p><p>{request.body.task.name} {uiText(" · 자산 ")}{request.body.task.asset_ids.length}{uiText("개 · ")}{request.body.task.planner === "ai" ? uiText("AI 계획") : uiText("규칙 기반 계획")}</p><p>{uiText("원래 목표: ")}{request.body.task.goal}</p><p>{uiText("도구: ")}{request.body.task.checks.join(", ")}</p>{purposes.map(purpose => <p key={purpose}>{labels[purpose]}: {request.body.models[purpose] ? uiText("프로필 {0} · 검토 버전 {1}", [request.body.models[purpose]!.profile_id, request.body.models[purpose]!.expected_profile_revision]) : uiText("워크스페이스 용도별 선택 따름")}</p>)}</>;
}

export default function TaskCreateModels({ actorId, canAdmin, tools, onClose, onCreated }: { actorId: string; canAdmin: boolean; tools: { id: string; name: string }[]; onClose: () => void; onCreated: (taskId: string) => void }) {
  const [profiles, setProfiles] = useState<Profile[]>([]), [profileError, setProfileError] = useState(""), [loading, setLoading] = useState(true), [latest, setLatest] = useState<Profile[] | null>(null);
  const [rows, setRows] = useState<PendingTaskCreation[]>([]), [storageError, setStorageError] = useState(""), [current, setCurrent] = useState<PendingTaskCreation | null>(null), [error, setError] = useState(""), [conflict, setConflict] = useState(false), [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<TaskCreationDraft>(empty), [draftKey, setDraftKey] = useState(0), [selected, setSelected] = useState<Record<string, string>>({}), [checks, setChecks] = useState<string[]>(tools.map(tool => tool.id)), [remoteChecks, setRemoteChecks] = useState<string[] | null>(null);
  const pending = useRef<PendingTaskCreation | null>(null), inFlight = useRef(false), lifetime = useRef(0);
  useEffect(() => () => { lifetime.current++; }, []);
  function reload() { try { setRows(loadTaskCreationPending(window.localStorage, actorId));setStorageError(""); } catch (value) { setStorageError(message(value)); } }
  useEffect(() => { reload();window.addEventListener("storage", reload);return () => window.removeEventListener("storage", reload); }, [actorId]);
  async function review(adopt = false) {
    const alive = lifetime.current, session = captureSession();setLoading(true);setProfileError("");
    try {
      const result = await api<{ items: Profile[] }>("/model-profiles?status=all&limit=25");
      if (alive === lifetime.current && session()) { if (adopt) setLatest(result.items);else setProfiles(result.items); }
    } catch (value) { if (alive === lifetime.current && session()) setProfileError(message(value)); }
    finally { if (alive === lifetime.current && session()) setLoading(false); }
  }
  useEffect(() => { void review(); }, []);
  const waiting = rows.length > 0 && !current, locked = busy || !!current || waiting || !!storageError;
  const allowedRemote = useCallback((allowed: string[] | null) => { setRemoteChecks(allowed);if (allowed) setChecks(previous => previous.filter(id => allowed.includes(id))); }, []);
  async function send(body?: { task: TaskCreationDraft; models: InitialModels }) {
    if (inFlight.current || !canAdmin || conflict) return;
    const alive = lifetime.current, session = captureSession();let dispatched = false;
    inFlight.current = true;setBusy(true);setError("");
    try {
      if (storageError) throw new Error(storageError);
      if (!pending.current && loadTaskCreationPending(window.localStorage, actorId).length) throw new Error(uiText("이전 미확인 생성 요청을 먼저 선택하세요."));
      if (!pending.current) {
        if (!body) throw new Error(uiText("생성 입력을 확인하세요."));
        pending.current = { version: 1, actor: actorId, body: { ...JSON.parse(JSON.stringify(body)), request_id: crypto.randomUUID() }, created_at: Date.now() };
      }
      storeTaskCreationPending(window.localStorage, pending.current);setCurrent(pending.current);reload();dispatched = true;
      const result = await api<{ task: { id: string }; replayed: boolean; execution_authorized: boolean }>("/tasks/with-models", "POST", pending.current.body);
      if (alive === lifetime.current && session()) { finishTaskCreationPending(window.localStorage, pending.current);pending.current = null;setCurrent(null);reload();onCreated(result.task.id); }
    } catch (value) {
      if (alive === lifetime.current && session()) {
        setError(message(value));
        if (!dispatched && !current) pending.current = null;
        if (dispatched && value instanceof ApiError && value.status === 409) setConflict(true);
        else if (dispatched && value instanceof ApiError && [400, 404, 422].includes(value.status)) {
          try { if (pending.current) finishTaskCreationPending(window.localStorage, pending.current);pending.current = null;setCurrent(null);reload(); } catch (cleanup) { setError(message(cleanup)); }
        }
      }
    } finally { inFlight.current = false;if (alive === lifetime.current && session()) setBusy(false); }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();const data = new FormData(event.currentTarget);
    try {
      const task: TaskCreationDraft = { name: String(data.get("name") || ""), goal: String(data.get("goal") || ""), asset_ids: data.getAll("asset").map(String), checks,
        workers: Number(data.get("workers")), planner: data.get("planner") === "ai" ? "ai" : "rules", remote_connection_id: String(data.get("remote_connection_id") || "") || null,
        worker_dependencies: JSON.parse(String(data.get("worker_dependencies") || "{}")) };
      validateWorkerDependencies(task.asset_ids, task.worker_dependencies);
      const models: InitialModels = {};
      for (const purpose of purposes) if (selected[purpose]) {
        const profile = profiles.find(row => row.id === selected[purpose]);if (!profile || !eligible(profile)) throw new Error(uiText("현재 활성 프로필을 검토해 선택하세요."));
        models[purpose] = { profile_id: profile.id, expected_profile_revision: profile.revision };
      }
      void send({ task, models });
    } catch (value) { setError(message(value)); }
  }
  function adopt() {
    if (!latest || !pending.current || busy) return;
    try {
      const original = pending.current.body;finishTaskCreationPending(window.localStorage, pending.current);
      setDraft(original.task);setChecks(original.task.checks);setRemoteChecks(null);setDraftKey(value => value + 1);
      setSelected(Object.fromEntries(purposes.map(purpose => [purpose, latest.some(profile => profile.id === original.models[purpose]?.profile_id && eligible(profile)) ? original.models[purpose]!.profile_id : ""])));
      setProfiles(latest);setLatest(null);pending.current = null;setCurrent(null);setConflict(false);setError("");reload();
    } catch (value) { setError(message(value)); }
  }
  function clear() {
    try { clearTaskCreationPending(window.localStorage, actorId);pending.current = null;setCurrent(null);setConflict(false);setError("");reload(); }
    catch (value) { setStorageError(message(value)); }
  }
  return <Modal title={uiText("모델을 선택해 작업 만들기")} subtitle={uiText("최초 계획·이후 기록 대화의 모델을 검토합니다. 실행 승인은 별도입니다.")} onClose={() => { if (!inFlight.current) onClose(); }}>
    <p>{uiText("최소 한 용도의 현재 프로필을 선택하세요. 선택하지 않은 용도는 워크스페이스 기본값을 따릅니다. 반복 예약·후속 작업에는 이 선택을 자동 복사하지 않습니다.")}</p>
    {storageError && <p role="alert">{storageError}</p>}{error && <p role="alert">{error}</p>}{profileError && <p role="alert">{profileError}</p>}
    {waiting && <section className="prompt-card"><h3>{uiText("이전 미확인 생성 요청 ")}{rows.length}{uiText("개")}</h3><p>{uiText("작성 후24시간 보존합니다. 선택만으로 생성하지 않습니다. 원래 요청을 선택해 서버 결과를 확인하세요.")}</p>{rows.map(request => <article key={request.body.request_id}><Contents request={request} /><button disabled={busy || !canAdmin} onClick={() => { pending.current = request;setCurrent(request);setConflict(false);setError(""); }}>{uiText("이 생성 요청을 선택")}</button></article>)}</section>}
    {current && <article className="prompt-card"><h3>{uiText("확인 중인 원래 생성 요청")}</h3><Contents request={current} /><p>{uiText("현재 폼 대신 이 ID·원래 입력으로 결과를 확인합니다. 서버 영수증이 남아 있으면 새 작업을 만들지 않습니다.")}</p>{canAdmin && <button className="primary" disabled={busy || conflict || !!storageError} onClick={() => void send()}>{uiText("같은 요청으로 생성 결과 확인")}</button>}</article>}
    {conflict && <><p>{uiText("원래 요청을 보존했습니다. 작업 목록과 현재 프로필을 확인한 뒤 새 초안을 명시적으로 검토하세요.")}</p><button disabled={busy || loading} onClick={() => void review(true)}>{uiText("최신 생성 모델 검토")}</button></>}
    {latest && <article className="prompt-card"><h3>{uiText("현재 프로필 검토")}</h3>{latest.map(profile => <p key={profile.id}>{profile.name} {uiText(" · 버전 ")}{profile.revision} · {profile.model} · {eligible(profile) ? uiText("선택 가능") : uiText("재검토 필요")}</p>)}<button disabled={busy || !canAdmin} onClick={adopt}>{uiText("원래 작업 입력으로 새 초안 준비")}</button></article>}
    {(rows.length > 0 || current || storageError) && <details><summary>{uiText("생성 요청의 브라우저 기록 정리")}</summary><p>{uiText("현재 계정의 이 생성 기능 기록만 지웁니다. 서버 작업은 남을 수 있습니다. 먼저 작업 목록을 확인하세요. 새 요청은 별도 작업을 만들 수 있습니다.")}</p><button disabled={busy || !canAdmin} onClick={clear}>{uiText("작업 생성의 브라우저 기록 지우기")}</button></details>}
    <form key={draftKey} onSubmit={submit} aria-busy={busy}><fieldset className="submission-fields" disabled={!canAdmin || locked} aria-label={uiText("모델 선택 작업의 등록 내용")}>
      <label>{uiText("작업 이름")}<input name="name" maxLength={120} defaultValue={draft.name} required /></label><label>{uiText("검증 목표")}<textarea name="goal" maxLength={2000} rows={2} defaultValue={draft.goal} /></label>
      <AssetPicker initialId={null} initialSelection={{ selected: Object.fromEntries(draft.asset_ids.map(id => [id, { id, name: uiText("원래 선택 자산 {0}", [id]), url: "" }])), dependencies: draft.worker_dependencies }} />
      <RemoteExecutionPicker initialId={draft.remote_connection_id || ""} disabled={locked} names={Object.fromEntries(tools.map(tool => [tool.id, tool.name]))} onChecks={allowedRemote} />
      <fieldset><legend>{uiText("검증 도구")}</legend>{tools.map(tool => <label className="checkbox-label" key={tool.id}><input type="checkbox" checked={checks.includes(tool.id)} disabled={!!remoteChecks && !remoteChecks.includes(tool.id)} onChange={event => setChecks(previous => event.target.checked ? [...previous, tool.id] : previous.filter(id => id !== tool.id))} />{tool.name}</label>)}</fieldset>
      <div className="form-grid"><label>{uiText("계획 방식")}<select name="planner" defaultValue={draft.planner}><option value="rules">{uiText("규칙 기반")}</option><option value="ai">{uiText("AI 계획")}</option></select></label><label>{uiText("병렬 Worker")}<select name="workers" defaultValue={draft.workers}>{[1, 2, 3, 4].map(count => <option value={count} key={count}>{count}{uiText("개")}</option>)}</select></label></div>
      {purposes.map(purpose => <label key={purpose}>{labels[purpose]} {uiText(" 최초 모델")}<select value={selected[purpose] || ""} onChange={event => setSelected(previous => ({ ...previous, [purpose]: event.target.value }))}><option value="">{uiText("워크스페이스 용도별 선택 따름")}</option>{profiles.map(profile => <option key={profile.id} value={profile.id} disabled={!eligible(profile)}>{profile.name} {uiText(" · 버전 ")}{profile.revision} · {profile.model}{eligible(profile) ? "" : uiText(" · 재검토 필요")}</option>)}</select></label>)}
      <p>{uiText("모델 선택으로 대상 실행을 승인하거나 AI 대화를 활성화하지 않습니다.")}</p><button type="button" disabled={loading} onClick={() => void review()}>{uiText("생성 모델 다시 조회")}</button>
      <button className="primary" disabled={loading || !checks.length || !purposes.some(purpose => selected[purpose])}>{uiText("선택 모델과 승인 대기 작업 생성")}</button>
    </fieldset></form><button disabled={busy} onClick={onClose}>{uiText("닫기")}</button>
  </Modal>;
}
