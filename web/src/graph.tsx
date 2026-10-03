import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useRecords, Pagination } from "./records";
import { coverageNames } from "./coverage";

type GraphAsset = {
  id: string;
  name: string;
  url: string;
  owner: string;
  revision: number;
  archived_at: number | null;
};
type GraphTask = {
  id: string;
  name: string;
  status: string;
  approved_at?: number;
  scope_revision?: number;
  scope_url?: string;
};
type Node = {
  id: string;
  kind: string;
  record_id: string;
  label: string;
  data: Record<string, unknown>;
};
type Edge = { id: string; source: string; target: string; relation: string };
type Graph = {
  asset: GraphAsset;
  task: GraphTask | null;
  nodes: Node[];
  edges: Edge[];
  findings: {
    total: number;
    offset: number;
    limit: number;
    snapshot: number;
    has_more: boolean;
  };
  omitted: { evidence: number; endpoints: number; invalid_evidence: number };
};
const kinds: Record<string, string> = {
  asset: "자산",
  task: "작업",
  check: "검증 도구",
  finding: "발견",
  evidence: "증거",
  endpoint: "관찰 링크",
};
const relations: Record<string, string> = {
  scope: "계획 범위",
  planned_check: "선택한 도구",
  finding: "발견 기록",
  evidence: "검증 증거",
  observed_link: "관찰한 링크",
};
const columns: Record<string, number> = {
  asset: 0,
  task: 1,
  check: 2,
  finding: 3,
  endpoint: 3,
  evidence: 4,
};
const taskStatuses: Record<string, string> = {
  pending: "승인 대기",
  queued: "대기 중",
  running: "실행 중",
  stopping: "중지 중",
  completed: "완료",
  failed: "실패",
  stopped: "중지됨",
  interrupted: "중단됨",
  rejected: "거절됨",
};
const severityNames: Record<string, string> = {
  critical: "치명적",
  high: "높음",
  medium: "보통",
  low: "낮음",
  info: "정보",
};
const findingStatuses: Record<string, string> = {
  open: "미조치",
  accepted: "위험 수용",
  resolved: "해결됨",
};
function initial() {
  const q = new URLSearchParams(location.search);
  const offset = Number(q.get("graph_offset") || 0);
  const snapshot = q.has("graph_snapshot")
    ? Number(q.get("graph_snapshot"))
    : null;
  return {
    asset: q.get("graph_asset") || "",
    task: q.get("graph_task") || "",
    check: q.get("graph_check") || "",
    severity: q.get("graph_severity") || "",
    status: q.get("graph_status") || "",
    offset:
      Number.isSafeInteger(offset) && offset >= 0 && offset <= 10_000_000
        ? offset
        : 0,
    snapshot:
      snapshot !== null && Number.isSafeInteger(snapshot) && snapshot >= 0
        ? snapshot
        : null,
  };
}
function stateLabel(node: Node) {
  if (node.kind === "check")
    return node.data.stale
      ? `이전 범위 · 당시 ${coverageNames[String(node.data.status)] || "기록 없음"}`
      : coverageNames[String(node.data.status)] || "기록 없음";
  if (node.kind === "task")
    return taskStatuses[String(node.data.status)] || String(node.data.status);
  if (node.kind === "finding")
    return `${severityNames[String(node.data.severity)] || node.data.severity} · ${findingStatuses[String(node.data.status)] || node.data.status}`;
  if (node.kind === "endpoint") return "링크 관찰 · 미검증";
  if (node.kind === "asset")
    return node.data.archived_at
      ? "보관된 자산"
      : `등록 범위 #${node.data.revision || 1}`;
  return "원본 검증 관찰";
}

export function EvidenceGraph({
  tools,
  onFinding,
}: {
  tools: { id: string; name: string }[];
  onFinding: (id: string) => void;
}) {
  const [scope, setScope] = useState(initial);
  const [assetSearch, setAssetSearch] = useState("");
  const [taskSearch, setTaskSearch] = useState("");
  const [includeArchived, setIncludeArchived] = useState(true);
  const assets = useRecords<GraphAsset>(
    "assets",
    assetSearch,
    includeArchived ? {} : { archived: "false" },
  );
  const tasks = useRecords<GraphTask>(
    scope.asset ? "tasks" : null,
    taskSearch,
    { asset_id: scope.asset },
  );
  const [result, setResult] = useState<{ key: string; data: Graph } | null>(
    null,
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState(
    () => new URLSearchParams(location.search).get("graph_node") || "",
  );
  const [zoom, setZoom] = useState(100);
  const [listView, setListView] = useState(false);
  const [showControls, setShowControls] = useState(
    () => !window.matchMedia("(max-width: 700px)").matches,
  );
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const lastRevealed = useRef("");
  const focusRequested = useRef(false);
  const key = JSON.stringify(scope);
  const graph = result?.key === key ? result.data : null;
  useEffect(() => {
    if (!scope.asset && assets.items.length)
      setScope((current) => ({ ...current, asset: assets.items[0].id }));
  }, [scope.asset, assets.items]);
  useEffect(() => {
    const back = () => {
      setScope(initial());
      setSelected(new URLSearchParams(location.search).get("graph_node") || "");
    };
    window.addEventListener("popstate", back);
    return () => window.removeEventListener("popstate", back);
  }, []);
  useEffect(() => {
    const q = new URLSearchParams(location.search);
    for (const [name, value] of Object.entries(scope)) {
      if (value === "" || value === null || (name === "offset" && value === 0))
        q.delete("graph_" + name);
      else q.set("graph_" + name, String(value));
    }
    if (selected) q.set("graph_node", selected);
    else q.delete("graph_node");
    history.replaceState(
      history.state,
      "",
      location.pathname + (q.size ? "?" + q : "") + location.hash,
    );
  }, [key, selected]);
  useEffect(() => {
    const timer = setInterval(() => setRevision((value) => value + 1), 4000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!scope.asset) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const q = new URLSearchParams({
      asset_id: scope.asset,
      limit: "10",
      offset: String(scope.offset),
    });
    for (const name of ["task", "check", "severity", "status"] as const)
      if (scope[name]) q.set(name === "task" ? "task_id" : name, scope[name]);
    if (scope.snapshot !== null) q.set("snapshot", String(scope.snapshot));
    api<Graph>("/graph?" + q, "GET", undefined, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        if (!scope.task && data.task) {
          setScope((current) => ({ ...current, task: data.task!.id }));
          return;
        }
        if (data.findings.total && scope.offset >= data.findings.total) {
          setScope((current) => ({
            ...current,
            offset: Math.floor((data.findings.total - 1) / 10) * 10,
            snapshot: data.findings.snapshot,
          }));
          return;
        }
        setResult({ key, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [key, revision]);
  useEffect(() => {
    if (!selected) {
      lastRevealed.current = "";
      return;
    }
    const button = buttons.current.get(selected);
    if (
      button &&
      (lastRevealed.current !== selected || focusRequested.current)
    ) {
      button.scrollIntoView({ block: "nearest", inline: "nearest" });
      if (focusRequested.current) button.focus({ preventScroll: true });
      lastRevealed.current = selected;
      focusRequested.current = false;
    }
  }, [selected, graph, listView, zoom]);
  function change(
    name: "check" | "severity" | "status" | "task",
    value: string,
  ) {
    setScope((current) => ({
      ...current,
      [name]: value,
      offset: 0,
      snapshot: null,
    }));
    setSelected("");
  }
  const selectedNode =
    graph?.nodes.find((node) => node.id === selected) || graph?.nodes[0];
  const neighboringEdges =
    graph?.edges.filter(
      (edge) =>
        edge.source === selectedNode?.id || edge.target === selectedNode?.id,
    ) || [];
  const positions = new Map<string, { x: number; y: number }>();
  const rows = [0, 0, 0, 0, 0];
  graph?.nodes.forEach((node) => {
    const column = columns[node.kind];
    positions.set(node.id, {
      x: 24 + column * 270,
      y: 56 + rows[column]++ * 88,
    });
  });
  const height = Math.max(300, 56 + Math.max(...rows) * 88);
  const nodeButton = (node: Node, diagram = false) => {
    const position = positions.get(node.id)!;
    return (
      <button
        type="button"
        key={node.id}
        className={`relation-node ${node.kind} ${selectedNode?.id === node.id ? "selected" : ""}`}
        style={diagram ? { left: position.x, top: position.y } : undefined}
        aria-pressed={selectedNode?.id === node.id}
        onClick={() => setSelected(node.id)}
        title={node.label}
        ref={(element) => {
          if (element) buttons.current.set(node.id, element);
          else buttons.current.delete(node.id);
        }}
      >
        <small>{kinds[node.kind]}</small>
        <strong>{node.label}</strong>
        <span>{stateLabel(node)}</span>
      </button>
    );
  };
  const currentAsset = graph?.asset;
  const assetOptions = assets.items.some((asset) => asset.id === scope.asset)
    ? assets.items
    : currentAsset && currentAsset.id === scope.asset
      ? [currentAsset, ...assets.items]
      : assets.items;
  const taskOptions = tasks.items.some((task) => task.id === scope.task)
    ? tasks.items
    : graph?.task && graph.task.id === scope.task
      ? [graph.task, ...tasks.items]
      : tasks.items;
  return (
    <div className="relation-workspace">
      <section className="panel relation-controls">
        <div className="panel-head">
          <h3>기록으로 연결된 탐색 경로</h3>
          <span className="subtle">대상에 추가 요청 없음</span>
          <button
            type="button"
            aria-expanded={showControls}
            aria-controls="relation-controls"
            onClick={() => setShowControls((value) => !value)}
          >
            {showControls ? "선택·필터 접기" : "선택·필터 변경"}
          </button>
        </div>
        {showControls && (
          <div id="relation-controls">
            <div className="relation-selectors">
              <div>
                <label>
                  자산 검색
                  <input
                    value={assetSearch}
                    onChange={(e) => setAssetSearch(e.target.value)}
                    maxLength={200}
                    placeholder="이름·주소·담당자"
                  />
                </label>
                <label>
                  자산 선택
                  <select
                    value={scope.asset}
                    onChange={(e) => {
                      setScope({
                        ...initial(),
                        asset: e.target.value,
                        task: "",
                        check: "",
                        severity: "",
                        status: "",
                        offset: 0,
                        snapshot: null,
                      });
                      setSelected("");
                      setTaskSearch("");
                    }}
                  >
                    {!assetOptions.some(
                      (asset) => asset.id === scope.asset,
                    ) && (
                      <option value={scope.asset}>
                        {scope.asset
                          ? "주소에서 선택한 자산"
                          : "자산을 선택하세요"}
                      </option>
                    )}
                    {assetOptions.map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.name}
                        {asset.archived_at ? " · 보관됨" : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={includeArchived}
                    onChange={(e) => setIncludeArchived(e.target.checked)}
                  />
                  보관된 자산 포함
                </label>
                <Pagination records={assets} />
              </div>
              <div>
                <label>
                  작업 검색
                  <input
                    value={taskSearch}
                    onChange={(e) => setTaskSearch(e.target.value)}
                    maxLength={200}
                    placeholder="이 자산의 작업 이름"
                  />
                </label>
                <label>
                  작업 선택
                  <select
                    value={scope.task}
                    onChange={(e) => change("task", e.target.value)}
                    disabled={!scope.asset}
                  >
                    <option value="">최근 생성한 작업</option>
                    {!taskOptions.some((task) => task.id === scope.task) &&
                      scope.task && (
                        <option value={scope.task}>주소에서 선택한 작업</option>
                      )}
                    {taskOptions.map((task) => (
                      <option key={task.id} value={task.id}>
                        {task.name} · {taskStatuses[task.status] || task.status}
                      </option>
                    ))}
                  </select>
                </label>
                <Pagination records={tasks} />
              </div>
            </div>
            <div className="relation-filters">
              <label>
                검증 도구
                <select
                  value={scope.check}
                  onChange={(e) => change("check", e.target.value)}
                >
                  <option value="">모든 선택 도구</option>
                  {tools.map((tool) => (
                    <option key={tool.id} value={tool.id}>
                      {tool.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                발견 심각도
                <select
                  value={scope.severity}
                  onChange={(e) => change("severity", e.target.value)}
                >
                  <option value="">전체</option>
                  {Object.entries(severityNames).map(([value, name]) => (
                    <option key={value} value={value}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                발견 상태
                <select
                  value={scope.status}
                  onChange={(e) => change("status", e.target.value)}
                >
                  <option value="">전체</option>
                  {Object.entries(findingStatuses).map(([value, name]) => (
                    <option key={value} value={value}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={loading}
                onClick={() => {
                  setScope((current) => ({
                    ...current,
                    offset: 0,
                    snapshot: null,
                  }));
                  setRevision((value) => value + 1);
                }}
              >
                최신 기록
              </button>
            </div>
          </div>
        )}
      </section>
      {error && (
        <div className="form-error" role="alert">
          {error}{" "}
          <button
            type="button"
            onClick={() => {
              setScope((current) => ({
                ...current,
                task: "",
                check: "",
                severity: "",
                status: "",
                offset: 0,
                snapshot: null,
              }));
              setSelected("");
            }}
          >
            최근 작업으로 돌아가기
          </button>
        </div>
      )}
      {!scope.asset && !assets.loading && !assets.error && (
        <div className="quiet-state">
          자산을 등록하면 검증 계획과 증거의 연결 관계를 탐색할 수 있습니다.
        </div>
      )}
      {loading && !graph && <p role="status">연결된 기록을 불러오는 중…</p>}
      {graph && (
        <>
          {selected && !graph.nodes.some((node) => node.id === selected) && (
            <p className="footnote" role="status">
              북마크에서 선택한 기록이 현재 필터·페이지의 표시 범위에 없습니다.
              발견 페이지를 이동하거나 발견 상세에서 전체 증거를 확인하세요.
            </p>
          )}
          <div className="relation-context">
            <strong>{graph.asset.name}</strong>
            <span>
              {graph.task
                ? `${graph.task.name} · ${taskStatuses[graph.task.status] || graph.task.status}`
                : "아직 검증 계획이 없습니다."}
            </span>
            {graph.task && (
              <span>
                등록 범위 #{graph.asset.revision || 1} / 작업 범위 #
                {graph.task.scope_revision || 1}
              </span>
            )}
            <span>
              {graph.nodes.length}개 노드 · {graph.edges.length}개 실제 연결
            </span>
          </div>
          <section className="panel relation-diagram">
            <div className="panel-head">
              <h3>자산 · 작업 · 검증 · 발견 · 증거</h3>
              <div className="relation-view-controls">
                <button
                  type="button"
                  aria-pressed={listView}
                  onClick={() => {
                    lastRevealed.current = "";
                    setListView((value) => !value);
                  }}
                >
                  {listView ? "그래프 보기" : "목록으로 보기"}
                </button>
                <label>
                  확대
                  <select
                    value={zoom}
                    onChange={(e) => {
                      lastRevealed.current = "";
                      setZoom(Number(e.target.value));
                    }}
                  >
                    {[80, 100, 120].map((value) => (
                      <option key={value} value={value}>
                        {value}%
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            {listView ? (
              <div className="relation-node-list">
                {graph.nodes.map((node) => nodeButton(node))}
              </div>
            ) : (
              <div
                className="relation-scroll"
                tabIndex={0}
                role="region"
                aria-label="관계 그래프 · 좌우와 위아래로 이동 가능"
              >
                <div
                  style={{
                    width: (1370 * zoom) / 100,
                    height: (height * zoom) / 100,
                  }}
                >
                  <div
                    className="relation-canvas"
                    style={{
                      width: 1370,
                      height,
                      transform: `scale(${zoom / 100})`,
                    }}
                  >
                    <svg width="1370" height={height} aria-hidden="true">
                      <defs>
                        <marker
                          id="relation-arrow"
                          viewBox="0 0 10 10"
                          refX="9"
                          refY="5"
                          markerWidth="6"
                          markerHeight="6"
                          orient="auto-start-reverse"
                        >
                          <path d="M 0 0 L 10 5 L 0 10 z" />
                        </marker>
                      </defs>
                      {graph.edges.map((edge) => {
                        const from = positions.get(edge.source)!,
                          to = positions.get(edge.target)!;
                        const active = neighboringEdges.some(
                          (item) => item.id === edge.id,
                        );
                        return (
                          <path
                            key={edge.id}
                            className={active ? "active" : ""}
                            d={`M ${from.x + 210} ${from.y + 36} C ${from.x + 240} ${from.y + 36}, ${to.x - 30} ${to.y + 36}, ${to.x} ${to.y + 36}`}
                            markerEnd="url(#relation-arrow)"
                          />
                        );
                      })}
                    </svg>
                    {[
                      "자산",
                      "작업",
                      "검증 도구",
                      "발견 · 관찰 링크",
                      "증거",
                    ].map((name, index) => (
                      <span
                        className="relation-column-title"
                        key={name}
                        style={{ left: 24 + index * 270 }}
                      >
                        {name}
                      </span>
                    ))}
                    {graph.nodes.map((node) => nodeButton(node, true))}
                  </div>
                </div>
              </div>
            )}
            <p className="footnote">
              노드를 선택하면 연결된 기록과 근거를 아래에서 확인할 수 있습니다.
              좁은 화면에서는 그래프를 좌우로 이동하거나 목록 보기를 사용하세요.
            </p>
          </section>
          {selectedNode && (
            <section className="panel relation-detail">
              <div className="panel-head">
                <h3>
                  {kinds[selectedNode.kind]} · {selectedNode.label}
                </h3>
                <span>{stateLabel(selectedNode)}</span>
              </div>
              <div className="relation-detail-body">
                {selectedNode.kind === "asset" && (
                  <p>
                    {String(selectedNode.data.url)} · 담당자{" "}
                    {String(selectedNode.data.owner || "미지정")}
                  </p>
                )}
                {selectedNode.kind === "task" && (
                  <p>
                    계획 범위:{" "}
                    {String(selectedNode.data.scope_url || graph.asset.url)} ·{" "}
                    {selectedNode.data.approved_at
                      ? "실행 승인 기록 있음"
                      : "승인되지 않은 계획"}
                  </p>
                )}
                {selectedNode.kind === "check" && (
                  <p>
                    {String(
                      selectedNode.data.reason ||
                        "이전 기록에 상세 이유가 없습니다.",
                    )}
                    {selectedNode.data.stale
                      ? " 현재 등록 범위와 다른 결과입니다."
                      : ""}
                  </p>
                )}
                {selectedNode.kind === "finding" && (
                  <>
                    <p>
                      이 작업의 증거{" "}
                      {Number(selectedNode.data.evidence_count || 0)}개 · 전체
                      이력 참조{" "}
                      {Number(selectedNode.data.history_reference_count || 0)}개
                    </p>
                    <button
                      type="button"
                      onClick={() => onFinding(selectedNode.record_id)}
                    >
                      발견 상세 열기
                    </button>
                  </>
                )}
                {selectedNode.kind === "evidence" && (
                  <pre>
                    {JSON.stringify(selectedNode.data.observation, null, 2)}
                  </pre>
                )}
                {selectedNode.kind === "endpoint" && (
                  <p>
                    {String(selectedNode.data.url)} · 링크를 관찰한 기록이며
                    해당 주소로 검증 요청을 보낸 결과가 아닙니다.
                  </p>
                )}
                <h4>직접 연결된 기록</h4>
                {neighboringEdges.length ? (
                  <ul className="relation-neighbors">
                    {neighboringEdges.map((edge) => {
                      const outgoing = edge.source === selectedNode.id;
                      const neighbor = graph.nodes.find(
                        (node) =>
                          node.id === (outgoing ? edge.target : edge.source),
                      )!;
                      return (
                        <li key={edge.id}>
                          <button
                            type="button"
                            onClick={() => {
                              focusRequested.current = true;
                              setSelected(neighbor.id);
                            }}
                          >
                            {outgoing ? "→" : "←"} {relations[edge.relation]} ·{" "}
                            {kinds[neighbor.kind]} · {neighbor.label}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p>이 조회 범위에서 연결된 기록이 없습니다.</p>
                )}
              </div>
            </section>
          )}
          <nav className="pagination" aria-label="그래프 발견 페이지">
            <span>
              발견{" "}
              {graph.findings.total
                ? `${graph.findings.offset + 1}–${Math.min(graph.findings.offset + graph.findings.limit, graph.findings.total)}`
                : "0"}{" "}
              / 전체 {graph.findings.total}개
            </span>
            <button
              type="button"
              disabled={loading || !scope.offset}
              onClick={() => {
                setScope((current) => ({
                  ...current,
                  offset: Math.max(0, current.offset - 10),
                  snapshot: graph.findings.snapshot,
                }));
                setSelected("");
              }}
            >
              이전 발견
            </button>
            <button
              type="button"
              disabled={loading || !graph.findings.has_more}
              onClick={() => {
                setScope((current) => ({
                  ...current,
                  offset: current.offset + 10,
                  snapshot: graph.findings.snapshot,
                }));
                setSelected("");
              }}
            >
              다음 발견
            </button>
          </nav>
          <p className="footnote">
            발견은 한 페이지에 10개, 증거는 발견마다 최근 2개, 관찰 링크는 최근
            10개를 표시합니다. 이 페이지에서 생략한 증거{" "}
            {graph.omitted.evidence}개 · 관찰 링크 {graph.omitted.endpoints}개.
            전체 증거는 발견 상세에서 확인하세요.
          </p>
          {graph.omitted.invalid_evidence > 0 && (
            <p className="form-error" role="status">
              누락되거나 자산·도구·지문이 맞지 않는 증거 참조{" "}
              {graph.omitted.invalid_evidence}개는 연결하지 않았습니다.
            </p>
          )}
        </>
      )}
    </div>
  );
}
