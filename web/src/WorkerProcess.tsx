import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { CoverageTable, type Coverage } from "./coverage";
import { useRecords, Pagination, RecordState } from "./records";
import { ObservationRecord, type Observation } from "./task-records";

type Scope = { id: string; name: string; url: string; revision?: number };
type Process = {
  format: "aegis-worker-process-v1";
  worker: { task_id: string; asset_id: string; asset_name: string; scope_url: string; scope_revision: number };
  task_status: string;
  approved_at: number | null;
  coverage: Coverage[];
  execution_authorized: false;
};
type WorkerEvent = {
  seq: number; ts: number; level: string; message: string;
  detail: Record<string, unknown>;
  worker_provenance?: { status: string };
};

export function WorkerProcess({ taskId, assets, tools }: {
  taskId: string; assets: Scope[]; tools: { id: string; name: string }[];
}) {
  const [assetId, setAssetId] = useState("");
  return <section className="worker-process" aria-label="Worker 실행 과정">
    <h4 className="detail-heading">Worker 실행 과정</h4>
    <p className="subtle">자산별 검증 결과와 실행 기록을 확인하세요. 작업에 저장된 승인 범위로 조회합니다.</p>
    <label className="task-record-search">과정을 확인할 자산
      <select aria-label="Worker 자산" value={assetId} onChange={e => setAssetId(e.target.value)}>
        <option value="">자산 선택</option>
        {assets.map(a => <option key={a.id} value={a.id}>{a.name} · revision {a.revision ?? 1}</option>)}
      </select>
    </label>
    {assetId && <ProcessDetail key={`${taskId}:${assetId}`} taskId={taskId} assetId={assetId} tools={tools} />}
  </section>;
}

function ProcessDetail({ taskId, assetId, tools }: {
  taskId: string; assetId: string; tools: { id: string; name: string }[];
}) {
  const path = `/tasks/${encodeURIComponent(taskId)}/workers/${encodeURIComponent(assetId)}`;
  const [result, setResult] = useState<Process | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const queryButton = useRef<HTMLButtonElement>(null);
  const focusError = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; controller.current?.abort(); };
  }, []);
  useEffect(() => {
    if (focusError.current && !loading) { focusError.current = false; queryButton.current?.focus(); }
  }, [loading, error]);
  async function load() {
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await api<Process>(path, "GET", undefined, request.signal);
      if (!mounted.current || controller.current !== request) return;
      if (data.format !== "aegis-worker-process-v1" || data.worker?.task_id !== taskId ||
          data.worker.asset_id !== assetId || data.execution_authorized !== false)
        throw new Error("Worker 출처가 일치하지 않습니다. 다시 조회하세요.");
      setResult(data);
    } catch (e) {
      if (mounted.current && controller.current === request && !request.signal.aborted) {
        focusError.current = true; setError((e as Error).message);
      }
    } finally {
      if (mounted.current && controller.current === request) setLoading(false);
    }
  }
  return <div aria-busy={loading}>
    <button type="button" ref={queryButton} disabled={loading} onClick={() => void load()}>
      {loading ? "과정 조회 중…" : "Worker 과정 조회"}
    </button>
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <>
      <p><strong>{result.worker.asset_name}</strong> · 승인 범위 revision {result.worker.scope_revision}</p>
      <code className="observation-url">{result.worker.scope_url}</code>
      <p className="subtle">{result.approved_at ? "실행 승인 기록 있음" : "실행 승인 기록 없음"} · 저장된 출처 메타데이터의 일치이며 실행 성공이나 자산의 안전성을 보장하지 않습니다.</p>
      <CoverageTable rows={result.coverage} assets={[{ id: assetId, name: result.worker.asset_name }]} tools={tools} />
      <WorkerCollection key={`${path}:events`} path={path} kind="events" />
      <WorkerCollection key={`${path}:observations`} path={path} kind="observations" />
    </>}
  </div>;
}

function WorkerCollection({ path, kind }: { path: string; kind: "events" | "observations" }) {
  const [search, setSearch] = useState("");
  const records = useRecords<WorkerEvent | Observation>(kind, search, {}, undefined, `${path}/${kind}`);
  const name = kind === "events" ? "선택 Worker 실행 기록" : "선택 Worker 관찰";
  return <section className="finding-collection" aria-label={name}>
    <h4 className="detail-heading">{name}</h4>
    <label className="task-record-search">{kind === "events" ? "메시지·수준으로 검색" : "링크·제목으로 검색"}
      <input aria-label={`${name} 검색`} maxLength={200} value={search} onChange={e => setSearch(e.target.value)} />
    </label>
    {kind === "observations" && <p className="subtle">관찰한 링크를 방문하거나 실행하지 않습니다. 출처 확인은 저장 메타데이터 비교입니다.</p>}
    <Pagination records={records} />
    {!records.ready ? <RecordState records={records} /> : records.items.length ? records.items.map(row => {
      if (kind === "observations") return <ObservationRecord key={(row as Observation).id} record={row as Observation} />;
      const event = row as WorkerEvent;
      return <article className="finding-record execution-entry task-event-record" key={event.seq}>
        <strong>{event.message}</strong>
        <small>{new Date(event.ts * 1000).toLocaleString("ko-KR")} · {event.level}</small>
        <p className="subtle">{event.worker_provenance?.status === "matched" ? "Worker 출처 메타데이터 일치" : "Worker 출처 미확인"}</p>
        <details><summary>실행 기록 상세</summary><pre>{JSON.stringify(event.detail, null, 2)}</pre></details>
      </article>;
    }) : <p className="subtle">{search ? "검색 결과가 없습니다." : `${name}이 없습니다.`}</p>}
  </section>;
}
