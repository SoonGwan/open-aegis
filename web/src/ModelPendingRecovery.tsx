import { useEffect, useRef, useState } from "react";
import { clearModelPending, finishModelPending, loadModelPending, storeModelPending, type ModelBody, type PendingModelRequest } from "./model-pending";

export function useModelPending(actor: string, path: string, method: "PUT" | "POST") {
  const selected = useRef<PendingModelRequest | null>(null);
  const [current, setCurrent] = useState<PendingModelRequest | null>(null), [rows, setRows] = useState<PendingModelRequest[]>([]), [error, setError] = useState("");
  function reload() {
    try { setRows(loadModelPending(window.localStorage, actor, path, method));setError(""); }
    catch (value) { setError(value instanceof Error ? value.message : "브라우저 요청 기록을 읽지 못했습니다."); }
  }
  useEffect(() => {
    reload();
    const changed = () => reload();
    window.addEventListener("storage", changed);return () => window.removeEventListener("storage", changed);
  }, [actor, path, method]);
  function stage(body: ModelBody) {
    if (error) throw new Error(error);
    if (!selected.current && loadModelPending(window.localStorage, actor, path, method).length) throw new Error("이전 미확인 요청을 먼저 선택해 결과를 확인하세요.");
    const request = selected.current || { version: 1 as const, actor, path, method, body: { ...body, request_id: crypto.randomUUID() }, created_at: Date.now() };
    storeModelPending(window.localStorage, request);selected.current = request;setCurrent(request);reload();return request.body;
  }
  function choose(request: PendingModelRequest) {
    selected.current = request;setCurrent(request);
  }
  function finish() {
    if (selected.current) finishModelPending(window.localStorage, selected.current);
    selected.current = null;setCurrent(null);reload();
  }
  function clear() {
    try { clearModelPending(window.localStorage, actor, path, method);selected.current = null;setCurrent(null);reload();return true; }
    catch (value) { setError(value instanceof Error ? value.message : "브라우저 기록을 정리하지 못했습니다.");return false; }
  }
  return { rows, current, error, stage, choose, finish, clear, waiting: rows.length > 0 && !current };
}

const when = (timestamp: number) => new Date(timestamp).toLocaleString("ko-KR");
function Contents({ request }: { request: PendingModelRequest }) {
  const body = request.body;
  return <><p>작성 {when(request.created_at)} · 요청 {String(body.request_id)}</p>
    {body.expected_revision !== undefined && <p>당시 기준 버전 {String(body.expected_revision)}{body.expected_archive_revision !== undefined ? ` · 작업 보관 버전 ${body.expected_archive_revision}` : ""}</p>}
    {typeof body.name === "string" && <p>{body.name} · 모델 {String(body.model)} · 수신처 {String(body.destination_id)} · {body.enabled ? "활성 설정" : "비활성 설정"}</p>}
    {"profile_id" in body && <p>{body.profile_id ? `당시 프로필 ${body.profile_id} · 검토 버전 ${body.expected_profile_revision}` : "고정 프로필 해제 / 기본 선택 따름"}</p>}
  </>;
}
export function ModelPendingRecovery({ state, canAdmin, busy, choose, onCleared }: { state: ReturnType<typeof useModelPending>; canAdmin: boolean; busy: boolean; choose: (request: PendingModelRequest) => void; onCleared: () => void }) {
  return <>
    {state.error && <p role="alert">{state.error}</p>}
    {state.current && <article className="prompt-card"><h3>확인 중인 원래 요청</h3><Contents request={state.current} /><p>같은 요청 ID와 당시 내용으로 결과를 확인합니다. 현재 화면의 설정이 달라도 이 내용을 바꾸지 않습니다.</p></article>}
    {state.waiting && <section className="prompt-card"><h3>이전 미확인 요청 {state.rows.length}개</h3><p>브라우저가 보존한 요청은24시간 동안 복구할 수 있습니다. 자동으로 보내지 않습니다. 하나를 선택한 뒤 같은 요청 결과를 확인하세요.</p>
      {state.rows.map(request => <article key={String(request.body.request_id)}><Contents request={request} />{canAdmin && <button disabled={busy} onClick={() => choose(request)}>이 요청을 선택해 결과 확인 준비</button>}</article>)}</section>}
    {(state.error || state.rows.length > 0 || state.current) && <details><summary>브라우저 요청 기록 정리</summary><p>브라우저에서만 이 리소스의 미확인 요청을 지웁니다. 서버 기록은 남을 수 있습니다. 먼저 이력을 확인하세요. 새 요청을 보내면 별도 작업 또는 비용이 발생할 수 있습니다.</p>{canAdmin && <button disabled={busy} onClick={() => { if (state.clear()) onCleared(); }}>이 리소스의 브라우저 요청 기록 지우기</button>}</details>}
  </>;
}
