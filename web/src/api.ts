let sessionRevision = 0;

/** Capture the browser session associated with a request, without reading cookies. */
export function captureSession(): () => boolean {
  const revision = sessionRevision;
  return () => revision === sessionRevision;
}

export function expireSession(isCurrent: () => boolean): void {
  if (!isCurrent()) return;
  sessionRevision++;
  window.dispatchEvent(new Event("aegis-session-expired"));
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const isCurrentSession = captureSession();
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      method,
      signal,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (
      signal?.aborted ||
      (error instanceof Error && error.name === "AbortError")
    )
      throw error;
    throw new Error(
      "서버에 연결할 수 없습니다. 연결 상태를 확인하고 다시 시도하세요.",
    );
  }
  if (!response.ok) {
    let text = "요청을 처리하지 못했습니다.";
    try {
      const data = await response.json();
      text =
        typeof data.detail === "string"
          ? data.detail
          : data.detail?.[0]?.msg || text;
    } catch {
      /* response may be non-JSON */
    }
    if (
      response.status === 401 &&
      !path.startsWith("/auth/") &&
      !signal?.aborted
    )
      expireSession(isCurrentSession);
    throw new Error(text);
  }
  if (method !== "GET" && /^\/auth\/(login|setup|logout|password)$/.test(path))
    sessionRevision++;
  return response.json();
}
