import { t as uiText, localizeLabels, getFormatLocale } from "./i18n-core.ts";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import Modal from "./components/Modal";
import { useModelPending, ModelPendingRecovery } from "./ModelPendingRecovery";
import { Pagination, RecordState, useRecords } from "./records";

type Profile = { id: string; name: string; revision: number; model: string; enabled: boolean; configuration_available: boolean; destination_review_current: boolean; admin_review_current: boolean };
type Query = { id: string; profile_revision: number; profile_snapshot: { name: string; model: string; provider_protocol?: "openai" | "anthropic" }; status: string; result_code: string; models?: string[]; model_count?: number; tokens?: { status: string; prompt_tokens: number | null; completion_tokens: number | null; total_tokens: number | null }; cost?: { status: string; amount: string | null; currency: string | null }; created_at: number; response_sha256?: string; http_status?: number };
const status: Record<string, string> = localizeLabels({ started: "응답 확인 중", completed: "목록 응답 확인됨", failed: "요청 확인 실패", blocked: "설정 변경으로 중단", unknown: "완료 여부 확인 불가" });
const codes: Record<string, string> = localizeLabels({
  inference_response_valid: "고정된 짧은 메시지의 추론 응답을 확인했습니다. 모델 품질이나 이후 가용성을 보장하지 않습니다.",
  awaiting_response: "저장된 요청의 결과를 다시 확인하세요.", catalog_response_valid: "제공자의 모델 목록 응답을 검증했습니다.",
  process_receipt_unconfirmed: "서버 재시작 전 요청 결과를 확정하지 못했습니다. 외부 요청을 다시 보내지 않았습니다.",
  request_stopped: "종료 중 요청이 중단되어 결과를 확정하지 못했습니다.", profile_review_changed: "요청 직전 프로필 또는 인증 설정이 변경됐습니다.",
  provider_status: "제공자가 성공 응답을 반환하지 않았습니다.", response_encoding: "지원하지 않는 응답 인코딩입니다.",
  response_content_type: "JSON 응답이 아닙니다.", response_byte_budget: "응답 크기 제한을 초과했습니다.",
  catalog_incomplete: "다음 페이지가 있어 전체 모델 목록을 확인하지 못했습니다. 현재 조회는 최대256개 한 페이지를 지원합니다.",
  response_shape: "기대한 응답 형식 또는 고정 메시지의 답이 유효하지 않습니다.", connection_failed: "제공자 연결 또는 응답을 확인하지 못했습니다.",
});
const stateLabel = (state: string, connection: boolean) => connection && state === "completed" ? uiText("고정 메시지 추론 응답 확인됨") : connection && state === "failed" ? uiText("연결 시험 실패") : status[state] || state;
const usageLabel: Record<string, string> = localizeLabels({ reported: "보고됨", partial: "일부 보고됨", missing: "미보고", invalid: "유효하지 않음" });
const date = (value: number) => new Date(value * 1000).toLocaleString(getFormatLocale());
function Result({ query, connection }: { query: Query; connection: boolean }) {
  return <article className="prompt-card"><h3>{stateLabel(query.status, connection)} {uiText(" · 프로필 버전 ")}{query.profile_revision}</h3>
    <p>{query.profile_snapshot.name} {uiText(" · 당시 설정 모델 ")}{query.profile_snapshot.model} · {query.profile_snapshot.provider_protocol === "anthropic" ? "Claude API" : uiText("OpenAI 호환 API")}</p>
    <p>{codes[query.result_code] || query.result_code}{query.http_status ? ` · HTTP ${query.http_status}` : ""}</p>
    <p>{uiText("요청 시작 ")}{date(query.created_at)}{!connection && uiText(" · 모델 {0}개", [query.model_count])}</p>
    {connection && <><p>{uiText("보고된 토큰: 입력 ")}{query.tokens?.prompt_tokens ?? uiText("미보고")} {uiText(" · 출력 ")}{query.tokens?.completion_tokens ?? uiText("미보고")} {uiText(" · 전체 ")}{query.tokens?.total_tokens ?? uiText("미보고")} {uiText(" · 상태 ")}{usageLabel[query.tokens?.status || "missing"] || uiText("유효하지 않음")}</p><p>{query.cost?.status === "estimated" ? uiText("당시 설정 단가에 따른 추정 {0} {1}", [query.cost.amount, query.cost.currency]) : uiText("유효한 사용량 또는 단가가 없어 비용을 추정하지 못했습니다.")}</p><p>{uiText("연결 시험은 계획·대화 사용량 합계에 포함되지 않습니다. 실제 청구는 제공자 기록에서 확인하세요.")}</p></>}
    {!connection && query.status === "completed" && <><p>{uiText("목록에 포함되어도 대화 호출 지원이나 이용 권한을 보장하지 않습니다.")}</p>{query.models?.length ? <ul>{query.models?.map(model => <li key={model}>{model}</li>)}</ul> : <p>{uiText("제공자가 빈 목록을 반환했습니다.")}</p>}</>}
  </article>;
}

export default function ModelProviderCheck({ actorId, initial, canAdmin, onClose, connection = false }: { actorId: string; initial: Profile; canAdmin: boolean; onClose: () => void; connection?: boolean }) {
  const action = connection ? uiText("모델 연결 시험") : uiText("모델 목록 조회"), endpoint = connection ? "connection-test" : "catalog", historyEndpoint = connection ? "connection-history" : "catalog-history";
  const [profile, setProfile] = useState(initial), [latest, setLatest] = useState<Profile | null>(null);
  const [query, setQuery] = useState<Query | null>(null), [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [conflict, setConflict] = useState(false), [error, setError] = useState("");
  const pending = useModelPending(actorId, `/model-profiles/${initial.id}/${endpoint}`, "POST"), inFlight = useRef(false), lifetime = useRef(0);
  const history = useRecords<Query>(`model-${historyEndpoint}`, "", {}, undefined, `/model-profiles/${initial.id}/${historyEndpoint}`, false);
  useEffect(() => () => { lifetime.current++; }, []);
  const eligible = profile.enabled && profile.configuration_available && profile.destination_review_current && profile.admin_review_current;
  async function read() {
    if (inFlight.current || conflict) return;
    const alive = lifetime.current, session = captureSession();let dispatched = false;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const body = pending.stage({ expected_revision: profile.revision });dispatched = true;
      const result = await api<{ query: Query; replayed: boolean }>(`/model-profiles/${initial.id}/${endpoint}`, "POST", body);
      if (alive === lifetime.current && session()) {
        setQuery(result.query);
        if (result.query.status !== "started") pending.finish();
        setUncertain(result.query.status === "started");
        history.reload();
      }
    } catch (error) {
      if (alive === lifetime.current && session()) {
        setError(error instanceof Error ? error.message : uiText("제공자 응답을 확인하지 못했습니다."));
        if (!dispatched) setUncertain(!!pending.current);
        else if (error instanceof ApiError && error.status === 409) { setConflict(true); setUncertain(false); }
        else if (error instanceof ApiError && [400, 404, 422].includes(error.status)) {
          try { pending.finish();setUncertain(false); } catch (cleanup) { setError(cleanup instanceof Error ? cleanup.message : uiText("브라우저 기록을 정리하지 못했습니다."));setUncertain(true); }
        }
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
    } catch (error) { if (alive === lifetime.current && session()) setError(error instanceof Error ? error.message : uiText("현재 프로필을 확인하지 못했습니다.")); }
    finally { inFlight.current = false; if (alive === lifetime.current && session()) setBusy(false); }
  }
  return <Modal title={connection ? uiText("제공자 모델 연결 시험") : uiText("제공자 모델 목록")} onClose={() => { if (!inFlight.current) onClose(); }}>
    <p>{profile.name} {uiText(" · 검토 기준 버전 ")}{profile.revision} {uiText(" · 설정 모델 ")}{profile.model}{uiText(". 등록된 고정 수신처에 ")}{action} {uiText(" 요청을 한 번 보냅니다.")}</p>
    <p>{connection ? uiText("고정된 짧은 메시지와 출력 토큰 제한16으로 실제 추론 요청을 보냅니다. 제공자 비용이 발생할 수 있습니다. 작업 데이터나 대상 정보는 보내지 않습니다.") : uiText("응답은 최대1MiB·256개 모델입니다.")} {uiText(" 프로필별 기록은 최대200개이며 모델 선택을 변경하지 않습니다.")}</p>
    {!eligible && <p>{uiText("활성 프로필과 현재 인증 설정을 먼저 검토하세요.")}</p>}
    <ModelPendingRecovery state={pending} canAdmin={canAdmin} busy={busy} choose={request => { pending.choose(request);setUncertain(true);setConflict(false);setError(""); }} onCleared={() => { setUncertain(false);setConflict(false);setError(""); }} />
    {error && <p role="alert">{error}</p>}
    {uncertain && <p role="status">{uiText("같은 요청으로 결과를 다시 확인하세요. 저장된 요청이 있으면 외부 요청을 중복하지 않습니다.")}</p>}
    {conflict && <><p>{uiText("설정 변경 또는 요청 기록 제한을 확인하세요. 기록 제한은 프로필을 다시 검토해도 해제되지 않습니다.")}</p><button disabled={busy} onClick={review}>{uiText("최신 프로필 검토")}</button></>}
    {latest && <article className="prompt-card"><h3>{uiText("최신 버전 ")}{latest.revision}</h3><p>{latest.name} · {latest.model} · {latest.enabled ? uiText("활성") : uiText("비활성")}</p><button disabled={busy} onClick={() => { try { pending.finish();setProfile(latest);setLatest(null);setConflict(false);setUncertain(false);setError(""); } catch (value) { setError(value instanceof Error ? value.message : uiText("브라우저 기록을 정리하지 못했습니다.")); } }}>{uiText("이 프로필을 검토하고 요청 준비")}</button></article>}
    <div className="prompt-actions"><button disabled={busy} onClick={onClose}>{uiText("닫기")}</button>{canAdmin && <button className="primary" disabled={busy || conflict || pending.waiting || !!pending.error || (!uncertain && !eligible)} onClick={read}>{busy ? uiText("응답 확인 중…") : uncertain ? uiText("같은 요청 결과 확인") : connection ? uiText("추론 요청으로 연결 시험") : query ? uiText("새 요청으로 모델 목록 조회") : uiText("고정 수신처 모델 목록 조회")}</button>}</div>
    {query && <Result query={query} connection={connection} />}
    <h3>{uiText("저장된 ")}{action} {uiText(" 기록")}</h3><button disabled={history.loading} onClick={history.reload}>{uiText("요청 기록 새로고침")}</button>
    {history.loading || history.error ? <RecordState records={history} /> : <><p>{history.total}{uiText("개 요청")}</p>{history.items.map(row => <details key={row.id}><summary>{stateLabel(row.status, connection)} {uiText(" · 버전 ")}{row.profile_revision} · {date(row.created_at)}</summary><Result query={row} connection={connection} /></details>)}<Pagination records={history} /></>}
  </Modal>;
}
