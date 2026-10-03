import { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "./api";

type Checkpoint = {
  format: string;
  chain_id: string;
  seq: number;
  hash: string;
};
type Result = {
  status: "verified" | "mismatch" | "inconclusive";
  checked_at: number;
  checkpoint_compared: boolean;
  events?: number;
  sealed_legacy_until?: number;
  checkpoint?: Checkpoint;
  detail?: string;
};

export function AuditPanel() {
  const [checkpoint, setCheckpoint] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  async function verify() {
    if (request.current) return;
    let value: unknown = null;
    try {
      if (checkpoint.trim()) value = JSON.parse(checkpoint);
    } catch {
      setError("체크포인트 JSON 문법을 확인하세요.");
      return;
    }
    // Null is reserved for the explicit empty input; do not silently skip comparison.
    if (
      checkpoint.trim() &&
      (!value || typeof value !== "object" || Array.isArray(value))
    ) {
      setError("체크포인트는 JSON 객체여야 합니다.");
      return;
    }
    if (value && !Number.isSafeInteger((value as Checkpoint).seq)) {
      setError(
        "seq는 브라우저가 정확히 표현할 수 있는 정수여야 합니다. 큰 번호는 CLI에서 비교하세요.",
      );
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await api<Result>(
        "/audit/verify",
        "POST",
        { checkpoint: value },
        controller.signal,
      );
      if (!controller.signal.aborted) setResult(response);
    } catch (e) {
      if (!controller.signal.aborted) setError((e as Error).message);
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
        request.current = null;
      }
    }
  }

  return (
    <section className="panel audit-panel" aria-label="감사 로그 연결 검증">
      <div className="panel-head">
        <h3>감사 로그 연결 검증</h3>
        <ShieldCheck size={20} aria-hidden="true" />
      </div>
      <div className="audit-body">
        <p>
          저장된 이벤트와 SHA-256 연결을 읽기 전용으로 검사합니다. 수동 실행이며
          검사 시점의 결과입니다.
        </p>
        <fieldset disabled={busy} className="policy-editor-controls">
          <label>
            독립 보관 체크포인트 JSON (선택)
            <textarea
              rows={4}
              value={checkpoint}
              maxLength={2048}
              placeholder="비우면 로컬 연결만 검사합니다."
              onChange={(event) => {
                setCheckpoint(event.target.value);
                setResult(null);
                setError("");
              }}
            />
          </label>
          <p className="subtle">
            CLI로 이전에 내보내 독립 보관한 format·chain_id·seq·hash 객체를 붙여
            넣으세요. 체크포인트의 보관 신뢰는 운영자가 확인해야 합니다.
          </p>
          <button type="button" onClick={() => void verify()} disabled={busy}>
            {busy ? "검증 중…" : "감사 연결 검증"}
          </button>
        </fieldset>
        {busy && (
          <p role="status">
            전체 연결을 검사 중입니다. 한 번에 1개, 기본 10초의 협력적 시간
            제한을 적용합니다.
          </p>
        )}
        {error && <p role="alert">{error} 입력을 확인하고 다시 시도하세요.</p>}
        {result && (
          <div aria-live="polite">
            {result.status === "verified" ? (
              <>
                <p role="status">
                  <strong>
                    {result.checkpoint_compared
                      ? "로컬 연결과 입력 체크포인트 일치"
                      : "로컬 연결 일치"}
                  </strong>
                </p>
                <dl className="runtime-policy">
                  <div className="setting-row">
                    <dt>검증 이벤트</dt>
                    <dd>{result.events}개</dd>
                  </div>
                  <div className="setting-row">
                    <dt>이전 기록 최초 봉인 기준</dt>
                    <dd>seq {result.sealed_legacy_until}</dd>
                  </div>
                </dl>
                <details className="form-details">
                  <summary>이번 검사 체크포인트</summary>
                  <pre className="audit-checkpoint">
                    {JSON.stringify(result.checkpoint, null, 2)}
                  </pre>
                  <p className="subtle">
                    이 출력은 서명되지 않았습니다. 파일 보존은
                    aegis-verify-audit --output으로 수행하고 독립 저장소에
                    보관하세요.
                  </p>
                </details>
              </>
            ) : (
              <p role="alert">
                <strong>
                  {result.status === "mismatch"
                    ? "연결 또는 체크포인트 불일치"
                    : "검증 미완료"}
                </strong>{" "}
                · {result.detail}
              </p>
            )}
            <p className="subtle">
              검사 시각:{" "}
              {new Date(result.checked_at * 1000).toLocaleString("ko-KR")}
            </p>
          </div>
        )}
        <p className="subtle">
          로컬 해시 일치만으로 DB 전체 재작성이나 기록 내용의 진위를 증명할 수
          없습니다. 최초 봉인 이전의 무결성도 증명하지 않습니다. 불일치 시
          원본을 보존하고 독립 체크포인트·백업과 비교하세요.
        </p>
      </div>
    </section>
  );
}
