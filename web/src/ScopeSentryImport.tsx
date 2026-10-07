import { t as uiText, localizeLabels, getFormatLocale } from "./i18n-core.ts";
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
  remote?: { connection_id?: string; page?: number; has_more?: boolean };
};
type Connection = {
  id: string;
  url: string;
  project: string;
  configured: boolean;
};
type Applied = {
  created: number;
  linked: number;
  seen: number;
  source_changed: number;
  items: { asset_id: string; external_id: string; url: string }[];
};
const actions: Record<string, string> = localizeLabels({
  create: "새 자산 등록",
  link: "기존 자산에 출처 연결",
  seen: "기존 출처 확인",
});

export function ScopeSentryImport({
  onClose,
  onApplied,
}: {
  onClose: () => void;
  onApplied: () => void;
}) {
  const [mode, setMode] = useState<"file" | "remote">("file");
  const [connections, setConnections] = useState<Connection[]>([]);
  const [connection, setConnection] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [connectionsLoading, setConnectionsLoading] = useState(true);
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
  const listingController = useRef<AbortController | null>(null);
  async function loadConnections() {
    listingController.current?.abort();
    const listing = new AbortController();
    listingController.current = listing;
    setConnectionsLoading(true);
    setConnectionError("");
    try {
      const items = await api<Connection[]>(
        "/integrations/scopesentry/connections",
        "GET",
        undefined,
        listing.signal,
      );
      if (
        active.current &&
        listingController.current === listing &&
        !listing.signal.aborted
      ) {
        setConnections(items);
        setConnection((current) =>
          items.some((item) => item.id === current && item.configured)
            ? current
            : "",
        );
      }
    } catch (e) {
      if (
        active.current &&
        listingController.current === listing &&
        !listing.signal.aborted
      )
        setConnectionError((e as Error).message);
    } finally {
      if (
        active.current &&
        listingController.current === listing &&
        !listing.signal.aborted
      )
        setConnectionsLoading(false);
    }
  }
  useEffect(() => {
    active.current = true;
    void loadConnections();
    return () => {
      active.current = false;
      listingController.current?.abort();
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
  async function preview(e?: React.FormEvent, previous?: string) {
    e?.preventDefault();
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    controller.current = new AbortController();
    try {
      const next = await api<Preview>(
        mode === "remote"
          ? "/integrations/scopesentry/remote/preview"
          : "/integrations/scopesentry/preview",
        "POST",
        mode === "remote"
          ? {
              connection_id: connection,
              ...(previous ? { previous_preview_id: previous } : {}),
            }
          : { source_key: source, export: text },
        controller.current.signal,
      );
      if (active.current) {
        reset();
        setPlan(next);
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
      title={uiText("ScopeSentry 자산 가져오기")}
      subtitle={uiText("원본 검토 → 항목 선택 → 출처와 자산 반영")}
      onClose={onClose}
    >
      <div className="modal-actions" aria-label={uiText("원본 가져오기 방식")}>
        <button
          disabled={busy || submitted}
          aria-pressed={mode === "file"}
          onClick={() => {
            reset();
            setMode("file");
          }}
        >
          {uiText("파일 가져오기")}</button>
        <button
          disabled={busy || submitted}
          aria-pressed={mode === "remote"}
          onClick={() => {
            reset();
            setMode("remote");
          }}
        >
          {uiText("원격 원본 조회")}</button>
      </div>
      {mode === "remote" && (
        <section className="scopesentry-preview" aria-label={uiText("원격 원본 연결")}>
          <p className="remediation">
            {uiText("관리자가 등록한 원본에서 한 번에 최대 50개를 조회합니다. 항목 반영은 직접 선택하며 검증 작업 실행에는 별도 승인이 필요합니다.")}</p>
          {connectionsLoading && (
            <p role="status">{uiText("원격 연결 목록을 불러오는 중…")}</p>
          )}
          {connectionError && (
            <p role="alert" className="form-error">
              {uiText("연결 목록 조회 실패: ")}{connectionError}
            </p>
          )}
          {!connectionsLoading && !connectionError && !connections.length && (
            <p>
              {uiText("등록된 원격 원본이 없습니다. 관리자가 서버 연결과 인증을 설정하거나 파일 가져오기를 사용하세요.")}</p>
          )}
          <button
            disabled={connectionsLoading || busy || submitted}
            onClick={() => void loadConnections()}
          >
            {connectionError ? uiText("연결 목록 다시 시도") : uiText("연결 목록 새로고침")}
          </button>
          {connections.map((item) => (
            <label
              className="checkbox-label scopesentry-connection"
              key={item.id}
            >
              <input
                type="radio"
                name="scopesentry-connection"
                checked={connection === item.id}
                disabled={
                  connectionsLoading ||
                  !!connectionError ||
                  busy ||
                  submitted ||
                  !item.configured
                }
                onChange={() => {
                  reset();
                  setConnection(item.id);
                }}
              />
              <span>
                {item.id} · {item.url}
                {item.project ? ` · ${item.project}` : ""}
                {!item.configured ? uiText(" · 서버 인증 설정 필요") : ""}
              </span>
            </label>
          ))}
          {!plan && (
            <button
              disabled={
                connectionsLoading || !!connectionError || busy || !connection
              }
              onClick={() => void preview()}
            >
              {busy ? uiText("원본 조회 중…") : uiText("첫 페이지 조회")}
            </button>
          )}
        </section>
      )}
      {mode === "file" && (
        <>
          <p className="remediation">
            {uiText("ScopeSentry의 asset JSON 내보내기 파일을 붙여 넣으세요. 한 줄에 레코드 하나이며 최대 100줄·1 MiB입니다. 파일에 없는 항목은 삭제하지 않습니다. 가져온 후에도 검증 작업은 별도로 승인해야 합니다.")}</p>
          <form onSubmit={preview}>
            <fieldset
              disabled={busy || submitted}
              className="identity-form-fields"
              aria-label={uiText("ScopeSentry 가져오기 입력")}
            >
              <label>
                {uiText("원본 인스턴스 식별자")}<input
                  value={source}
                  maxLength={64}
                  pattern="[A-Za-z0-9_.-]+"
                  required
                  placeholder={uiText("예: company-sentry")}
                  onChange={(e) => {
                    reset();
                    setSource(e.target.value);
                  }}
                />
              </label>
              <label>
                {uiText("내보낸 자산 JSON")}<textarea
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
                {uiText("같은 ScopeSentry 인스턴스는 항상 같은 식별자를 사용하세요. HTTP 자산의 _id·type·url을 읽습니다. 본문·헤더·스크린샷과 외부 접근 규칙은 저장하지 않습니다.")}</p>
            </fieldset>
            {!submitted && (
              <button type="submit" disabled={busy}>
                {busy ? uiText("미리보는 중…") : uiText("가져오기 미리보기")}
              </button>
            )}
          </form>
        </>
      )}
      {plan?.remote?.page && (
        <p role="status">
          {uiText("원본 ")}{plan.source_key} · {plan.remote.page}{uiText("페이지 · ")}{plan.rows.length}
          {uiText("개")}</p>
      )}
      {plan && !result && (
        <section className="scopesentry-preview" aria-label={uiText("가져오기 검토")}>
          <p>
            <strong>
              {uiText("전체 ")}{plan.rows.length}{uiText("개 · 가져올 수 있는 항목 ")}{ready.length}{uiText("개")}</strong>
          </p>
          <p className="subtle">
            {uiText("이 검토는")}{" "}
            {new Date(plan.expires_at * 1000).toLocaleTimeString(getFormatLocale())}{uiText("에 만료됩니다. 기존 자산의 로컬 설정은 유지합니다. 주소 변경 항목은 새 주소의 자산에 연결하며 이전 이력은 보존합니다.")}</p>
          <button
            disabled={busy || submitted || !ready.length}
            onClick={() => setSelected(ready.map((row) => row.external_id!))}
          >
            {uiText("가져올 수 있는 항목 모두 선택")}</button>
          <div
            className="scopesentry-rows"
            tabIndex={0}
            role="region"
            aria-label={uiText("가져올 원본 항목")}
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
                  <strong>{row.url || uiText("레코드 {0}", [row.line])}</strong>
                  <small>
                    {row.external_id || uiText("원본 ID 없음")} ·{" "}
                    {row.reason || actions[row.action || ""]}
                  </small>
                  {row.source_changed && (
                    <small>{uiText("원본 주소 변경 · 이전 주소 ")}{row.previous_url}</small>
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
            {uiText("선택한 주소에 대한 검증 권한을 확인했습니다.")}</label>
          <p className="subtle">
            {uiText("선택한 ")}{selected.length}{uiText("개만 반영합니다. 응답을 확인하지 못하면 같은 선택으로 다시 확인하세요.")}</p>
          <div className="modal-actions">
            <button disabled={busy} onClick={reset}>
              {uiText("미리보기 다시 만들기")}</button>
            <button
              className="primary"
              disabled={busy || !authorized || !selected.length}
              onClick={() => void apply()}
            >
              {busy
                ? uiText("반영 중…")
                : submitted
                  ? uiText("같은 선택으로 다시 확인")
                  : uiText("선택한 항목 반영")}
            </button>
          </div>
        </section>
      )}
      {result && (
        <section
          className="scopesentry-preview"
          aria-label={uiText("가져오기 반영 결과")}
        >
          <p role="status">
            {uiText("새 자산 ")}{result.created}{uiText("개 · 새 출처 연결 ")}{result.linked}{uiText("개 · 기존 출처 확인 ")}{result.seen}{uiText("개 · 주소 변경 ")}{result.source_changed}{uiText("개")}</p>
          <p>
            {uiText("검증 작업을 자동 생성하거나 실행하지 않았습니다. 자산의 ‘출처’에서 연결 정보를 확인하세요.")}</p>
          <ul>
            {result.items.map((item) => (
              <li key={item.external_id}>
                <code>{item.url}</code>
              </li>
            ))}
          </ul>
          <button onClick={onClose}>{uiText("닫기")}</button>
        </section>
      )}
      {plan?.remote?.page && (
        <section
          className="scopesentry-preview"
          aria-label={uiText("원본 페이지 이어받기")}
        >
          <p className="subtle">
            {uiText("원본 목록은 조회 중 바뀔 수 있습니다. 이전 페이지 변경이나 중복 ID가 발견되면 처음부터 다시 조회하세요. 누락된 항목을 자동 삭제하지 않습니다.")}</p>
          {plan.remote.has_more && plan.remote.page < 20 ? (
            <button
              disabled={
                connectionsLoading ||
                !!connectionError ||
                !connection ||
                busy ||
                (submitted && !result)
              }
              onClick={() => void preview(undefined, plan.id)}
            >
              {busy
                ? uiText("원본 조회 중…")
                : result
                  ? uiText("다음 원본 페이지 조회")
                  : uiText("이 페이지 반영 없이 다음 조회")}
            </button>
          ) : (
            <p>
              {plan.remote.has_more
                ? uiText("20페이지 한도입니다. 관리자에게 원본 필터 설정을 확인하세요.")
                : uiText("이 수집의 마지막 페이지입니다.")}
            </p>
          )}
          <button
            disabled={
              connectionsLoading ||
              !!connectionError ||
              !connection ||
              busy ||
              (submitted && !result)
            }
            onClick={() => void preview()}
          >
            {uiText("원본 처음부터 다시 조회")}</button>
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
    <Modal title={uiText("자산의 원본 출처")} subtitle={asset.name} onClose={onClose}>
      <div className="scopesentry-sources">
        <p>
          {uiText("ScopeSentry 파일에서 명시적으로 반영한 원본 연결입니다. 원본의 삭제나 주소 변경이 검증 증거를 삭제하지 않습니다.")}</p>
        <label>
          {uiText("출처 검색")}<input
            value={search}
            maxLength={200}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={uiText("인스턴스·원본 ID·주소")}
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={history}
            onChange={(e) => setHistory(e.target.checked)}
          />
          {uiText("이전 연결 이력 보기")}</label>
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
                {uiText("최초 확인")}{" "}
                {new Date(source.first_seen * 1000).toLocaleString(getFormatLocale())} {uiText(" · 최근 확인")}{" "}
                {new Date(source.last_seen * 1000).toLocaleString(getFormatLocale())}
              </p>
              {source.replaced_at && (
                <p>
                  {uiText("연결 변경")}{" "}
                  {new Date(source.replaced_at * 1000).toLocaleString(getFormatLocale())}
                </p>
              )}
              <details>
                <summary>{uiText("내보내기 파일의 SHA-256")}</summary>
                <code>{source.export_sha256}</code>
              </details>
            </article>
          ))
        ) : (
          <p>{uiText("표시할 출처가 없습니다.")}</p>
        )}
      </div>
    </Modal>
  );
}
