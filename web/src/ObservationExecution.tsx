import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import { pendingStorage } from "./chat-pending";
import type { ObservationPlanContext } from "./NextPlan";

export type ObservationExecutionInput = {
  fingerprint: string;
  observation_ids: string[];
  checks: string[];
  request_id: string;
};
export type ObservationExecution = {
  source_task_id: string;
  targets: {
    id: string;
    url: string;
    asset_id: string;
    scope_revision: number;
  }[];
};
const key = (actor: string, task: string, objective?: string) =>
  "aegis:observation-request:" + JSON.stringify(objective ? [actor, task, objective] : [actor, task]);
const allowed = [
  "security_headers",
  "transport_security",
  "cookie_policy",
  "cors_policy",
];
function read(actor: string, task: string, objective?: string): ObservationExecutionInput | null {
  try {
    const raw = pendingStorage()?.getItem(key(actor, task, objective));
    if (!raw || raw.length > 5000) return null;
    const value = JSON.parse(raw) as ObservationExecutionInput;
    if (
      !/^[a-f0-9]{32}$/.test(value.request_id) ||
      !/^[a-f0-9]{64}$/.test(value.fingerprint) ||
      !Array.isArray(value.observation_ids) ||
      !value.observation_ids.length ||
      value.observation_ids.length > 10 ||
      value.observation_ids.some(
        (id) => typeof id !== "string" || !/^[a-f0-9]{64}$/.test(id),
      ) ||
      new Set(value.observation_ids).size !== value.observation_ids.length ||
      !Array.isArray(value.checks) ||
      !value.checks.length ||
      value.checks.length > 4 ||
      value.checks.some((id) => !allowed.includes(id)) ||
      new Set(value.checks).size !== value.checks.length
    )
      return null;
    return {
      fingerprint: value.fingerprint,
      observation_ids: value.observation_ids,
      checks: value.checks,
      request_id: value.request_id,
    };
  } catch {
    return null;
  }
}

export type GoalObservationRef = {source_task_id:string;source_task_name:string;objective_title:string;objective_id:string};
export function GoalObservationOrigin({origin,onTask}:{origin?:GoalObservationRef;onTask:(id:string)=>void}) {
  if(!origin)return null;
  return <section className="next-plan" aria-label="관찰 검사의 원래 목표 과제">
    <h4>목표 과제에서 선택한 관찰 검사</h4>
    <p>{origin.source_task_name} · {origin.objective_title}</p>
    <p>과제에 속한 자산의 관찰 URL과 선언한 응답 검사를 선택한 계획입니다. 실행에는 별도 관리자 승인이 필요합니다. 기본 응답 완료율이나 자연어 목표 달성으로 합치지 않습니다.</p>
    <button type="button" onClick={()=>onTask(origin.source_task_id)}>원래 목표 작업 열기</button>
  </section>;
}

export function ObservationExecutionBasis({
  execution,
}: {
  execution?: ObservationExecution;
}) {
  if (!execution) return null;
  return (
    <section className="next-plan observation-execution" aria-label="승인할 관찰 응답 요청">
      <h4>선택한 관찰 응답 검증</h4>
      <p>
        아래 URL에 GET 요청을 보내 선택한 응답 설정을 검증합니다. 실행은 관리자
        승인이 필요합니다. URL별 결과를 기록하며 기본 자산 응답의 완료율에는
        포함하지 않습니다.
      </p>
      {execution.targets.map((row) => (
        <article key={row.id}>
          <code className="observation-url">{row.url}</code>
          <p>
            범위 버전 {row.scope_revision} · 관찰 {row.id}
          </p>
        </article>
      ))}
    </section>
  );
}

export function ObservationExecutionPicker({
  taskId,
  actorId,
  names,
  canOperate,
  busy,
  captureView,
  onCreated,
  objectiveId,
  objectiveTitle,
}: {
  taskId: string;
  actorId: string;
  names: Record<string, string>;
  canOperate: boolean;
  busy: boolean;
  captureView: () => () => boolean;
  onCreated: (id: string, current: () => boolean) => Promise<void>;
  objectiveId?: string;
  objectiveTitle?: string;
}) {
  const storageKey=key(actorId,taskId,objectiveId);
  const path="/tasks/"+encodeURIComponent(taskId)+(objectiveId?"/goal-objectives/"+encodeURIComponent(objectiveId):"")+"/observation-plan";
  const [pending, setPending] = useState(() => read(actorId, taskId, objectiveId));
  const [ids, setIds] = useState<string[]>(pending?.observation_ids || []);
  const [checks, setChecks] = useState<string[]>(
    pending?.checks || ["security_headers"],
  );
  const [preview, setPreview] = useState<{
    context: ObservationPlanContext;
    checks: string[];
    max_targets: number;
    fingerprint?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false),
    [saving, setSaving] = useState(false),
    [error, setError] = useState("");
  const active = useRef(true),
    locked = useRef(false),
    controller = useRef<AbortController | null>(null);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  async function load() {
    if (loading || locked.current || busy) return;
    const view = captureView(),
      session = captureSession();
    const request = new AbortController();
    controller.current?.abort();
    controller.current = request;
    setLoading(true);
    setError("");
    try {
      const result = await api<{
        context: ObservationPlanContext;
        checks: string[];
        max_targets: number;
        fingerprint?: string;
      }>(
        path,
        "GET",
        undefined,
        request.signal,
      );
      if (active.current && view() && session()) {
        setPreview(result);
        if (!pending) {
          setIds([]);
          setChecks(previous=>{const selected=previous.filter(check=>result.checks.includes(check));return selected.length?selected:result.checks.slice(0,1);});
        }
      }
    } catch (err) {
      if (active.current && view() && session() && !request.signal.aborted)
        setError(err instanceof Error ? err.message : "목록 조회 실패");
    } finally {
      if (active.current && controller.current === request) setLoading(false);
    }
  }
  async function create() {
    if (
      locked.current ||
      busy ||
      loading ||
      !canOperate ||
      (!pending && (!preview || !ids.length || !checks.length))
    )
      return;
    const request = pending || {
      fingerprint: preview!.fingerprint || preview!.context.fingerprint,
      observation_ids: ids,
      checks,
      request_id: crypto.randomUUID().replaceAll("-", ""),
    };
    try {
      const storage = pendingStorage();
      if (!storage) throw new Error();
      storage.setItem(storageKey, JSON.stringify(request));
    } catch {
      setError(
        "요청 복구 정보를 저장하지 못했습니다. 브라우저 저장소를 확인하세요.",
      );
      return;
    }
    locked.current = true;
    setPending(request);
    setSaving(true);
    setError("");
    const view = captureView(),
      session = captureSession(),
      current = () => active.current && view() && session();
    try {
      const task = await api<{ id: string }>(
        path,
        "POST",
        request,
      );
      if (!session()) return;
      try {
        if (read(actorId, taskId, objectiveId)?.request_id === request.request_id)
          pendingStorage()?.removeItem(storageKey);
      } catch {
        /* Exact replay is safe if storage cleanup fails. */
      }
      if (current()) {
        setPending(null);
        await onCreated(task.id, current);
      }
    } catch (err) {
      if (current()) {
        if (err instanceof ApiError && err.status === 409) {
          try {
            pendingStorage()?.removeItem(storageKey);
          } catch {
            /* Keep replay information when storage is unavailable. */
          }
          setPending(null);
          setPreview(null);
          setIds([]);
        }
        setError(err instanceof Error ? err.message : "계획 반영 실패");
      }
    } finally {
      locked.current = false;
      if (active.current) setSaving(false);
    }
  }
  return (
    <section className="next-plan observation-execution" aria-label={objectiveId?"과제의 관찰 응답 검사 · "+objectiveTitle:"관찰 응답 검사 계획"}>
      <h4>{objectiveId?"이 과제의 관찰 응답 검사":"관찰 응답 검사 계획"}</h4>
      {objectiveId && <p>이 과제에 선언된 자산의 관찰과 응답 검사만 선택합니다. 새 계획에도 원래 과제 출처를 보존합니다.</p>}
      {preview && !preview.checks.length && <p role="status">이 과제에는 지원하는 응답 검사가 없습니다. 목표 초안을 새로 검토해 검사 범위를 정하세요.</p>}
      <p>
        출처와 현재 범위를 확인한 관찰 중 최대 10개를 선택합니다. 계획 생성과
        URL 조회는 별개이며 새 계획의 관리자 승인 후 GET 요청을 보냅니다.
      </p>
      <button
        type="button"
        onClick={() => void load()}
        disabled={busy || loading || saving || !!pending}
      >
        {loading ? "관찰 확인 중…" : "검사할 관찰 확인"}
      </button>
      {error && <p role="alert">{error}</p>}
      {pending && (
        <p role="status">
          이전 반영 요청의 결과를 확인해야 합니다. 선택을 유지한 채 같은
          요청으로 다시 확인합니다.
        </p>
      )}
      {preview && (
        <>
          <p>
            전체 {preview.context.counts.total}개 · 사용 가능{" "}
            {preview.context.counts.included}개 · 제외{" "}
            {preview.context.counts.excluded}개 · 표본 밖{" "}
            {preview.context.counts.omitted}개
          </p>
          <fieldset disabled={busy || saving || !!pending || !canOperate}>
            <legend>검사할 관찰 URL</legend>
            {preview.context.items.map((row) => (
              <label key={row.id} className="observation-url">
                <input
                  type="checkbox"
                  checked={ids.includes(row.id)}
                  disabled={!ids.includes(row.id) && ids.length >= 10}
                  onChange={(e) =>
                    setIds(
                      e.target.checked
                        ? [...ids, row.id]
                        : ids.filter((id) => id !== row.id),
                    )
                  }
                />
                {row.url}
              </label>
            ))}
            {!preview.context.items.length && (
              <p>현재 검사할 수 있는 관찰이 없습니다.</p>
            )}
          </fieldset>
          <fieldset disabled={busy || saving || !!pending || !canOperate}>
            <legend>관찰 응답의 검증 도구</legend>
            {preview.checks.map((id) => (
              <label key={id}>
                <input
                  type="checkbox"
                  checked={checks.includes(id)}
                  onChange={(e) =>
                    setChecks(
                      e.target.checked
                        ? [...checks, id]
                        : checks.filter((c) => c !== id),
                    )
                  }
                />
                {names[id] || id}
              </label>
            ))}
          </fieldset>
        </>
      )}
      {pending && !preview && (
        <p>
          저장된 선택: 관찰 {pending.observation_ids.length}개 ·{" "}
          {pending.checks.map((c) => names[c] || c).join(", ")}
        </p>
      )}
      <button
        type="button"
        onClick={() => void create()}
        disabled={
          busy ||
          loading ||
          saving ||
          !canOperate ||
          (!pending && (!ids.length || !checks.length))
        }
      >
        {saving
          ? "반영 중…"
          : pending
            ? "같은 요청으로 결과 확인"
            : "선택한 관찰의 승인 대기 계획 만들기"}
      </button>
      {!canOperate && <p>관리자 또는 운영자가 계획을 만들 수 있습니다.</p>}
    </section>
  );
}
