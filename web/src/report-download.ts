import { t as uiText } from "./i18n-core.ts";
export type ReportFormat = "json" | "csv" | "markdown";
export class ReportDownloadError extends Error {
  status: number | null;
  retryAfter: number;
  constructor(message: string, status: number | null = null, retryAfter = 0) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}
export function retrySeconds(header: string | null, now = Date.now()): number {
  if (!header) return 0;
  const value = /^\d+$/.test(header)
    ? Number(header)
    : Math.ceil((Date.parse(header) - now) / 1000);
  return Number.isFinite(value) ? Math.min(600, Math.max(0, value)) : 0;
}
export async function fetchReport(
  format: ReportFormat,
  taskId: string | undefined,
  signal: AbortSignal,
  request: typeof fetch = fetch,
): Promise<{ blob: Blob; filename: string }> {
  const query = new URLSearchParams({ format });
  if (taskId) query.set("task_id", taskId);
  return fetchFile(
    `/api/reports/export?${query}`,
    {
      json: "application/json",
      csv: "text/csv",
      markdown: "text/markdown",
    }[format],
    `aegis-report.${format === "markdown" ? "md" : format}`,
    signal,
    request,
  );
}
export async function fetchPolicy(
  taskId: string,
  signal: AbortSignal,
  request: typeof fetch = fetch,
) {
  return fetchFile(
    `/api/tasks/${encodeURIComponent(taskId)}/policy-reproduction`,
    "application/json",
    "aegis-api-policy.json",
    signal,
    request,
  );
}
async function fetchFile(
  url: string,
  media: string,
  filename: string,
  signal: AbortSignal,
  request: typeof fetch,
): Promise<{ blob: Blob; filename: string }> {
  try {
    const response = await request(url, {
      credentials: "same-origin",
      signal,
    });
    if (!response.ok) {
      let message = uiText("파일을 다운로드하지 못했습니다.");
      try {
        const data = await response.json();
        if (typeof data.detail === "string") message = data.detail;
      } catch {
        /* An HTML or empty error is still an error, never a report. */
      }
      throw new ReportDownloadError(
        message,
        response.status,
        retrySeconds(response.headers.get("Retry-After")),
      );
    }
    if (
      response.headers
        .get("Content-Type")
        ?.split(";")[0]
        .trim()
        .toLowerCase() !== media
    )
      throw new ReportDownloadError(
        uiText("파일 형식을 확인할 수 없습니다. 다시 시도하세요."),
        response.status,
      );
    const blob = await response.blob();
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    if (!blob.size)
      throw new ReportDownloadError(uiText("빈 파일을 받았습니다. 다시 시도하세요."));
    return {
      blob,
      filename,
    };
  } catch (error) {
    if (signal.aborted || error instanceof ReportDownloadError) throw error;
    throw new ReportDownloadError(
      uiText("파일 다운로드를 완료하지 못했습니다. 연결 상태를 확인하고 다시 시도하세요."),
    );
  }
}
