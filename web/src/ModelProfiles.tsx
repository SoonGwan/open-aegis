import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import Modal from "./components/Modal";
import ModelCatalog from "./ModelCatalog";
import { Pagination, RecordState, useRecords } from "./records";
import type { ListPosition, HistoryMode } from "./navigation-state";

type Purpose = "planner" | "conversation";
type Profile = { id: string; name: string; model: string; destination_id: string; enabled: boolean; revision: number; configuration_available: boolean; destination_review_current: boolean; admin_review_current: boolean };
type Selection = { purpose: Purpose; revision: number; profile_id: string | null; profile_revision: number | null; configuration_available: boolean };
type Configuration = { destinations: { id: string; name: string; configuration_available: boolean }[]; defaults: Selection[]; conversation_enabled: boolean };
type Body = Record<string, string | number | boolean | null>;
const names = { planner: "검증 순서 계획", conversation: "기록 기반 대화" };
const message = (error: unknown) => error instanceof Error ? error.message : "요청을 확인할 수 없습니다.";
const eligible = (p: Profile) => p.enabled && p.configuration_available && p.destination_review_current && p.admin_review_current;

// Both profile edits and default selections retain the exact request after a lost response.
export function useReviewedSave(path: string, method: string, onSaved: () => void) {
  const pending = useRef<Body | null>(null), inFlight = useRef(false), lifetime = useRef(0);
  const [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [conflict, setConflict] = useState(false), [error, setError] = useState("");
  useEffect(() => () => { lifetime.current++; }, []);
  async function save(body: Body) {
    if (inFlight.current || conflict) return;
    const alive = lifetime.current, session = captureSession();
    inFlight.current = true; setBusy(true); setError("");
    pending.current ||= { ...body, request_id: crypto.randomUUID() };
    try {
      await api(path, method, pending.current);
      if (alive === lifetime.current && session()) onSaved();
    } catch (error) {
      if (alive === lifetime.current && session()) {
        setError(message(error));
        if (error instanceof ApiError && error.status === 409) { setConflict(true); setUncertain(false); }
        else if (error instanceof ApiError && error.status >= 400 && error.status < 500) { pending.current = null; setUncertain(false); }
        else setUncertain(true);
      }
    } finally { inFlight.current = false; if (alive === lifetime.current && session()) setBusy(false); }
  }
  function reviewed() { pending.current = null; setConflict(false); setUncertain(false); setError(""); }
  return { busy, uncertain, conflict, error, save, reviewed, locked: busy || uncertain || conflict, inFlight };
}
export function SaveStatus({ state }: { state: ReturnType<typeof useReviewedSave> }) {
  return <>{state.error && <p role="alert">{state.error}</p>}{state.uncertain && <p role="status">저장 응답을 확인하지 못했습니다. 같은 요청으로 다시 저장해 결과를 확인하세요.</p>}{state.conflict && <p>초안을 유지했습니다. 현재 설정을 명시적으로 검토한 뒤 다시 저장하세요.</p>}</>;
}
function History({ path }: { path: string }) {
  const rows = useRecords<{ id: string; revision: number; actor: { name: string }; snapshot: { name?: string; model?: string; enabled?: boolean; profile_id?: string | null; profile_revision?: number | null } }>("model-history", "", {}, undefined, path, false);
  return <><h3>버전 이력</h3>{rows.loading || rows.error ? <RecordState records={rows} /> : <><p>{rows.total}개 버전</p>{rows.items.map(row => <details key={row.id}><summary>버전 {row.revision} · {row.actor.name}</summary><p>{row.snapshot.name ? `${row.snapshot.name} · ${row.snapshot.model} · ${row.snapshot.enabled ? "활성" : "비활성"}` : row.snapshot.profile_id ? `${row.snapshot.profile_id} · 프로필 버전 ${row.snapshot.profile_revision}` : "기본 환경 설정"}</p></details>)}<Pagination records={rows} /></>}</>;
}

export default function ModelProfiles({ canAdmin, search, onSearch, status, onStatus, position }: {
  canAdmin: boolean; search: string; onSearch: (value: string) => void; status: string; onStatus: (value: string) => void;
  position: ListPosition & { onPositionChange: (value: ListPosition, mode?: HistoryMode) => void };
}) {
  const records = useRecords<Profile>("model-profiles", search, { status }, position, "/model-profiles");
  const [config, setConfig] = useState<Configuration | null>(null), [profiles, setProfiles] = useState<Profile[]>([]), [error, setError] = useState(""), [nonce, setNonce] = useState(0);
  const [editor, setEditor] = useState<Profile | null | undefined>(), [selection, setSelection] = useState<Selection | null>(null);
  const [catalog, setCatalog] = useState<Profile | null>(null);
  useEffect(() => {
    const changed = () => setNonce(value => value + 1);
    window.addEventListener("aegis-records-changed", changed);
    const timer = window.setInterval(changed, 4000);
    return () => { window.clearInterval(timer); window.removeEventListener("aegis-records-changed", changed); };
  }, []);
  useEffect(() => {
    const controller = new AbortController(); setError("");
    Promise.all([api<Configuration>("/models/configuration", "GET", undefined, controller.signal), api<{ items: Profile[] }>("/model-profiles?status=all&limit=25", "GET", undefined, controller.signal)])
      .then(([value, page]) => { if (!controller.signal.aborted) { setConfig(value); setProfiles(page.items); } })
      .catch(error => { if (!controller.signal.aborted) setError(message(error)); });
    return () => controller.abort();
  }, [nonce]);
  function saved() { setEditor(undefined); setSelection(null); setNonce(value => value + 1); records.reload(); }
  return <section className="panel prompt-panel">
    <div className="section-heading"><div><h2>모델 프로필</h2><p>고정 수신처의 모델을 용도별로 선택하세요. 변경은 이후 호출에 적용하며 호출 당시 선택을 기록합니다.</p></div><button onClick={() => { setNonce(value => value + 1); records.reload(); }}>새로고침</button></div>
    {error && <p role="alert">{error}</p>}
    {config && <><p>설정 확인은 실제 연결 성공을 의미하지 않습니다. 대화 AI는 설치 설정에서 {config.conversation_enabled ? "허용" : "비활성화"}되어 있습니다.</p><div className="prompt-actions">{config.defaults.map(item => <article className="prompt-card" key={item.purpose}><h3>{names[item.purpose]} · 선택 버전 {item.revision}</h3><p>{item.profile_id ? `${profiles.find(p => p.id === item.profile_id)?.name || item.profile_id} · 프로필 버전 ${item.profile_revision}` : "기본 환경 설정"} · {item.configuration_available ? "설정 확인됨" : "설정 재검토 필요"}</p><button onClick={() => setSelection(item)}>{canAdmin ? `${names[item.purpose]} 모델 선택` : `${names[item.purpose]} 선택 검토`}</button></article>)}</div></>}
    <div className="template-toolbar"><label>프로필 검색<input maxLength={200} value={search} onChange={event => onSearch(event.target.value)} /></label><select aria-label="프로필 상태" value={status} onChange={event => onStatus(event.target.value)}><option value="all">모든 프로필</option><option value="active">활성</option><option value="disabled">비활성</option></select>{canAdmin && <button className="primary" disabled={!config} onClick={() => setEditor(null)}>프로필 만들기</button>}</div>
    {records.loading || records.error ? <RecordState records={records} /> : <><p>{records.total}개 프로필 · 최대25개</p>{records.items.map(profile => <article className="prompt-card" key={profile.id}><h3>{profile.name} · 버전 {profile.revision}</h3><p>{profile.model} · {config?.destinations.find(d => d.id === profile.destination_id)?.name || profile.destination_id} · {profile.enabled ? "활성" : "비활성"}</p><p>{eligible(profile) ? "선택 가능한 검토된 설정" : "활성화 및 설정 재검토 필요"}</p><button onClick={() => setEditor(profile)}>{canAdmin ? "프로필 검토 및 편집" : "프로필 검토"}</button><button onClick={() => setCatalog(profile)}>제공자 모델 목록 검토</button></article>)}<Pagination records={records} /></>}
    {editor !== undefined && config && <ProfileEditor key={editor?.id || "new"} initial={editor} config={config} canAdmin={canAdmin} onClose={() => setEditor(undefined)} onSaved={saved} />}
    {selection && <DefaultEditor key={selection.purpose} initial={selection} profiles={profiles} canAdmin={canAdmin} onClose={() => setSelection(null)} onSaved={saved} />}
    {catalog && <ModelCatalog key={catalog.id} initial={catalog} canAdmin={canAdmin} onClose={() => setCatalog(null)} />}
  </section>;
}

function ProfileEditor({ initial, config, canAdmin, onClose, onSaved }: { initial: Profile | null; config: Configuration; canAdmin: boolean; onClose: () => void; onSaved: () => void }) {
  const [base, setBase] = useState(initial), [name, setName] = useState(initial?.name || ""), [model, setModel] = useState(initial?.model || ""), [destination, setDestination] = useState(initial?.destination_id || config.destinations[0]?.id || ""), [enabled, setEnabled] = useState(initial?.enabled || false);
  const [latest, setLatest] = useState<Profile | null>(null), [reviewError, setReviewError] = useState(""), [reviewing, setReviewing] = useState(false);
  const lifetime = useRef(0); useEffect(() => () => { lifetime.current++; }, []);
  const state = useReviewedSave(initial ? `/model-profiles/${initial.id}` : "/model-profiles", initial ? "PUT" : "POST", onSaved);
  async function review() {
    if (!initial || state.inFlight.current || reviewing) return;
    const alive = lifetime.current, session = captureSession(); setReviewing(true); setReviewError("");
    try { const value = await api<Profile>(`/model-profiles/${initial.id}`); if (alive === lifetime.current && session()) setLatest(value); }
    catch (error) { if (alive === lifetime.current && session()) setReviewError(message(error)); }
    finally { if (alive === lifetime.current && session()) setReviewing(false); }
  }
  return <Modal title={initial ? "모델 프로필 검토" : "모델 프로필 만들기"} onClose={() => { if (!state.inFlight.current) onClose(); }}>
    <p>검토 기준 버전 {base?.revision || 0} · 최대200개 버전. 활성화하면 현재 수신처 인증 설정을 검토한 것으로 기록합니다.</p>
    <label>프로필 이름<input value={name} maxLength={100} disabled={!canAdmin || state.locked} onChange={e => setName(e.target.value)} /></label>
    <label>모델 이름<input value={model} maxLength={160} disabled={!canAdmin || state.locked} onChange={e => setModel(e.target.value)} /></label>
    <label>고정 수신처<select value={destination} disabled={!canAdmin || state.locked} onChange={e => setDestination(e.target.value)}>{config.destinations.map(item => <option key={item.id} value={item.id}>{item.name} · {item.configuration_available ? "설정 확인됨" : "설정 필요"}</option>)}</select></label>
    <label><input type="checkbox" checked={enabled} disabled={!canAdmin || state.locked} onChange={e => setEnabled(e.target.checked)} />활성화 및 현재 설정 검토</label>
    <p>프로필을 바꾸면 기존 용도별 선택도 다시 검토해야 합니다.</p><SaveStatus state={state} />
    {state.conflict && initial && <button disabled={reviewing} onClick={review}>최신 프로필 검토</button>}{reviewError && <p role="alert">{reviewError}</p>}
    {latest && <article className="prompt-card"><h3>최신 버전 {latest.revision}</h3><p>{latest.name} · {latest.model} · {latest.enabled ? "활성" : "비활성"}</p><button onClick={() => { setBase(latest); setLatest(null); state.reviewed(); }}>이 버전을 기준으로 내 초안 유지</button></article>}
    {state.conflict && !initial && <p>프로필 이름 또는 설치 설정을 확인한 뒤 다시 작성하세요.</p>}
    {state.conflict && !initial && <button onClick={() => state.reviewed()}>확인하고 초안 다시 편집</button>}
    <div className="prompt-actions"><button disabled={state.busy} onClick={onClose}>닫기</button>{canAdmin && <button className="primary" disabled={state.busy || state.conflict || !name.trim() || !model.trim()} onClick={() => state.save({ name, model, destination_id: destination, enabled, ...(initial ? { expected_revision: base!.revision } : {}) })}>{state.busy ? "저장 중…" : state.uncertain ? "같은 요청으로 다시 저장" : "새 버전 저장"}</button>}</div>
    {initial && <History path={`/model-profiles/${initial.id}/history`} />}
  </Modal>;
}

function DefaultEditor({ initial, profiles, canAdmin, onClose, onSaved }: { initial: Selection; profiles: Profile[]; canAdmin: boolean; onClose: () => void; onSaved: () => void }) {
  const [base, setBase] = useState(initial), [choices, setChoices] = useState(profiles), [selected, setSelected] = useState(initial.profile_id || ""), [latest, setLatest] = useState<{ selection: Selection; profiles: Profile[] } | null>(null), [reviewError, setReviewError] = useState(""), [reviewing, setReviewing] = useState(false);
  const lifetime = useRef(0); useEffect(() => () => { lifetime.current++; }, []);
  const state = useReviewedSave(`/model-defaults/${initial.purpose}`, "PUT", onSaved);
  const chosen = choices.find(p => p.id === selected), valid = selected === "" || !!chosen && eligible(chosen);
  async function review() {
    if (reviewing || state.inFlight.current) return;
    const alive = lifetime.current, session = captureSession(); setReviewing(true); setReviewError("");
    try {
      const [config, page] = await Promise.all([api<Configuration>("/models/configuration"), api<{ items: Profile[] }>("/model-profiles?status=all&limit=25")]);
      const selection = config.defaults.find(item => item.purpose === initial.purpose);
      if (!selection) throw new Error("현재 모델 선택을 확인할 수 없습니다.");
      if (alive === lifetime.current && session()) setLatest({ selection, profiles: page.items });
    } catch (error) { if (alive === lifetime.current && session()) setReviewError(message(error)); }
    finally { if (alive === lifetime.current && session()) setReviewing(false); }
  }
  return <Modal title={`${names[initial.purpose]} 모델 선택`} onClose={() => { if (!state.inFlight.current) onClose(); }}>
    <p>검토 기준 선택 버전 {base.revision} · 최대200개 버전. 선택 저장은 작업 실행을 승인하지 않습니다.</p>
    <label>사용할 모델 프로필<select value={selected} disabled={!canAdmin || state.locked} onChange={e => setSelected(e.target.value)}><option value="">기본 환경 설정</option>{choices.map(p => <option value={p.id} key={p.id} disabled={!eligible(p)}>{p.name} · 버전 {p.revision} · {p.model}{eligible(p) ? "" : " · 재검토 필요"}</option>)}</select></label>
    {chosen && <p>검토할 프로필 버전 {chosen.revision} · {chosen.model}</p>}<p>기본 환경 설정에 모델·키가 없으면 AI 호출을 사용할 수 없습니다.</p><SaveStatus state={state} />
    {state.conflict && <button disabled={reviewing} onClick={review}>최신 모델 선택 검토</button>}{reviewError && <p role="alert">{reviewError}</p>}
    {latest && <article className="prompt-card"><h3>현재 선택 버전 {latest.selection.revision}</h3><p>{latest.selection.profile_id ? `${latest.profiles.find(p => p.id === latest.selection.profile_id)?.name || latest.selection.profile_id} · 프로필 버전 ${latest.selection.profile_revision}` : "기본 환경 설정"}</p><button onClick={() => { setBase(latest.selection); setChoices(latest.profiles); setSelected(latest.selection.profile_id || ""); setLatest(null); state.reviewed(); }}>현재 설정을 검토하고 다시 선택</button></article>}
    <div className="prompt-actions"><button disabled={state.busy} onClick={onClose}>닫기</button>{canAdmin && <button className="primary" disabled={state.busy || state.conflict || !valid} onClick={() => state.save({ expected_revision: base.revision, profile_id: selected || null, expected_profile_revision: chosen?.revision || null })}>{state.busy ? "저장 중…" : state.uncertain ? "같은 요청으로 다시 저장" : "모델 선택 저장"}</button>}</div>
    <History path={`/model-defaults/${initial.purpose}/history`} />
  </Modal>;
}
