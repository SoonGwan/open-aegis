import { useEffect, useRef, useState } from "react";
import { api, captureSession } from "./api";
import { useReviewedSave, SaveStatus } from "./ModelProfiles";
import { Pagination, RecordState, useRecords } from "./records";

type Purpose = "planner" | "conversation";
type Profile = { id: string; name: string; model: string; revision: number; enabled: boolean; configuration_available: boolean; destination_review_current: boolean; admin_review_current: boolean };
type Selection = { purpose: Purpose; revision: number; profile_id: string | null; profile_revision: number | null; configuration_available: boolean; archive_revision: number; task_archived: boolean };
const names = { planner: "검증 순서 계획", conversation: "기록 기반 대화" };
const eligible = (profile: Profile) => profile.enabled && profile.configuration_available && profile.destination_review_current && profile.admin_review_current;
function selectionLabel(selection: { profile_id: string | null; profile_revision: number | null }, profiles: Profile[]) {
  if (!selection.profile_id) return "워크스페이스 용도별 선택 따름";
  const profile = profiles.find(item => item.id === selection.profile_id && item.revision === selection.profile_revision);
  return profile ? `${profile.name} · ${profile.model} · 검토 버전 ${selection.profile_revision}` : `이전 프로필 ${selection.profile_id} · 검토 버전 ${selection.profile_revision}`;
}


export default function TaskModels({ taskId, canAdmin }: { taskId: string; canAdmin: boolean }) {
  const [items, setItems] = useState<Selection[]>([]), [profiles, setProfiles] = useState<Profile[]>([]), [error, setError] = useState(""), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0), [editor, setEditor] = useState<Selection | null>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    Promise.all([api<{ items: Selection[] }>(`/tasks/${taskId}/models`, "GET", undefined, controller.signal), api<{ items: Profile[] }>("/model-profiles?status=all&limit=25", "GET", undefined, controller.signal)])
      .then(([selections, page]) => { if (!controller.signal.aborted) { setItems(selections.items); setProfiles(page.items); } })
      .catch(error => { if (!controller.signal.aborted) setError(error instanceof Error ? error.message : "작업 모델을 확인하지 못했습니다."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [taskId, revision]);
  return <section className="prompt-card"><h3>이 작업의 모델 선택</h3>
    <p>이후 계획 재작성·기록 대화에 사용할 모델입니다. 이미 저장된 계획·호출·실행 승인은 그대로 보존됩니다. 새로 만든 후속 작업은 워크스페이스 기본값을 따릅니다.</p>
    <button disabled={loading} onClick={() => setRevision(value => value + 1)}>작업 모델 새로고침</button>
    {error && <p role="alert">{error}</p>}{loading && <p role="status">작업 모델을 확인하는 중…</p>}
    {!loading && !error && items.map(item => <article className="prompt-card" key={item.purpose}><h4>{names[item.purpose]} · 작업 선택 버전 {item.revision}</h4><p>{selectionLabel(item, profiles)} · {item.configuration_available ? "설정 확인됨" : "현재 설정 재검토 필요"}</p>{item.task_archived && <p>보관된 작업은 모델 선택을 변경할 수 없습니다.</p>}<button onClick={() => setEditor(item)}>{names[item.purpose]} 작업 모델 검토</button></article>)}
    {editor && <Editor key={editor.purpose} taskId={taskId} initial={editor} initialProfiles={profiles} canAdmin={canAdmin} onClose={() => setEditor(null)} onSaved={() => { setEditor(null); setRevision(value => value + 1); window.dispatchEvent(new Event("aegis-records-changed")); }} />}
  </section>;
}

function Editor({ taskId, initial, initialProfiles, canAdmin, onClose, onSaved }: { taskId: string; initial: Selection; initialProfiles: Profile[]; canAdmin: boolean; onClose: () => void; onSaved: () => void }) {
  const [base, setBase] = useState(initial), [profiles, setProfiles] = useState(initialProfiles), [selected, setSelected] = useState(initial.profile_id || ""), [latest, setLatest] = useState<{ selection: Selection; profiles: Profile[] } | null>(null), [error, setError] = useState(""), [reviewing, setReviewing] = useState(false);
  const lifetime = useRef(0); useEffect(() => () => { lifetime.current++; }, []);
  const state = useReviewedSave(`/tasks/${taskId}/models/${initial.purpose}`, "PUT", onSaved);
  const chosen = profiles.find(profile => profile.id === selected), valid = selected === "" || !!chosen && eligible(chosen);
  const history = useRecords<{ id: string; revision: number; actor: { name: string }; snapshot: { profile_id: string | null; profile_revision: number | null } }>("task-model-history", "", {}, undefined, `/tasks/${taskId}/models/${initial.purpose}/history`, false);
  async function review() {
    if (reviewing || state.inFlight.current) return;
    const alive = lifetime.current, session = captureSession();setReviewing(true);setError("");
    try {
      const [configuration, page] = await Promise.all([api<{ items: Selection[] }>(`/tasks/${taskId}/models`), api<{ items: Profile[] }>("/model-profiles?status=all&limit=25")]);
      const selection = configuration.items.find(item => item.purpose === initial.purpose);
      if (!selection) throw new Error("현재 작업 모델을 확인하지 못했습니다.");
      if (alive === lifetime.current && session()) setLatest({ selection, profiles: page.items });
    } catch (error) { if (alive === lifetime.current && session()) setError(error instanceof Error ? error.message : "현재 작업 모델을 확인하지 못했습니다."); }
    finally { if (alive === lifetime.current && session()) setReviewing(false); }
  }
  return <div className="prompt-card"><h4>{names[initial.purpose]} 작업 모델 검토</h4><p>검토 기준 선택 버전 {base.revision} · 최대200개 버전. 현재 프로필 버전을 검토해 저장하세요. 호출이나 실행을 시작하지 않습니다.</p>
    <label>이 작업에 사용할 모델<select disabled={!canAdmin || state.locked || base.task_archived} value={selected} onChange={event => setSelected(event.target.value)}><option value="">워크스페이스 용도별 선택 따름</option>{profiles.map(profile => <option key={profile.id} value={profile.id} disabled={!eligible(profile)}>{profile.name} · 현재 버전 {profile.revision} · {profile.model}{eligible(profile) ? "" : " · 재검토 필요"}</option>)}</select></label>
    {chosen && <p>저장할 검토 프로필 버전 {chosen.revision} · {chosen.model}. 프로필이나 인증 설정이 바뀌면 이 작업 선택도 재검토해야 합니다.</p>}
    {selected === "" && <p>워크스페이스의 현재 용도별 선택을 이후 호출마다 따릅니다. 기본 선택의 변경은 이후 호출에 적용됩니다.</p>}
    <SaveStatus state={state} />{state.conflict && <button disabled={reviewing} onClick={review}>최신 작업 모델 검토</button>}{error && <p role="alert">{error}</p>}
    {latest && <article className="prompt-card"><h4>현재 작업 선택 버전 {latest.selection.revision}</h4><p>{selectionLabel(latest.selection, latest.profiles)} · {latest.selection.task_archived ? "작업 보관됨" : "보관되지 않음"}</p><button onClick={() => { setBase(latest.selection);setProfiles(latest.profiles);setSelected(latest.selection.profile_id || "");setLatest(null);state.reviewed(); }}>현재 작업 선택을 검토하고 다시 선택</button></article>}
    <div className="prompt-actions"><button disabled={state.busy} onClick={onClose}>작업 모델 편집 닫기</button>{canAdmin && <button className="primary" disabled={state.busy || state.conflict || base.task_archived || !valid} onClick={() => state.save({ expected_revision: base.revision, expected_archive_revision: base.archive_revision, profile_id: selected || null, expected_profile_revision: chosen?.revision || null })}>{state.busy ? "작업 모델 저장 중…" : state.uncertain ? "같은 요청으로 작업 모델 확인" : "작업 모델 선택 저장"}</button>}</div>
    <h4>작업 모델 선택 이력</h4>{history.loading || history.error ? <RecordState records={history} /> : <><p>{history.total}개 버전</p>{history.items.map(row => <details key={row.id}><summary>작업 선택 버전 {row.revision} · {row.actor.name}</summary><p>{selectionLabel(row.snapshot, profiles)}</p></details>)}<Pagination records={history} /></>}
  </div>;
}
