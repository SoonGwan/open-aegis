import { validateWorkerDependencies, type Dependencies } from "./worker-dependency-state.ts";
import { PendingModelError, type PendingStorage } from "./model-pending.ts";

export type TaskCreationDraft = { name: string; goal: string; asset_ids: string[]; checks: string[]; workers: number; planner: "rules" | "ai"; remote_connection_id: string | null; worker_dependencies: Dependencies };
export type InitialModels = Partial<Record<"planner" | "conversation", { profile_id: string; expected_profile_revision: number }>>;
export type TaskCreationBody = { task: TaskCreationDraft; models: InitialModels; request_id: string };
export type PendingTaskCreation = { version: 1; actor: string; body: TaskCreationBody; created_at: number };
const PREFIX = "aegis.pending.task-model-creation.v1.", TTL = 24 * 60 * 60 * 1000;
const ID = /^[A-Za-z0-9_-]{1,64}$/, REF = /^[A-Za-z0-9_.-]{1,64}$/, REQUEST = /^[A-Za-z0-9_-]{16,80}$/;
const exact = (value: object, fields: string[]) => Object.keys(value).sort().join() === fields.sort().join();
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
function canonical(value: unknown): string {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (object(value)) return "{" + Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => JSON.stringify(key) + ":" + canonical(item)).join(",") + "}";
  const text = JSON.stringify(value);if (text === undefined) throw new Error("Undefined creation field");return text;
}
export function validTaskCreationBody(value: unknown): value is TaskCreationBody {
  if (!object(value) || !exact(value, ["task", "models", "request_id"]) || typeof value.request_id !== "string" || !REQUEST.test(value.request_id)) return false;
  const task = value.task, models = value.models;
  if (!object(task) || !exact(task, ["name", "goal", "asset_ids", "checks", "workers", "planner", "remote_connection_id", "worker_dependencies"]) ||
      typeof task.name !== "string" || !task.name.trim() || task.name.length > 120 || typeof task.goal !== "string" || task.goal.length > 2000 ||
      typeof task.workers !== "number" || !Number.isInteger(task.workers) || task.workers < 1 || task.workers > 4 || typeof task.planner !== "string" || !["rules", "ai"].includes(task.planner) ||
      task.remote_connection_id !== null && (typeof task.remote_connection_id !== "string" || !REF.test(task.remote_connection_id))) return false;
  for (const [field, limit] of [["asset_ids", 20], ["checks", 6]] as const) {
    const rows = task[field];
    if (!Array.isArray(rows) || !rows.length || rows.length > limit || new Set(rows).size !== rows.length || rows.some(item => typeof item !== "string" || !REF.test(item))) return false;
  }
  try { validateWorkerDependencies(task.asset_ids as string[], task.worker_dependencies); } catch { return false; }
  if (!object(models) || !Object.keys(models).length || Object.keys(models).length > 2) return false;
  for (const [purpose, profile] of Object.entries(models)) {
    if (!["planner", "conversation"].includes(purpose) || !object(profile) || !exact(profile, ["profile_id", "expected_profile_revision"]) ||
        typeof profile.profile_id !== "string" || !ID.test(profile.profile_id) || typeof profile.expected_profile_revision !== "number" ||
        !Number.isSafeInteger(profile.expected_profile_revision) || profile.expected_profile_revision < 1) return false;
  }
  return true;
}
function valid(value: unknown): value is PendingTaskCreation {
  return object(value) && exact(value, ["version", "actor", "body", "created_at"]) && value.version === 1 &&
    typeof value.actor === "string" && ID.test(value.actor) && typeof value.created_at === "number" && Number.isSafeInteger(value.created_at) && value.created_at >= 0 && validTaskCreationBody(value.body);
}
function prefix(actor: string) { if (!ID.test(actor)) throw new PendingModelError("작업 생성 요청의 계정을 확인하세요.");return PREFIX + encodeURIComponent(actor) + "."; }
function keys(storage: PendingStorage, actor: string) {
  const found: string[] = [], scope = prefix(actor);
  for (let index = 0; index < storage.length; index++) { const key = storage.key(index);if (key?.startsWith(scope)) found.push(key); }
  return found;
}
export function loadTaskCreationPending(storage: PendingStorage, actor: string, clock = Date.now()): PendingTaskCreation[] {
  try {
    const rows: PendingTaskCreation[] = [], scope = prefix(actor);
    for (const key of keys(storage, actor)) {
      const text = storage.getItem(key);if (text === null) continue;
      if (new TextEncoder().encode(text).length > 16384) throw new Error();
      const row: unknown = JSON.parse(text);
      if (!valid(row) || row.actor !== actor || key !== scope + row.body.request_id || row.created_at > clock + 60_000) throw new Error();
      if (clock - row.created_at >= TTL) { storage.removeItem(key);continue; }
      rows.push(row);
    }
    if (rows.length > 20) throw new Error();
    return rows.sort((a, b) => a.created_at - b.created_at || a.body.request_id.localeCompare(b.body.request_id));
  } catch { throw new PendingModelError("모델을 선택한 작업 생성 기록을 읽지 못했습니다. 이력을 확인하거나 브라우저 기록을 정리하세요."); }
}
export function storeTaskCreationPending(storage: PendingStorage, request: PendingTaskCreation): void {
  if (!valid(request)) throw new PendingModelError("보존할 작업 생성 입력·모델·의존 관계를 확인하세요.");
  try {
    const key = prefix(request.actor) + request.body.request_id, text = JSON.stringify(request), previous = storage.getItem(key);
    if (new TextEncoder().encode(text).length > 16384) throw new Error();
    if (previous !== null) {
      const row: unknown = JSON.parse(previous);
      if (!valid(row) || row.actor !== request.actor || canonical(row.body) !== canonical(request.body)) throw new Error();
      return;
    }
    if (loadTaskCreationPending(storage, request.actor, request.created_at).length >= 20) throw new Error();
    storage.setItem(key, text);if (storage.getItem(key) !== text) throw new Error();
  } catch { throw new PendingModelError("작업 생성 요청을 브라우저에 보존하지 못해 서버로 보내지 않았습니다. 저장소 권한·용량을 확인하세요."); }
}
export function finishTaskCreationPending(storage: PendingStorage, request: PendingTaskCreation): void {
  try {
    const key = prefix(request.actor) + request.body.request_id, text = storage.getItem(key);
    if (text !== null) {
      const row: unknown = JSON.parse(text);
      if (!valid(row) || row.actor !== request.actor || canonical(row.body) !== canonical(request.body)) throw new Error();
      storage.removeItem(key);
    }
  } catch { throw new PendingModelError("서버 결과는 받았지만 작업 생성의 브라우저 기록을 정리하지 못했습니다. 같은 요청으로 확인할 수 있습니다."); }
}
export function clearTaskCreationPending(storage: PendingStorage, actor: string): void {
  for (const key of keys(storage, actor)) storage.removeItem(key);
}
