import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { PolicySummary, type ExecutionPolicy } from "./runtime";
import { ToolContracts } from "./ToolContracts";
import type { ToolManifest } from "./tool-contract-state";
import { WorkerDependencies } from "./WorkerDependencies";

type Cell = {
  id: string;
  asset_id: string;
  asset_revision: number;
  check: string;
  status: string;
};
export type TodoPlanContext = {
  format: string;
  root_task_id: string;
  fingerprint: string;
  items: {
    id: string;
    revision: number;
    status: string;
    title: string;
    description: string;
    check_ids: string[];
  }[];
};
export type ObservationPlanContext = {
  format: string;
  fingerprint: string;
  counts: {
    total: number;
    inspected: number;
    included: number;
    excluded: number;
    omitted: number;
  };
  items: {
    id: string;
    task_id: string;
    asset_id: string;
    url: string;
    scope_revision: number;
    category: string;
  }[];
};
export function WorkerObservationBasis({
  context,
}: {
  context?: ObservationPlanContext;
}) {
  if (!context) return null;
  if (
    !context.counts ||
    [
      context.counts.total,
      context.counts.inspected,
      context.counts.included,
      context.counts.excluded,
      context.counts.omitted,
    ].some((value) => !Number.isSafeInteger(value) || value < 0) ||
    !Array.isArray(context.items) ||
    context.items.length > 100 ||
    context.counts.included !== context.items.length ||
    context.counts.included + context.counts.excluded !==
      context.counts.inspected ||
    context.counts.inspected + context.counts.omitted !==
      context.counts.total ||
    context.items.some(
      (row) =>
        !row ||
        typeof row.url !== "string" ||
        typeof row.id !== "string" ||
        typeof row.task_id !== "string" ||
        typeof row.category !== "string" ||
        !Number.isSafeInteger(row.scope_revision) ||
        row.scope_revision < 1,
    )
  )
    return <p role="alert">저장된 Worker 관찰 계획 맥락을 확인하세요.</p>;
  const labels: Record<string, string> = {
    api_path: "API 경로",
    session_path: "세션 경로",
    management_path: "관리 경로",
    other: "기타 경로",
  };
  return (
    <section
      className="todo-plan-basis next-plan"
      aria-label="계획에 저장된 Worker 관찰"
    >
      <details>
        <summary>
          계획에 저장된 Worker 관찰 · {context.counts.included}개
        </summary>
        <p>
          생성 당시 출처·완료 근거·현재 범위가 일치한 관찰입니다. 경로 유형을
          도구 순서의 참고로 사용하며 링크 방문·취약점 판정·새 실행 권한을
          뜻하지 않습니다.
        </p>
        <p>
          전체 {context.counts.total}개 · 확인 {context.counts.inspected}개 ·
          제외 {context.counts.excluded}개 · 표본 밖 {context.counts.omitted}개
        </p>
        <p>
          AI 모드에서는 관찰 ID·출처 작업/자산 ID·범위 버전·경로 유형만 설정된
          제공자에게 전송합니다. URL·경로 원문은 전송하지 않습니다.
        </p>
        {context.items.map((row) => (
          <article key={row.id}>
            <code className="observation-url">{row.url}</code>
            <p>
              {labels[row.category] || row.category} · 범위 버전{" "}
              {row.scope_revision} · 작업 {row.task_id}
            </p>
          </article>
        ))}
        {!context.items.length && <p>계획 순서에 사용할 관찰이 없습니다.</p>}
      </details>
    </section>
  );
}
export function TodoPlanBasis({
  context,
  names,
  planner,
}: {
  context?: TodoPlanContext;
  names: Record<string, string>;
  planner: string;
}) {
  if (!context) return null;
  if (
    !Array.isArray(context.items) ||
    context.items.length > 100 ||
    context.items.some(
      (row) =>
        !row ||
        typeof row.id !== "string" ||
        !Number.isSafeInteger(row.revision) ||
        row.revision < 1 ||
        typeof row.status !== "string" ||
        typeof row.title !== "string" ||
        typeof row.description !== "string" ||
        !Array.isArray(row.check_ids) ||
        row.check_ids.some((id) => typeof id !== "string"),
    )
  )
    return <p role="alert">저장된 할 일 계획 맥락의 형식을 확인하세요.</p>;
  return (
    <section
      className="next-plan todo-plan-basis"
      aria-label="계획에 저장된 공유 할 일"
    >
      <details>
        <summary>계획에 저장된 공유 할 일 · {context.items.length}개</summary>
        <p>
          계획 생성 시점의 항목과 버전입니다. 현재 할 일과 다를 수 있으며 새
          내용으로 계획을 바꾸려면 재계획하세요.
        </p>
        {planner === "ai" && (
          <p>
            미완료·진행 중 항목의 제목·설명·도구 요청을 설정된 AI 제공자에게
            전송해 승인된 도구의 순서를 정합니다.
          </p>
        )}
        {context.items.map((row) => (
          <article key={row.id}>
            <strong>{row.title}</strong>
            <p>
              버전 {row.revision} ·{" "}
              {(
                {
                  open: "미완료",
                  in_progress: "진행 중",
                  done: "완료",
                  cancelled: "취소",
                } as Record<string, string>
              )[row.status] || row.status}
            </p>
            <p>{row.description}</p>
            <p>
              요청 도구:{" "}
              {row.check_ids.map((id) => names[id] || id).join(", ") || "없음"}
            </p>
          </article>
        ))}
        {!context.items.length && <p>참조한 공유 할 일이 없습니다.</p>}
      </details>
    </section>
  );
}
type Proposal = {
  worker_observation_context?: ObservationPlanContext;
  format: "aegis-next-plan-v1";
  source_task_id: string;
  fingerprint: string;
  planning_round: number;
  round_limit: number;
  available: boolean;
  reason: string;
  task: null | {
    name: string;
    goal: string;
    asset_ids: string[];
    checks: string[];
    workers: number;
    planner: string;
    worker_dependencies: Record<string, string[]>;
  };
  scope_snapshot: {
    id: string;
    name: string;
    url: string;
    revision?: number;
  }[];
  execution_policy: ExecutionPolicy;
  tool_contracts?: ToolManifest;
  basis: {
    missing_checks: string[];
    retry_checks: string[];
    todo_requested_checks?: string[];
    coverage: Cell[];
    skipped_cells: string[];
    repeated_completed_cells: string[];
  };
  shared_todo_context?: {
    fingerprint: string;
    items: {
      id: string;
      revision: number;
      status: string;
      title: string;
      description: string;
      check_ids: string[];
    }[];
  };
  accepted_task_id?: string | null;
  accepted_kind?: "followup" | "retry" | null;
};
const reasons: Record<string, string> = {
  already_accepted: "이 결과에서 이미 연결된 계획을 만들었습니다.",
  round_limit:
    "후속 계획 회차 한도에 도달했습니다. 결과와 실패 원인을 검토하세요.",
  history_limit:
    "교체·재실행을 포함한 연결 이력 한도에 도달했습니다. 기존 결과와 실행 범위를 검토하세요.",
  no_remaining_checks:
    "현재 결과에서 제안할 추가·재시도 검증이 없습니다. 자산의 안전성을 보장하는 판정은 아닙니다.",
};
const statuses: Record<string, string> = {
  completed: "완료",
  failed: "실패",
  cancelled: "취소",
  interrupted: "중단",
  not_recorded: "기록 없음",
  not_started: "미실행",
  running: "완료 미확인",
  stale: "오래된 결과",
  skipped: "건너뜀",
};

function AutomaticPlanStatus({
  taskId,
  displayedFingerprint,
}: {
  taskId: string;
  displayedFingerprint?: string;
}) {
  const [notice, setNotice] = useState(
    "자동 계획 준비 상태를 확인하고 있습니다.",
  );
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const request = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let active = true;
    async function read() {
      try {
        const row = await api<{
          format: string;
          source_task_id: string;
          status: string;
          stale?: boolean;
          event_seq?: number;
          proposal?: { fingerprint: string } | null;
        }>(
          "/tasks/" + encodeURIComponent(taskId) + "/planner",
          "GET",
          undefined,
          request.signal,
        );
        if (!active) return;
        if (
          row.format !== "aegis-event-planner-v1" ||
          row.source_task_id !== taskId
        )
          throw new Error("다른 작업의 자동 계획 상태입니다. 다시 조회하세요.");
        setFailed(false);
        setNotice(
          row.stale
            ? "자동 계획 근거가 변경되었습니다. 최신 제안을 조회해 검토하세요."
            : row.proposal &&
                displayedFingerprint &&
                row.proposal?.fingerprint !== displayedFingerprint
              ? "새 이벤트가 반영됐습니다. 현재 표시된 제안은 이전 내용이므로 다시 조회하세요."
              : row.status === "ready"
                ? "이벤트 " +
                  row.event_seq +
                  "를 반영해 다음 계획을 자동으로 준비했습니다. 아래에서 제안을 검토하세요."
                : row.status === "no_proposal"
                  ? "이벤트를 반영했습니다. 추가 제안이 없거나 이미 연결된 계획이 있습니다."
                  : row.status === "blocked"
                    ? "자동 계획 준비가 보류됐습니다. 계획 근거·범위·공유 할 일을 확인하세요."
                    : "종료·변경 이벤트의 자동 계획 처리를 기다리고 있습니다.",
        );
        timer = setTimeout(() => void read(), 4000);
      } catch (error) {
        if (!active || request.signal.aborted) return;
        setFailed(true);
        setNotice((error as Error).message);
      }
    }
    void read();
    return () => {
      active = false;
      request.abort();
      if (timer) clearTimeout(timer);
    };
  }, [taskId, attempt, displayedFingerprint]);
  return (
    <div className="automatic-plan-status">
      <p role={failed ? "alert" : "status"}>{notice}</p>
      {failed && (
        <button type="button" onClick={() => setAttempt((value) => value + 1)}>
          자동 계획 상태 다시 조회
        </button>
      )}
    </div>
  );
}

export function NextPlan({
  taskId,
  canOperate,
  busy,
  names,
  onAccept,
  onTask,
}: {
  taskId: string;
  canOperate: boolean;
  busy: boolean;
  names: Record<string, string>;
  onAccept: (
    fingerprint: string,
    onFailure: (message: string) => void,
  ) => Promise<unknown>;
  onTask: (id: string) => void;
}) {
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const savingRef = useRef(false);
  const queryButton = useRef<HTMLButtonElement>(null);
  const focusError = useRef(false);
  useEffect(() => {
    if (focusError.current && !loading && !saving && !busy) {
      focusError.current = false;
      queryButton.current?.focus();
    }
  }, [loading, saving, busy, error]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      controller.current?.abort();
    };
  }, []);
  async function load() {
    if (savingRef.current) return;
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError("");
    setProposal(null);
    try {
      const result = await api<Proposal>(
        "/tasks/" + encodeURIComponent(taskId) + "/next-plan",
        "GET",
        undefined,
        request.signal,
      );
      if (!mounted.current || controller.current !== request) return;
      if (
        result.format !== "aegis-next-plan-v1" ||
        result.source_task_id !== taskId
      )
        throw new Error("다른 작업의 제안입니다. 다시 조회하세요.");
      setProposal(result);
    } catch (e) {
      if (
        mounted.current &&
        controller.current === request &&
        !request.signal.aborted
      ) {
        focusError.current = true;
        setError((e as Error).message);
      }
    } finally {
      if (mounted.current && controller.current === request) setLoading(false);
    }
  }
  async function accept() {
    if (
      !proposal?.available ||
      busy ||
      savingRef.current ||
      loading ||
      !canOperate
    )
      return;
    savingRef.current = true;
    setSaving(true);
    setError("");
    try {
      await onAccept(proposal.fingerprint, (message) => {
        if (!mounted.current) return;
        focusError.current = true;
        setError(message + " 제안을 다시 조회한 뒤 검토하세요.");
        setProposal(null);
      });
    } finally {
      savingRef.current = false;
      if (mounted.current) setSaving(false);
    }
  }
  const assetName = (id: string) =>
    proposal?.scope_snapshot.find((a) => a.id === id)?.name || id;
  const checkNames = (checks: string[]) =>
    checks.map((c) => names[c] || c).join(", ") || "없음";
  return (
    <section
      className="next-plan finding-collection"
      aria-label="결과 기반 다음 계획"
    >
      <h4 className="detail-heading">결과 기반 다음 계획</h4>
      <p className="subtle">
        종료된 작업과 이전 회차의 결과에서 추가·재시도 검증을 제안합니다.
        반영하면 새 승인 대기 계획을 만들며 실행은 별도 관리자 승인이
        필요합니다.
      </p>
      <AutomaticPlanStatus
        key={taskId}
        taskId={taskId}
        displayedFingerprint={proposal?.fingerprint}
      />
      <button
        ref={queryButton}
        type="button"
        disabled={loading || saving || busy}
        onClick={() => void load()}
      >
        {loading
          ? "다음 계획 조회 중…"
          : proposal
            ? "제안 다시 조회"
            : "다음 계획 제안 보기"}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div aria-live="polite">
        {saving && <p>후속 승인 계획을 저장하고 있습니다.</p>}
      </div>
      {proposal && (
        <>
          {!proposal.available && (
            <p>
              {reasons[proposal.reason] || "현재 제안을 반영할 수 없습니다."}
            </p>
          )}
          {proposal.accepted_task_id && (
            <button
              type="button"
              disabled={busy || saving}
              onClick={() => onTask(proposal.accepted_task_id!)}
            >
              {proposal.accepted_kind === "retry"
                ? "이미 만든 재실행 계획 보기"
                : "이미 만든 후속 계획 보기"}
            </button>
          )}
          {proposal.available && proposal.task && (
            <>
              <p>
                <strong>{proposal.task.name}</strong> · 후속{" "}
                {proposal.planning_round} / 최대 {proposal.round_limit}회차
              </p>
              <p>추가 검증: {checkNames(proposal.basis.missing_checks)}</p>
              <p>재시도 검증: {checkNames(proposal.basis.retry_checks)}</p>
              <p>
                공유 할 일의 검증 요청:{" "}
                {checkNames(proposal.basis.todo_requested_checks || [])}
              </p>
              <WorkerObservationBasis
                context={proposal.worker_observation_context}
              />
              {proposal.shared_todo_context && (
                <section
                  className="todo-plan-basis"
                  aria-label="다음 계획이 참조한 공유 할 일"
                >
                  <details>
                    <summary>
                      참조한 공유 할 일 ·{" "}
                      {proposal.shared_todo_context.items.length}개
                    </summary>
                    <p>
                      생성 시점의 항목과 버전을 저장합니다. AI 계획을 선택하면
                      미완료·진행 중 항목의 제목·설명·도구 요청을 설정된
                      제공자에게 전송합니다.
                    </p>
                    {proposal.shared_todo_context.items.map((row) => (
                      <article key={row.id}>
                        <strong>{row.title}</strong>
                        <p>
                          버전 {row.revision} ·{" "}
                          {(
                            {
                              open: "미완료",
                              in_progress: "진행 중",
                              done: "완료",
                              cancelled: "취소",
                            } as Record<string, string>
                          )[row.status] || row.status}{" "}
                          · {checkNames(row.check_ids)}
                        </p>
                      </article>
                    ))}
                    {!proposal.shared_todo_context.items.length && (
                      <p>참조할 공유 할 일이 없습니다.</p>
                    )}
                  </details>
                </section>
              )}

              <p>
                {proposal.task.workers}개 Worker ·{" "}
                {proposal.task.planner === "ai"
                  ? "AI 도구 순서 계획"
                  : "규칙 기반 도구 순서"}
              </p>
              <h4 className="detail-heading">새 계획의 현재 자산 범위</h4>
              {proposal.scope_snapshot.map((asset) => (
                <div className="finding-record" key={asset.id}>
                  <strong>{asset.name}</strong> · revision {asset.revision || 1}
                  <code className="observation-url">{asset.url}</code>
                </div>
              ))}
              <WorkerDependencies
                dependencies={proposal.task.worker_dependencies}
                assets={proposal.scope_snapshot}
              />
              <details>
                <summary>새 계획의 실행 제한</summary>
                <PolicySummary policy={proposal.execution_policy} />
              </details>
              <ToolContracts
                snapshot={proposal.tool_contracts}
                current={proposal.tool_contracts}
                selected={proposal.task.checks}
                names={names}
                pending={false}
              />
              <p className="subtle">
                한 도구를 선택하면 모든 선택 자산에서 수행합니다. 다른 자산의
                완료 검증도 반복될 수 있습니다.
              </p>
              <p>
                반복될 완료 검증{" "}
                {proposal.basis.repeated_completed_cells.length}개 · 건너뛴 결과{" "}
                {proposal.basis.skipped_cells.length}개
              </p>
              <button
                type="button"
                disabled={!canOperate || busy || saving || loading}
                onClick={() => void accept()}
              >
                {saving
                  ? "승인 대기 계획 저장 중…"
                  : "제안을 승인 대기 계획으로 반영"}
              </button>
              {!canOperate && (
                <p className="subtle">
                  후속 계획 생성은 운영자 또는 관리자가 할 수 있습니다.
                </p>
              )}
            </>
          )}
          <details>
            <summary>
              제안 근거 · 자산별 최신 검증 {proposal.basis.coverage.length}개
            </summary>
            <p className="subtle">
              건너뜀은 완료나 안전성의 근거가 아닙니다. 오래된 결과는 현재 자산
              revision 또는 도구 계약과 다릅니다.
            </p>
            {proposal.basis.coverage.map((cell) => {
              const suffix = ":" + cell.asset_id + ":" + cell.check;
              const origin = cell.id.endsWith(suffix)
                ? cell.id.slice(0, -suffix.length)
                : null;
              const repeated = proposal.basis.repeated_completed_cells.includes(
                cell.id,
              );
              return (
                <div className="finding-record" key={cell.id}>
                  <strong>
                    {assetName(cell.asset_id)} ·{" "}
                    {names[cell.check] || cell.check}
                  </strong>
                  <p>
                    {statuses[cell.status] || "상태 미확인"} · 당시 revision{" "}
                    {cell.asset_revision}
                    {repeated ? " · 새 계획에서 반복 예정" : ""}
                  </p>
                  {origin && (
                    <button
                      type="button"
                      disabled={saving || busy}
                      onClick={() => onTask(origin)}
                    >
                      근거 작업 보기
                    </button>
                  )}
                </div>
              );
            })}
          </details>
        </>
      )}
    </section>
  );
}
