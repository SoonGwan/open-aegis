export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
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
