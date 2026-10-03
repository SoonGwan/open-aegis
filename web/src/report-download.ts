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
  try {
    const response = await request(`/api/reports/export?${query}`, {
      credentials: "same-origin",
      signal,
    });
    if (!response.ok) {
      let message = "보고서를 다운로드하지 못했습니다.";
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
    const media = {
      json: "application/json",
      csv: "text/csv",
      markdown: "text/markdown",
    }[format];
    if (
      response.headers
        .get("Content-Type")
        ?.split(";")[0]
        .trim()
        .toLowerCase() !== media
    )
      throw new ReportDownloadError(
        "보고서 파일 형식을 확인할 수 없습니다. 다시 시도하세요.",
        response.status,
      );
    const blob = await response.blob();
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    if (!blob.size)
      throw new ReportDownloadError(
        "빈 보고서 파일을 받았습니다. 다시 시도하세요.",
      );
    return {
      blob,
      filename: `aegis-report.${format === "markdown" ? "md" : format}`,
    };
  } catch (error) {
    if (signal.aborted || error instanceof ReportDownloadError) throw error;
    throw new ReportDownloadError(
      "파일 다운로드를 완료하지 못했습니다. 연결 상태를 확인하고 다시 시도하세요.",
    );
  }
}
