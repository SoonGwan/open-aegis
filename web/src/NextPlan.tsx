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
type Proposal = {
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
    coverage: Cell[];
    skipped_cells: string[];
    repeated_completed_cells: string[];
  };
  accepted_task_id?: string | null;
};
const reasons: Record<string, string> = {
  already_accepted: "이 결과에서 이미 후속 계획을 만들었습니다.",
  round_limit:
    "후속 계획 회차 한도에 도달했습니다. 결과와 실패 원인을 검토하세요.",
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
              이미 만든 후속 계획 보기
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
