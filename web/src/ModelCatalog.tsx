import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import Modal from "./components/Modal";
import { Pagination, RecordState, useRecords } from "./records";

type Profile = { id: string; name: string; revision: number; model: string; enabled: boolean; configuration_available: boolean; destination_review_current: boolean; admin_review_current: boolean };
type Query = { id: string; profile_revision: number; profile_snapshot: { name: string; model: string }; status: string; result_code: string; models: string[]; model_count: number; created_at: string; response_sha256?: string; http_status?: number };
type Request = { expected_revision: number; request_id: string };
const status: Record<string, string> = { started: "응답 확인 중", completed: "목록 응답 확인됨", failed: "목록 확인 실패", blocked: "설정 변경으로 중단", unknown: "완료 여부 확인 불가" };
const codes: Record<string, string> = {
  awaiting_response: "저장된 요청의 결과를 다시 확인하세요.", catalog_response_valid: "제공자의 모델 목록 응답을 검증했습니다.",
  process_receipt_unconfirmed: "서버 재시작 전 요청 결과를 확정하지 못했습니다. 외부 요청을 다시 보내지 않았습니다.",
  request_stopped: "종료 중 요청이 중단되어 결과를 확정하지 못했습니다.", profile_review_changed: "요청 직전 프로필 또는 인증 설정이 변경됐습니다.",
  provider_status: "제공자가 성공 응답을 반환하지 않았습니다.", response_encoding: "지원하지 않는 응답 인코딩입니다.",
  response_content_type: "JSON 응답이 아닙니다.", response_byte_budget: "응답 크기 제한을 초과했습니다.",
  response_shape: "모델 목록 형식이 유효하지 않습니다.", connection_failed: "제공자 연결 또는 응답을 확인하지 못했습니다.",
};
function Result({ query }: { query: Query }) {
  return <article className="prompt-card"><h3>{status[query.status] || query.status} · 프로필 버전 {query.profile_revision}</h3>
    <p>{query.profile_snapshot.name} · 당시 설정 모델 {query.profile_snapshot.model}</p>
    <p>{codes[query.result_code] || query.result_code}{query.http_status ? ` · HTTP ${query.http_status}` : ""}</p>
    <p>조회 시작 {query.created_at} · 모델 {query.model_count}개</p>
    {query.status === "completed" && <><p>목록에 포함되어도 대화 호출 지원이나 이용 권한을 보장하지 않습니다.</p>{query.models.length ? <ul>{query.models.map(model => <li key={model}>{model}</li>)}</ul> : <p>제공자가 빈 목록을 반환했습니다.</p>}</>}
  </article>;
}

export default function ModelCatalog({ initial, canAdmin, onClose }: { initial: Profile; canAdmin: boolean; onClose: () => void }) {
  const [profile, setProfile] = useState(initial), [latest, setLatest] = useState<Profile | null>(null);
  const [query, setQuery] = useState<Query | null>(null), [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [conflict, setConflict] = useState(false), [error, setError] = useState("");
  const pending = useRef<Request | null>(null), inFlight = useRef(false), lifetime = useRef(0);
  const history = useRecords<Query>("model-catalog-history", "", {}, undefined, `/model-profiles/${initial.id}/catalog-history`, false);
  useEffect(() => () => { lifetime.current++; }, []);
  const eligible = profile.enabled && profile.configuration_available && profile.destination_review_current && profile.admin_review_current;
  async function read() {
    if (inFlight.current || conflict) return;
    const alive = lifetime.current, session = captureSession();
    inFlight.current = true; setBusy(true); setError("");
    pending.current ||= { expected_revision: profile.revision, request_id: crypto.randomUUID() };
    try {
      const result = await api<{ query: Query; replayed: boolean }>(`/model-profiles/${initial.id}/catalog`, "POST", pending.current);
      if (alive === lifetime.current && session()) {
        setQuery(result.query); setUncertain(result.query.status === "started");
        if (result.query.status !== "started") pending.current = null;
        history.reload();
      }
    } catch (error) {
      if (alive === lifetime.current && session()) {
        setError(error instanceof Error ? error.message : "목록 응답을 확인하지 못했습니다.");
        if (error instanceof ApiError && error.status === 409) { setConflict(true); setUncertain(false); }
        else if (error instanceof ApiError && [400, 401, 403, 404, 422].includes(error.status)) { pending.current = null; setUncertain(false); }
        else setUncertain(true);
      }
    } finally { inFlight.current = false; if (alive === lifetime.current && session()) setBusy(false); }
  }
  async function review() {
    if (inFlight.current) return;
    const alive = lifetime.current, session = captureSession(); inFlight.current = true; setBusy(true); setError("");
    try {
      const value = await api<Profile>(`/model-profiles/${initial.id}`);
      if (alive === lifetime.current && session()) setLatest(value);
    } catch (error) { if (alive === lifetime.current && session()) setError(error instanceof Error ? error.message : "현재 프로필을 확인하지 못했습니다."); }
    finally { inFlight.current = false; if (alive === lifetime.current && session()) setBusy(false); }
  }
  return <Modal title="제공자 모델 목록" onClose={() => { if (!inFlight.current) onClose(); }}>
    <p>{profile.name} · 검토 기준 버전 {profile.revision}. 등록된 고정 수신처에 모델 목록 요청을 한 번 보냅니다.</p>
    <p>응답은 최대1MiB·256개 모델이며 프로필별 조회 기록은 최대200개입니다. 목록 확인은 프로필이나 용도별 모델 선택을 변경하지 않습니다.</p>
    {!eligible && <p>활성 프로필과 현재 인증 설정을 먼저 검토하세요.</p>}
    {error && <p role="alert">{error}</p>}
    {uncertain && <p role="status">같은 요청으로 결과를 다시 확인하세요. 저장된 조회가 있으면 외부 요청을 중복하지 않습니다.</p>}
    {conflict && <><p>설정 변경 또는 조회 기록 제한을 확인하세요. 기록 제한은 프로필을 다시 검토해도 해제되지 않습니다.</p><button disabled={busy} onClick={review}>최신 프로필 검토</button></>}
    {latest && <article className="prompt-card"><h3>최신 버전 {latest.revision}</h3><p>{latest.name} · {latest.model} · {latest.enabled ? "활성" : "비활성"}</p><button disabled={busy} onClick={() => { setProfile(latest); setLatest(null); pending.current = null; setConflict(false); setUncertain(false); setError(""); }}>이 프로필을 검토하고 조회 준비</button></article>}
    <div className="prompt-actions"><button disabled={busy} onClick={onClose}>닫기</button>{canAdmin && <button className="primary" disabled={busy || conflict || (!uncertain && !eligible)} onClick={read}>{busy ? "목록 확인 중…" : uncertain ? "같은 요청 결과 확인" : query ? "새 요청으로 모델 목록 조회" : "고정 수신처 모델 목록 조회"}</button>}</div>
    {query && <Result query={query} />}
    <h3>저장된 목록 조회 기록</h3><button disabled={history.loading} onClick={history.reload}>조회 기록 새로고침</button>
    {history.loading || history.error ? <RecordState records={history} /> : <><p>{history.total}개 조회</p>{history.items.map(row => <details key={row.id}><summary>{status[row.status] || row.status} · 버전 {row.profile_revision} · {row.created_at}</summary><Result query={row} /></details>)}<Pagination records={history} /></>}
  </Modal>;
}
