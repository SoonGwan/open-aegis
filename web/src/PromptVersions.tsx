import { t as uiText, localizeLabels } from "./i18n-core.ts";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import Modal from "./components/Modal";

type Purpose = "planner" | "conversation";
type Prompt = { id: Purpose; purpose: Purpose; revision: number; template: string; fingerprint: string; guardrail_sha256: string };
type Page = { items: { id: string; revision: number; snapshot: Prompt; action: string; actor: { name: string } }[]; total: number };
const names = localizeLabels({ planner: "검증 순서 계획", conversation: "기록 기반 대화" });
const variables = { planner: "{{goal}}", conversation: "{{question}}" };
const message = (error: unknown) => error instanceof Error ? error.message : uiText("요청을 확인할 수 없습니다.");

export default function PromptVersions({ canAdmin }: { canAdmin: boolean }) {
  const [items, setItems] = useState<Prompt[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const [selected, setSelected] = useState<Prompt | null>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api<{ items: Prompt[] }>("/prompts", "GET", undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) setItems(value.items); })
      .catch(error => { if (!controller.signal.aborted) setError(message(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [nonce]);
  return <>
    <section className="panel prompt-panel">
      <div className="section-heading"><div><h2>{uiText("프롬프트 버전")}</h2><p>{uiText("기본 출력 계약을 유지하면서 추가 지침을 검토하세요. 이후 호출부터 적용하며 호출 당시 버전을 기록합니다.")}</p></div><button onClick={() => setNonce(value => value + 1)}>{uiText("새로고침")}</button></div>
      {error && <p role="alert">{error}</p>}
      {loading ? <p role="status">{uiText("프롬프트를 불러오는 중입니다.")}</p> : items.map(item => <article key={item.id} className="prompt-card">
        <h3>{names[item.purpose]} {uiText(" · 버전 ")}{item.revision}</h3>
        <p>{uiText("지원 변수: ")}<code>{variables[item.purpose]}</code> {uiText(" · 변수 값은 JSON 문자열로 표시합니다.")}</p>
        <pre className="prompt-text">{item.template || uiText("기본 프롬프트 사용 · 추가 지침 없음")}</pre>
        <button onClick={() => setSelected(item)}>{canAdmin ? uiText("버전 검토 및 편집") : uiText("버전 검토")}</button>
      </article>)}
    </section>
    {selected && <PromptReview key={selected.id} initial={selected} canAdmin={canAdmin} onClose={() => setSelected(null)} onSaved={() => { setSelected(null); setNonce(value => value + 1); }} />}
  </>;
}

function PromptReview({ initial, canAdmin, onClose, onSaved }: { initial: Prompt; canAdmin: boolean; onClose: () => void; onSaved: () => void }) {
  const [base, setBase] = useState(initial);
  const [template, setTemplate] = useState(initial.template);
  const [sample, setSample] = useState("");
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [latest, setLatest] = useState<Prompt | null>(null);
  const [history, setHistory] = useState<Page | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [offset, setOffset] = useState(0);
  const pending = useRef<{ expected_revision: number; template: string; request_id: string } | null>(null);
  const inFlight = useRef(false);
  const lifetime = useRef(0);
  const previewTicket = useRef(0);
  const historyTicket = useRef(0);
  useEffect(() => () => { lifetime.current++; previewTicket.current++; historyTicket.current++; }, []);
  useEffect(() => {
    const controller = new AbortController(); const ticket = ++historyTicket.current;
    setHistory(null); setHistoryError("");
    api<Page>(`/prompts/${initial.purpose}/history?limit=25&offset=${offset}`, "GET", undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted && historyTicket.current === ticket) setHistory(value); })
      .catch(error => { if (!controller.signal.aborted && historyTicket.current === ticket) setHistoryError(message(error)); });
    return () => controller.abort();
  }, [initial.purpose, offset]);
  async function save() {
    if (inFlight.current || !canAdmin || conflict) return;
    inFlight.current = true; setBusy(true); setError("");
    const alive = lifetime.current; const currentSession = captureSession();
    pending.current ||= { expected_revision: base.revision, template, request_id: crypto.randomUUID() };
    try {
      await api(`/prompts/${initial.purpose}`, "PUT", pending.current);
      if (alive === lifetime.current && currentSession()) onSaved();
    } catch (error) {
      if (alive === lifetime.current && currentSession()) {
        setError(message(error));
        if (error instanceof ApiError && error.status === 409) { setConflict(true); setUncertain(false); }
        else if (error instanceof ApiError && error.status >= 400 && error.status < 500) { pending.current = null; setUncertain(false); }
        else setUncertain(true);
      }
    } finally {
      inFlight.current = false;
      if (alive === lifetime.current && currentSession()) setBusy(false);
    }
  }
  async function showPreview() {
    const ticket = ++previewTicket.current; const alive = lifetime.current; const currentSession = captureSession();
    setPreview(""); setError("");
    try {
      const result = await api<{ system: string }>(`/prompts/${initial.purpose}/preview`, "POST", { template, value: sample });
      if (ticket === previewTicket.current && alive === lifetime.current && currentSession()) setPreview(result.system);
    } catch (error) { if (ticket === previewTicket.current && alive === lifetime.current && currentSession()) setError(message(error)); }
  }
  async function reviewLatest() {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true);
    const alive = lifetime.current; const currentSession = captureSession();
    try {
      const result = await api<{ items: Prompt[] }>("/prompts");
      if (alive === lifetime.current && currentSession()) setLatest(result.items.find(item => item.purpose === initial.purpose) || null);
    } catch (error) { if (alive === lifetime.current && currentSession()) setError(message(error)); }
    finally { inFlight.current = false; if (alive === lifetime.current && currentSession()) setBusy(false); }
  }
  function changeTemplate(value: string) { previewTicket.current++; setPreview(""); setTemplate(value); }
  return <Modal title={uiText("{0} 프롬프트", [names[initial.purpose]])} onClose={() => { if (!inFlight.current) onClose(); }}>
    <p>{uiText("검토 기준 버전 ")}{base.revision} {uiText(" · 변경은 이후 호출에 적용합니다. 저장은 용도별 최대200개 버전입니다.")}</p>
    <label>{uiText("추가 지침")}<textarea value={template} maxLength={4000} disabled={!canAdmin || busy || uncertain || conflict} onChange={event => changeTemplate(event.target.value)} rows={7} /></label>
    <p>{uiText("지원 변수: ")}<code>{variables[initial.purpose]}</code>{uiText(". 환경변수·파일·명령은 확장하지 않습니다.")}</p>
    <div className="prompt-actions"><button disabled={!canAdmin || busy || uncertain || conflict} onClick={() => changeTemplate("")}>{uiText("기본값으로 되돌리기")}</button><button disabled={busy} onClick={showPreview}>{uiText("적용 내용 미리보기")}</button></div>
    <label>{uiText("미리보기 변수 값")}<input value={sample} maxLength={2000} disabled={busy} onChange={event => { previewTicket.current++; setPreview(""); setSample(event.target.value); }} /></label>
    {preview && <pre className="prompt-text" aria-label={uiText("프롬프트 미리보기")}>{preview}</pre>}
    {error && <p role="alert">{error}</p>}
    {uncertain && <p role="status">{uiText("저장 응답을 확인하지 못했습니다. 같은 요청으로 다시 저장하면 기존 결과를 확인합니다.")}</p>}
    {conflict && <><p>{uiText("초안을 유지했습니다. 현재 버전을 명시적으로 검토한 뒤 저장하세요.")}</p><button disabled={busy} onClick={reviewLatest}>{uiText("최신 버전 검토")}</button></>}
    {latest && <section className="prompt-card"><h3>{uiText("최신 버전 ")}{latest.revision}</h3><pre className="prompt-text">{latest.template || uiText("추가 지침 없음")}</pre><button disabled={busy} onClick={() => { setBase(latest); setLatest(null); setConflict(false); setUncertain(false); pending.current = null; setError(""); }}>{uiText("이 버전을 기준으로 내 초안 유지")}</button></section>}
    <div className="prompt-actions"><button disabled={busy} onClick={onClose}>{uiText("닫기")}</button>{canAdmin && <button className="primary" disabled={busy || conflict} onClick={save}>{busy ? uiText("저장 중…") : uncertain ? uiText("같은 요청으로 다시 저장") : uiText("새 버전 저장")}</button>}</div>
    <h3>{uiText("버전 이력")}</h3>{historyError && <p role="alert">{historyError}</p>}
    {history ? <><p>{history.total}{uiText("개 버전")}</p>{history.items.map(row => <details key={row.id}><summary>{uiText("버전 ")}{row.revision} · {row.action} · {row.actor.name}</summary><pre className="prompt-text">{row.snapshot.template || uiText("추가 지침 없음")}</pre></details>)}<div className="prompt-actions"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 25))}>{uiText("이전 버전")}</button><button disabled={offset + 25 >= history.total} onClick={() => setOffset(value => value + 25)}>{uiText("다음 버전")}</button></div></> : !historyError && <p role="status">{uiText("버전 이력을 불러오는 중입니다.")}</p>}
  </Modal>;
}
