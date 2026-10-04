import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import Modal from "./components/Modal";
import { useRecords, RecordState, Pagination } from "./records";

type PreviewRow = {
  line: number;
  external_id: string | null;
  url: string | null;
  status: string;
  action?: string;
  reason: string;
  source_changed?: boolean;
  previous_url?: string | null;
};
type Preview = {
  id: string;
  source_key: string;
  export_sha256: string;
  expires_at: number;
  rows: PreviewRow[];
};
type Applied = {
  created: number;
  linked: number;
  seen: number;
  source_changed: number;
  items: { asset_id: string; external_id: string; url: string }[];
};
const actions: Record<string, string> = {
  create: "새 자산 등록",
  link: "기존 자산에 출처 연결",
  seen: "기존 출처 확인",
};

export function ScopeSentryImport({
  onClose,
  onApplied,
}: {
  onClose: () => void;
  onApplied: () => void;
}) {
  const [source, setSource] = useState("");
  const [text, setText] = useState("");
  const [plan, setPlan] = useState<Preview | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<Applied | null>(null);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const active = useRef(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  function reset() {
    setPlan(null);
    setSelected([]);
    setAuthorized(false);
    setSubmitted(false);
    setResult(null);
    setError("");
  }
  async function preview(e: React.FormEvent) {
    e.preventDefault();
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    controller.current = new AbortController();
    try {
      const next = await api<Preview>(
        "/integrations/scopesentry/preview",
        "POST",
        { source_key: source, export: text },
        controller.current.signal,
      );
      if (active.current) {
        setPlan(next);
        setSelected([]);
      }
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      inFlight.current = false;
      if (active.current) setBusy(false);
    }
  }
  async function apply() {
    if (inFlight.current || !plan) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setSubmitted(true);
    try {
      const applied = await api<Applied>(
        `/integrations/scopesentry/${plan.id}/apply`,
        "POST",
        { selected, authorized },
      );
      // Reconcile a committed result even if the user closed this modal.
      onApplied();
      if (active.current) setResult(applied);
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      inFlight.current = false;
      if (active.current) setBusy(false);
    }
  }
  const ready =
    plan?.rows.filter((row) => row.status === "ready" && row.external_id) || [];
  return (
    <Modal
      title="ScopeSentry 자산 가져오기"
      subtitle="파일 검토 → 항목 선택 → 출처와 자산 반영"
      onClose={onClose}
    >
      <p className="remediation">
        ScopeSentry의 asset JSON 내보내기 파일을 붙여 넣으세요. 한 줄에 레코드
        하나이며 최대 100줄·1 MiB입니다. 파일에 없는 항목은 삭제하지 않습니다.
        가져온 후에도 검증 작업은 별도로 승인해야 합니다.
      </p>
      <form onSubmit={preview}>
        <fieldset
          disabled={busy || submitted}
          className="identity-form-fields"
          aria-label="ScopeSentry 가져오기 입력"
        >
          <label>
            원본 인스턴스 식별자
            <input
              value={source}
              maxLength={64}
              pattern="[A-Za-z0-9_.-]+"
              required
              placeholder="예: company-sentry"
              onChange={(e) => {
                reset();
                setSource(e.target.value);
              }}
            />
          </label>
          <label>
            내보낸 자산 JSON
            <textarea
              value={text}
              rows={7}
              maxLength={1048576}
              required
              spellCheck={false}
              placeholder={
                '{"_id":"000000000000000000000001","type":"http","url":"https://owned.example/"}'
              }
              onChange={(e) => {
                reset();
                setText(e.target.value);
              }}
            />
          </label>
          <p className="subtle">
            같은 ScopeSentry 인스턴스는 항상 같은 식별자를 사용하세요. HTTP
            자산의 _id·type·url을 읽습니다. 본문·헤더·스크린샷과 외부 접근
            규칙은 저장하지 않습니다.
          </p>
        </fieldset>
        {!submitted && (
          <button type="submit" disabled={busy}>
            {busy ? "미리보는 중…" : "가져오기 미리보기"}
          </button>
        )}
      </form>
      {plan && !result && (
        <section className="scopesentry-preview" aria-label="가져오기 검토">
          <p>
            <strong>
              전체 {plan.rows.length}개 · 가져올 수 있는 항목 {ready.length}개
            </strong>
          </p>
          <p className="subtle">
            이 검토는{" "}
            {new Date(plan.expires_at * 1000).toLocaleTimeString("ko-KR")}에
            만료됩니다. 기존 자산의 로컬 설정은 유지합니다. 주소 변경 항목은 새
            주소의 자산에 연결하며 이전 이력은 보존합니다.
          </p>
          <button
            disabled={busy || submitted || !ready.length}
            onClick={() => setSelected(ready.map((row) => row.external_id!))}
          >
            가져올 수 있는 항목 모두 선택
          </button>
          <div
            className="scopesentry-rows"
            tabIndex={0}
            role="region"
            aria-label="가져올 원본 항목"
          >
            {plan.rows.map((row) => (
              <label className="scopesentry-row" key={row.line}>
                <input
                  type="checkbox"
                  disabled={busy || submitted || row.status !== "ready"}
                  checked={Boolean(
                    row.external_id && selected.includes(row.external_id),
                  )}
                  onChange={(e) =>
                    setSelected((previous) =>
                      e.target.checked
                        ? [...previous, row.external_id!]
                        : previous.filter((id) => id !== row.external_id),
                    )
                  }
                />
                <span>
                  <strong>{row.url || `레코드 ${row.line}`}</strong>
                  <small>
                    {row.external_id || "원본 ID 없음"} ·{" "}
                    {row.reason || actions[row.action || ""]}
                  </small>
                  {row.source_changed && (
                    <small>원본 주소 변경 · 이전 주소 {row.previous_url}</small>
                  )}
                </span>
              </label>
            ))}
          </div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={authorized}
              disabled={busy || submitted}
              onChange={(e) => setAuthorized(e.target.checked)}
            />
            선택한 주소에 대한 검증 권한을 확인했습니다.
          </label>
          <p className="subtle">
            선택한 {selected.length}개만 반영합니다. 응답을 확인하지 못하면 같은
            선택으로 다시 확인하세요.
          </p>
          <div className="modal-actions">
            <button disabled={busy} onClick={reset}>
              미리보기 다시 만들기
            </button>
            <button
              className="primary"
              disabled={busy || !authorized || !selected.length}
              onClick={() => void apply()}
            >
              {busy
                ? "반영 중…"
                : submitted
                  ? "같은 선택으로 다시 확인"
                  : "선택한 항목 반영"}
            </button>
          </div>
        </section>
      )}
      {result && (
        <section
          className="scopesentry-preview"
          aria-label="가져오기 반영 결과"
        >
          <p role="status">
            새 자산 {result.created}개 · 새 출처 연결 {result.linked}개 · 기존
            출처 확인 {result.seen}개 · 주소 변경 {result.source_changed}개
          </p>
          <p>
            검증 작업을 자동 생성하거나 실행하지 않았습니다. 자산의 ‘출처’에서
            연결 정보를 확인하세요.
          </p>
          <ul>
            {result.items.map((item) => (
              <li key={item.external_id}>
                <code>{item.url}</code>
              </li>
            ))}
          </ul>
          <button onClick={onClose}>닫기</button>
        </section>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}

type Source = {
  id: string;
  source_key: string;
  external_id: string;
  source_url: string;
  first_seen: number;
  last_seen: number;
  replaced_at?: number;
  export_sha256: string;
};
export function AssetSources({
  asset,
  onClose,
}: {
  asset: { id: string; name: string };
  onClose: () => void;
}) {
  const [history, setHistory] = useState(false);
  const [search, setSearch] = useState("");
  const records = useRecords<Source>(
    history ? "asset_source_history" : "asset_sources",
    search,
    history ? { history: "true" } : {},
    undefined,
    `/assets/${encodeURIComponent(asset.id)}/sources`,
  );
  return (
    <Modal title="자산의 원본 출처" subtitle={asset.name} onClose={onClose}>
      <div className="scopesentry-sources">
        <p>
          ScopeSentry 파일에서 명시적으로 반영한 원본 연결입니다. 원본의 삭제나
          주소 변경이 검증 증거를 삭제하지 않습니다.
        </p>
        <label>
          출처 검색
          <input
            value={search}
            maxLength={200}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="인스턴스·원본 ID·주소"
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={history}
            onChange={(e) => setHistory(e.target.checked)}
          />
          이전 연결 이력 보기
        </label>
        <Pagination records={records} />
        {!records.ready ? (
          <RecordState records={records} />
        ) : records.items.length ? (
          records.items.map((source) => (
            <article className="scopesentry-source" key={source.id}>
              <strong>{source.source_key}</strong>
              <code>{source.external_id}</code>
              <code>{source.source_url}</code>
              <p>
                최초 확인{" "}
                {new Date(source.first_seen * 1000).toLocaleString("ko-KR")} ·
                최근 확인{" "}
                {new Date(source.last_seen * 1000).toLocaleString("ko-KR")}
              </p>
              {source.replaced_at && (
                <p>
                  연결 변경{" "}
                  {new Date(source.replaced_at * 1000).toLocaleString("ko-KR")}
                </p>
              )}
              <details>
                <summary>내보내기 파일의 SHA-256</summary>
                <code>{source.export_sha256}</code>
              </details>
            </article>
          ))
        ) : (
          <p>표시할 출처가 없습니다.</p>
        )}
      </div>
    </Modal>
  );
}
