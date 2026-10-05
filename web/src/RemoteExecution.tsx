import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type Executor = { id: string; url: string; check_ids: string[] };
export type RemoteExecution = {
  connection_id: string;
  url: string;
  tools: { name: string; revision: number }[];
  profile: { ceiling: { target_rps: number; request_timeout: number; task_timeout: number } };
};

export function RemoteExecutionPicker({ disabled, onChecks, names }: {
  disabled: boolean;
  onChecks: (checks: string[] | null) => void;
  names: Record<string, string>;
}) {
  const [connections, setConnections] = useState<Executor[]>([]);
  const [selected, setSelected] = useState("");
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const current = ++generation.current;
    setLoading(true);
    setError("");
    void api<Executor[]>("/integrations/mcp/executors", "GET", undefined, controller.signal)
      .then((rows) => {
        if (!controller.signal.aborted && current === generation.current) setConnections(rows);
      })
      .catch((cause) => {
        if (!controller.signal.aborted && current === generation.current)
          setError(cause instanceof Error ? cause.message : "실행 연결을 확인하지 못했습니다.");
      })
      .finally(() => {
        if (!controller.signal.aborted && current === generation.current) setLoading(false);
      });
    return () => { controller.abort(); ++generation.current; };
  }, [revision]);
  const connection = connections.find((row) => row.id === selected);
  return <section className="remote-execution" aria-label="검증 실행 위치">
    <label>실행 위치
      <select name="remote_connection_id" disabled={disabled} value={selected}
        onChange={(event) => {
          const value = event.target.value;
          setSelected(value);
          onChecks(value ? connections.find((row) => row.id === value)?.check_ids || [] : null);
        }}>
        <option value="">현재 Open Aegis 서버</option>
        {selected && !connection && <option value={selected}>{selected} · 연결 변경됨</option>}
        {connections.map((row) => <option key={row.id} value={row.id}>{row.id} · 원격 GET 검증</option>)}
      </select>
    </label>
    {loading && <p role="status">관리자 검토를 마친 실행 연결을 확인합니다…</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    <button type="button" disabled={disabled || loading} onClick={() => setRevision((value) => value + 1)}>실행 연결 새로고침</button>
    {connection && <p className="subtle">{connection.url} · 지원 검사: {connection.check_ids.map((check) => names[check] || check).join(", ")}</p>}
    {selected && <p className="subtle">등록한 범위의 GET 검사만 실행합니다. 중지는 이후 검사 전송을 막습니다. 진행 중인 원격 검사의 요청은 즉시 종료되지 않을 수 있습니다.</p>}
  </section>;
}

export function RemoteExecutionSummary({ contract }: { contract?: RemoteExecution }) {
  if (!contract) return null;
  return <section className="remote-execution" aria-label="승인할 원격 실행 서버">
    <h4>원격 GET 검증 · {contract.connection_id}</h4>
    <p className="subtle">{contract.url}</p>
    <p className="subtle">서버 상한 · 초당 {contract.profile.ceiling.target_rps} 요청 · 요청 {contract.profile.ceiling.request_timeout}초 · 검사 {contract.profile.ceiling.task_timeout}초</p>
    <p className="subtle">관리자 검토한 도구 {contract.tools.length}개 · 연결과 도구가 변경되면 새 계획을 검토합니다. 자산별 승인 요청 예산을 함께 사용합니다.</p>
  </section>;
}
