import { t as uiText } from "./i18n-core.ts";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";

type Connection = { id: string; url: string; configured: boolean };
type Definition = {
  name: string;
  description?: string;
  inputSchema: unknown;
  outputSchema?: unknown;
  annotations?: unknown;
};
type Review = {
  id: string;
  expires_at: number;
  catalog: { tools: Definition[] };
};
type Tool = {
  id: string;
  connection_id: string;
  name: string;
  revision: number;
  enabled: boolean;
  execution_available?: boolean;
  definition_sha256: string;
};
type Page = { items: Tool[]; total: number; has_more: boolean };
type Detail = Tool & { definition: Definition };
const base = "/integrations/mcp";

export function MCPRegistryPanel() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [connection, setConnection] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [page, setPage] = useState<Page>({
    items: [],
    total: 0,
    has_more: false,
  });
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const alive = useRef(true);
  const locked = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const clearReview = () => {
    setReview(null);
    setSelected([]);
    setConfirmed(false);
  };

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (locked.current) return;
    locked.current = true;
    const current = new AbortController();
    controller.current = current;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action(current.signal);
    } catch (cause) {
      if (alive.current && !current.signal.aborted) {
        setError(
          cause instanceof Error
            ? cause.message
            : uiText("요청을 처리하지 못했습니다."),
        );
        if (cause instanceof ApiError && [409, 410].includes(cause.status))
          clearReview();
      }
    } finally {
      if (controller.current === current) {
        locked.current = false;
        if (alive.current && !current.signal.aborted) setBusy(false);
      }
    }
  }

  async function load(signal: AbortSignal, nextOffset = offset) {
    const [sources, rows] = await Promise.all([
      api<Connection[]>(base + "/connections", "GET", undefined, signal),
      api<Page>(
        base + `/tools?limit=25&offset=${nextOffset}`,
        "GET",
        undefined,
        signal,
      ),
    ]);
    if (!alive.current || signal.aborted) return;
    setConnections(sources);
    setPage(rows);
    setOffset(nextOffset);
    setDetail(null);
    if (
      !sources.some((source) => source.id === connection && source.configured)
    ) {
      clearReview();
      setConnection("");
    }
  }

  useEffect(() => {
    alive.current = true;
    void run((signal) => load(signal, 0));
    return () => {
      alive.current = false;
      controller.current?.abort();
      controller.current = null;
      locked.current = false;
    };
  }, []);

  function inspect() {
    void run(async (signal) => {
      clearReview();
      const result = await api<Review>(
        base + "/previews",
        "POST",
        { connection_id: connection },
        signal,
      );
      if (alive.current && !signal.aborted) setReview(result);
    });
  }

  function register() {
    if (!review) return;
    void run(async (signal) => {
      const result = await api<{ items: Tool[] }>(
        base + `/previews/${review.id}/register`,
        "POST",
        { selected, reviewed: confirmed },
        signal,
      );
      if (!alive.current || signal.aborted) return;
      clearReview();
      setMessage(
        uiText("{0}개 도구를 등록했습니다. 검증 실행은 별도 작업 승인이 필요합니다.", [result.items.length]),
      );
      await load(signal, 0);
    });
  }

  function disable(tool: Tool) {
    void run(async (signal) => {
      await api(
        base + `/tools/${tool.id}/disable`,
        "POST",
        { revision: tool.revision },
        signal,
      );
      if (!alive.current || signal.aborted) return;
      setMessage(uiText("{0} 등록을 비활성화했습니다.", [tool.name]));
      await load(signal);
    });
  }

  return (
    <section
      className="panel mcp-registry"
      aria-label={uiText("원격 MCP 도구 등록")}
      aria-busy={busy}
    >
      <div className="panel-head">
        <h3>{uiText("원격 MCP 도구 등록")}</h3>
        <button
          disabled={busy}
          onClick={() => void run((signal) => load(signal))}
        >
          {uiText("목록 새로고침")}</button>
      </div>
      <p>
        {uiText("관리자가 도구 정의를 검토해 등록합니다. 운영자가 구성한 GET 실행 어댑터는 새 작업에서 선택할 수 있습니다. 등록은 실행 승인이 아닙니다.")}</p>
      {error && (
        <p role="alert" className="error">
          {error} {uiText(" 목록을 다시 조회하거나 새로고침한 뒤 재시도하세요.")}</p>
      )}
      {message && <p role="status">{message}</p>}
      {!busy && connections.length === 0 && (
        <p>
          {uiText("설정된 MCP 연결이 없습니다. 서버 관리자가 연결 주소와 인증을 설정한 후 새로고침하세요.")}</p>
      )}
      <div className="mcp-actions">
        <label>
          {uiText("검토할 MCP 연결")}{" "}
          <select
            value={connection}
            disabled={busy}
            onChange={(event) => {
              setConnection(event.target.value);
              clearReview();
              setError("");
              setMessage("");
            }}
          >
            <option value="">{uiText("연결 선택")}</option>
            {connections.map((source) => (
              <option
                key={source.id}
                value={source.id}
                disabled={!source.configured}
              >
                {source.id}
                {source.configured ? "" : uiText(" · 인증 설정 필요")}
              </option>
            ))}
          </select>
        </label>
        <button disabled={busy || !connection} onClick={inspect}>
          {busy ? uiText("처리 중…") : uiText("도구 목록 검토")}
        </button>
      </div>
      {connection && (
        <p className="mcp-endpoint">
          {connections.find((source) => source.id === connection)?.url}
        </p>
      )}
      {review && (
        <section aria-label={uiText("MCP 도구 정의 검토")}>
          <p>
            {uiText("검토는 ")}{new Date(review.expires_at * 1000).toLocaleTimeString()}{uiText("까지 유효합니다. 등록 전에 현재 서버 목록을 다시 확인합니다.")}</p>
          {review.catalog.tools.length === 0 && (
            <p>{uiText("이 서버가 제공한 도구가 없습니다.")}</p>
          )}
          {review.catalog.tools.map((tool) => (
            <article className="mcp-tool" key={tool.name}>
              <label>
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={selected.includes(tool.name)}
                  onChange={(event) => {
                    setSelected((current) =>
                      event.target.checked
                        ? [...current, tool.name]
                        : current.filter((name) => name !== tool.name),
                    );
                    setConfirmed(false);
                  }}
                />{" "}
                {tool.name}
              </label>
              {tool.description && <p>{tool.description}</p>}
              <details>
                <summary>{tool.name} {uiText(" 입력·결과 정의 보기")}</summary>
                <pre>{JSON.stringify(tool, null, 2)}</pre>
              </details>
            </article>
          ))}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy || selected.length === 0}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            {uiText("선택한 도구 정의를 검토했습니다. 등록은 실행 승인이 아닙니다.")}</label>
          <button
            className="primary"
            disabled={busy || !confirmed || selected.length === 0}
            onClick={register}
          >
            {uiText("선택한 ")}{selected.length}{uiText("개 도구 등록")}</button>
        </section>
      )}
      <h4>{uiText("등록된 도구 · ")}{page.total}{uiText("개")}</h4>
      {page.items.length === 0 && (
        <p>
          {busy
            ? uiText("목록을 확인하고 있습니다…")
            : uiText("이 페이지에 등록된 도구가 없습니다.")}
        </p>
      )}
      {page.items.map((tool) => (
        <article className="mcp-tool" key={tool.id}>
          <strong>
            {tool.connection_id} / {tool.name}
          </strong>
          <p>
            {uiText("버전 ")}{tool.revision} · {tool.enabled ? uiText("등록됨") : uiText("비활성화됨")}
            {tool.enabled && tool.execution_available ? uiText(" · 실행 어댑터 검토됨") : uiText(" · 실행 어댑터 없음")}
          </p>
          <div className="mcp-actions">
            <button
              disabled={busy}
              onClick={() =>
                void run(async (signal) => {
                  const result = await api<Detail>(
                    base + `/tools/${tool.id}`,
                    "GET",
                    undefined,
                    signal,
                  );
                  if (alive.current && !signal.aborted) setDetail(result);
                })
              }
            >
              {tool.name} {uiText(" 등록 정의 보기")}</button>
            <button
              disabled={busy || !tool.enabled}
              onClick={() => disable(tool)}
            >
              {tool.name} {uiText(" 비활성화")}</button>
          </div>
        </article>
      ))}
      {detail && (
        <details open>
          <summary>{detail.name} {uiText(" 저장된 등록 정의")}</summary>
          <pre>{JSON.stringify(detail.definition, null, 2)}</pre>
        </details>
      )}
      {page.total > 25 && (
        <nav className="mcp-actions" aria-label={uiText("MCP 등록 도구 페이지")}>
          <button
            disabled={busy || offset === 0}
            onClick={() =>
              void run((signal) => load(signal, Math.max(0, offset - 25)))
            }
          >
            {uiText("이전 도구")}</button>
          <span>
            {offset + 1}–{offset + page.items.length} / {page.total}
          </span>
          <button
            disabled={busy || !page.has_more}
            onClick={() => void run((signal) => load(signal, offset + 25))}
          >
            {uiText("다음 도구")}</button>
        </nav>
      )}
    </section>
  );
}
