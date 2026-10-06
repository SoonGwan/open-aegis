/** Per-request browser receipts; authoritative operation results remain on the server. */
export type ModelBody = Record<string, string | number | boolean | null>;
export type PendingModelRequest = { version: 1; actor: string; path: string; method: "PUT" | "POST"; body: ModelBody; created_at: number };
export interface PendingStorage { readonly length: number; key(index: number): string | null; getItem(key: string): string | null; setItem(key: string, value: string): void; removeItem(key: string): void }
const PREFIX = "aegis.pending.models.v1.";
const TTL = 24 * 60 * 60 * 1000;
const ID = /^[A-Za-z0-9_-]{1,64}$/;
const REQUEST = /^[A-Za-z0-9_-]{16,80}$/;
const PATH = /^\/(?:model-profiles(?:\/[A-Za-z0-9_-]{1,64}(?:\/(?:catalog|connection-test))?)?|model-defaults\/(?:planner|conversation)|tasks\/[A-Za-z0-9_-]{1,64}\/models\/(?:planner|conversation))$/;

export class PendingModelError extends Error {
  constructor(message: string) { super(message); this.name = "PendingModelError"; }
}
function scope(actor: string, path: string, method: string) {
  if (!ID.test(actor) || !PATH.test(path) || !operation(path, method)) throw new PendingModelError("요청의 계정·리소스를 확인할 수 없습니다.");
  return PREFIX + encodeURIComponent(actor) + "." + encodeURIComponent(path) + "." + method + ".";
}
function operation(path: string, method: string) {
  if (path === "/model-profiles" || /\/(?:catalog|connection-test)$/.test(path)) return method === "POST";
  return method === "PUT";
}
const sameBody = (a: ModelBody, b: ModelBody) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
function encoded(request: PendingModelRequest) {
  const text = JSON.stringify(request);
  if (new TextEncoder().encode(text).length > 4096) throw new PendingModelError("브라우저에 보존할 모델 요청의 크기를 초과했습니다.");
  return text;
}
function valid(value: unknown): value is PendingModelRequest {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const row = value as PendingModelRequest;
  if (Object.keys(row).sort().join() !== "actor,body,created_at,method,path,version" || row.version !== 1 ||
      typeof row.actor !== "string" || !ID.test(row.actor) || typeof row.path !== "string" || !PATH.test(row.path) ||
      !operation(row.path, row.method) || !Number.isSafeInteger(row.created_at) || row.created_at < 0 ||
      !row.body || typeof row.body !== "object" || Array.isArray(row.body)) return false;
  const body = row.body;
  if (typeof body.request_id !== "string" || !REQUEST.test(body.request_id)) return false;
  const query = /\/(?:catalog|connection-test)$/.test(row.path);
  const profile = /^\/model-profiles(?:\/[A-Za-z0-9_-]+)?$/.test(row.path);
  const allowed = query ? ["expected_revision", "request_id"] : profile
    ? ["name", "model", "destination_id", "enabled", "request_id", ...(row.method === "PUT" ? ["expected_revision"] : [])]
    : ["expected_revision", "profile_id", "expected_profile_revision", "request_id", ...(row.path.startsWith("/tasks/") ? ["expected_archive_revision"] : [])];
  if (Object.keys(body).sort().join() !== allowed.sort().join()) return false;
  for (const [key, field] of Object.entries(body)) {
    if (key.startsWith("expected_")) {
      if (key === "expected_profile_revision" && field === null) continue;
      if (typeof field !== "number" || !Number.isSafeInteger(field) || field < 0) return false;
    } else if (key === "enabled") { if (typeof field !== "boolean") return false; }
    else if (key === "profile_id") { if (field !== null && (typeof field !== "string" || !ID.test(field))) return false; }
    else if (typeof field !== "string" || field.length > (key === "model" ? 160 : 100)) return false;
  }
  return true;
}
function keys(storage: PendingStorage, prefix: string) {
  const result: string[] = [];
  for (let index = 0; index < storage.length; index++) {
    const key = storage.key(index); if (key?.startsWith(prefix)) result.push(key);
  }
  return result;
}
export function loadModelPending(storage: PendingStorage, actor: string, path: string, method: "PUT" | "POST", clock = Date.now()): PendingModelRequest[] {
  const prefix = scope(actor, path, method), result: PendingModelRequest[] = [];
  try {
    for (const key of keys(storage, prefix)) {
      const text = storage.getItem(key); if (text === null) continue;
      if (new TextEncoder().encode(text).length > 4096) throw new Error();
      const row: unknown = JSON.parse(text);
      if (!valid(row) || row.actor !== actor || row.path !== path || row.method !== method || key !== prefix + row.body.request_id || row.created_at > clock + 60_000) throw new Error();
      if (clock - row.created_at >= TTL) { storage.removeItem(key); continue; }
      result.push(row);
    }
    if (result.length > 20) throw new Error();
  } catch { throw new PendingModelError("이 리소스의 브라우저 요청 기록을 읽지 못했습니다. 기록을 확인하거나 정리한 뒤 다시 여세요."); }
  return result.sort((a, b) => a.created_at - b.created_at || String(a.body.request_id).localeCompare(String(b.body.request_id)));
}
export function storeModelPending(storage: PendingStorage, request: PendingModelRequest): void {
  if (!valid(request)) throw new PendingModelError("보존할 모델 요청의 형식을 확인하세요.");
  const prefix = scope(request.actor, request.path, request.method), key = prefix + request.body.request_id, text = encoded(request);
  try {
    const previous = storage.getItem(key);
    if (previous !== null) {
      const row = JSON.parse(previous);
      if (!valid(row) || row.actor !== request.actor || row.path !== request.path || row.method !== request.method || !sameBody(row.body, request.body)) throw new Error();
      return; // Preserve the original creation time and expiry when confirming a request.
    }
    if (loadModelPending(storage, request.actor, request.path, request.method, request.created_at).length >= 20) throw new Error();
    storage.setItem(key, text);
    if (storage.getItem(key) !== text) throw new Error();
  } catch { throw new PendingModelError("요청을 브라우저에 보존하지 못해 서버로 보내지 않았습니다. 저장소 사용 권한이나 용량을 확인하세요."); }
}
export function finishModelPending(storage: PendingStorage, request: PendingModelRequest): void {
  const key = scope(request.actor, request.path, request.method) + request.body.request_id;
  try {
    const text = storage.getItem(key);
    if (text !== null) {
      const row = JSON.parse(text);
      if (!valid(row) || row.actor !== request.actor || row.path !== request.path || row.method !== request.method || !sameBody(row.body, request.body)) throw new Error();
      storage.removeItem(key);
    }
  } catch { throw new PendingModelError("서버 응답은 받았지만 브라우저 요청 기록을 정리하지 못했습니다. 같은 요청 결과를 다시 확인할 수 있습니다."); }
}
export function clearModelPending(storage: PendingStorage, actor: string, path?: string, method?: "PUT" | "POST"): void {
  const prefix = path && method ? scope(actor, path, method) : PREFIX + encodeURIComponent(actor) + ".";
  if (!ID.test(actor)) throw new PendingModelError("요청 기록의 계정을 확인할 수 없습니다.");
  for (const key of keys(storage, prefix)) storage.removeItem(key);
}
