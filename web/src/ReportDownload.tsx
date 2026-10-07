import { t as uiText } from "./i18n-core.ts";
import { useEffect, useRef, useState } from "react";
import { Download } from "lucide-react";
import { captureSession, expireSession } from "./api";
import {
  fetchReport,
  fetchPolicy,
  ReportDownloadError,
  type ReportFormat,
} from "./report-download";

export function ReportDownload({
  format,
  taskId,
  label,
}: {
  label: string;
} & (
  | { format: ReportFormat; taskId?: string }
  | { format: "policy"; taskId: string }
)) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [retryAt, setRetryAt] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!retryAt) {
      setSeconds(0);
      return;
    }
    const update = () => {
      const remaining = Math.max(0, Math.ceil((retryAt - Date.now()) / 1000));
      setSeconds(remaining);
      if (!remaining) setRetryAt(0);
    };
    update();
    const timer = setInterval(update, 250);
    return () => clearInterval(timer);
  }, [retryAt]);
  async function download() {
    if (controller.current || retryAt > Date.now()) return;
    const request = new AbortController();
    const isCurrentSession = captureSession();
    controller.current = request;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const result = await (format === "policy"
        ? fetchPolicy(taskId, request.signal)
        : fetchReport(format, taskId, request.signal));
      if (!active.current || request.signal.aborted || !isCurrentSession()) return;
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      setRetryAt(0);
      setSaved(true);
    } catch (e) {
      if (!active.current || !isCurrentSession()) return;
      if (request.signal.aborted) setError(uiText("다운로드를 중단했습니다."));
      else {
        const error = e as ReportDownloadError;
        if (error.status === 401)
          expireSession(isCurrentSession);
        setError(error.message);
        setRetryAt(error.retryAfter ? Date.now() + error.retryAfter * 1000 : 0);
      }
    } finally {
      if (controller.current === request) controller.current = null;
      if (active.current) setBusy(false);
    }
  }
  return (
    <div className="report-download">
      <div className="report-download-actions">
        <button
          type="button"
          disabled={busy || seconds > 0}
          onClick={() => void download()}
        >
          <Download size={15} />
          {busy
            ? format === "policy"
              ? uiText("정책 파일 받는 중…")
              : uiText("보고서 받는 중…")
            : seconds > 0
              ? uiText("{0}초 후 재시도", [seconds])
              : error
                ? uiText("다운로드 다시 시도")
                : label}
        </button>
        {busy && (
          <button type="button" onClick={() => controller.current?.abort()}>
            {uiText("다운로드 중단")}</button>
        )}
      </div>
      {busy && <p role="status">{uiText("파일을 모두 받은 뒤 저장을 시작합니다.")}</p>}
      {error && <p role="alert">{error}</p>}
      {saved && <p role="status">{uiText("파일 다운로드를 시작했습니다.")}</p>}
    </div>
  );
}
