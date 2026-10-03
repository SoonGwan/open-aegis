export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
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
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("aegis-session-expired"));
    throw new Error(text);
  }
  return response.json();
}
