import { t as uiText } from "./i18n-core.ts";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import Modal from "./components/Modal";
import { AssetPicker, Pagination, RecordState, useRecords } from "./records";
import { RemoteExecutionPicker } from "./RemoteExecution";
import { validateWorkerDependencies } from "./worker-dependency-state";
import type { ListPosition, HistoryMode } from "./navigation-state";

type Definition = {
  name: string;
  goal: string;
  checks: string[];
  workers: number;
  planner: string;
  asset_ids: string[];
  worker_dependencies: Record<string, string[]>;
  remote_connection_id: string | null;
};
export type TemplateOrigin = {
  template_id: string;
  revision: number;
  fingerprint: string;
  name: string;
  category: string;
  definition: Definition;
};
type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  definition: Definition;
  revision: number;
  status: "active" | "archived";
  fingerprint: string;
};
type Tool = { id: string; name: string };
const base = "/task-templates";
const message = (error: unknown) =>
  error instanceof Error
    ? error.message
    : uiText("처리하지 못했습니다. 입력을 확인하고 다시 시도하세요.");
const changed = () => window.dispatchEvent(new Event("aegis-records-changed"));

function Fields({
  template,
  tools,
  apply,
}: {
  template?: Template;
  tools: Tool[];
  apply: boolean;
}) {
  const defaults = template?.definition;
  const [selected, setSelected] = useState(
    defaults?.checks || tools.map((tool) => tool.id),
  );
  const [remote, setRemote] = useState<string[] | null>(null);
  return (
    <>
      <label>
        {uiText("작업 이름")}<input
          name="task_name"
          required
          maxLength={120}
          defaultValue={defaults?.name || template?.name || uiText("정기 보안 검증")}
        />
      </label>
      <label>
        {uiText("검증 목표")}<textarea
          name="goal"
          maxLength={2000}
          rows={3}
          defaultValue={
            defaults?.goal ||
            uiText("등록된 자산의 보안 설정과 접근 권한을 검증합니다.")
          }
        />
      </label>
      {apply ? (
        <AssetPicker
          initialId={null}
          initialSelection={{
            selected: Object.fromEntries(
              (defaults?.asset_ids || []).map((id) => [
                id,
                { id, name: id, url: "" },
              ]),
            ),
            dependencies: defaults?.worker_dependencies || {},
          }}
        />
      ) : (
        <p className="subtle">
          {defaults?.asset_ids.length
            ? uiText("기본 자산 {0}개와 Worker 의존 관계를 유지합니다. 적용할 때 자산을 변경할 수 있습니다.", [defaults.asset_ids.length])
            : uiText("자산은 계획을 만들 때 선택합니다.")}
        </p>
      )}
      <RemoteExecutionPicker
        disabled={false}
        initialId={defaults?.remote_connection_id || ""}
        onChecks={setRemote}
        names={Object.fromEntries(tools.map((tool) => [tool.id, tool.name]))}
      />
      <fieldset>
        <legend>{uiText("검증 도구")}</legend>
        <div className="check-grid">
          {tools.map((tool) => (
            <label className="checkbox-label" key={tool.id}>
              <input
                type="checkbox"
                name="check"
                value={tool.id}
                disabled={!!remote && !remote.includes(tool.id)}
                checked={
                  selected.includes(tool.id) &&
                  (!remote || remote.includes(tool.id))
                }
                onChange={(event) =>
                  setSelected((rows) =>
                    event.target.checked
                      ? [...rows, tool.id]
                      : rows.filter((id) => id !== tool.id),
                  )
                }
              />
              {tool.name}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="form-grid">
        <label>
          {uiText("계획 방식")}<select name="planner" defaultValue={defaults?.planner || "rules"}>
            <option value="rules">{uiText("규칙 기반")}</option>
            <option value="ai">{uiText("AI 계획 (LLM 설정 필요)")}</option>
          </select>
        </label>
        <label>
          {uiText("병렬 Worker")}<select name="workers" defaultValue={defaults?.workers || 3}>
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {n}{uiText("개")}</option>
            ))}
          </select>
        </label>
      </div>
    </>
  );
}

function draft(
  form: HTMLFormElement,
  source?: Definition,
  apply = false,
): Definition {
  const data = new FormData(form);
  const asset_ids = apply
    ? data.getAll("asset").map(String)
    : source?.asset_ids || [];
  const worker_dependencies = apply
    ? JSON.parse(String(data.get("worker_dependencies") || "{}"))
    : source?.worker_dependencies || {};
  if (apply || asset_ids.length)
    validateWorkerDependencies(asset_ids, worker_dependencies);
  const checks = data.getAll("check").map(String);
  if (!checks.length) throw new Error(uiText("검증 도구를 한 개 이상 선택하세요."));
  if (apply && !asset_ids.length)
    throw new Error(uiText("현재 검증 자산을 선택하세요."));
  return {
    name: String(data.get("task_name") || ""),
    goal: String(data.get("goal") || ""),
    asset_ids,
    checks,
    workers: Number(data.get("workers")),
    planner: String(data.get("planner")),
    worker_dependencies,
    remote_connection_id:
      String(data.get("remote_connection_id") || "") || null,
  };
}

function TemplateForm({
  template,
  tools,
  apply,
  onClose,
  onSaved,
  onTask,
}: {
  template?: Template;
  tools: Tool[];
  apply: boolean;
  onClose: () => void;
  onSaved: () => void;
  onTask: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [latest, setLatest] = useState<Template | null>(null),
    [expected, setExpected] = useState(template?.revision || 1);
  const pending = useRef(false),
    mounted = useRef(true);
  const replay = useRef({ body: "", id: crypto.randomUUID() });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = event.currentTarget;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const data = new FormData(form),
        definition = draft(form, template?.definition, apply);
      const value = apply
        ? { expected_revision: expected, overrides: definition }
        : {
            name: String(data.get("name") || "").trim(),
            description: String(data.get("description") || ""),
            category: String(data.get("category") || ""),
            definition,
          };
      const encoded = JSON.stringify(value);
      if (replay.current.body !== encoded)
        replay.current = { body: encoded, id: crypto.randomUUID() };
      if (apply && template) {
        const task = await api<{ id: string }>(
          `${base}/${template.id}/apply`,
          "POST",
          { ...value, request_id: replay.current.id },
        );
        changed();
        if (mounted.current) {
          onClose();
          onTask(task.id);
        }
      } else if (template) {
        await api(`${base}/${template.id}`, "PUT", {
          ...value,
          expected_revision: expected,
        });
        changed();
        if (mounted.current) onSaved();
      } else {
        await api(base, "POST", { ...value, request_id: replay.current.id });
        changed();
        if (mounted.current) onSaved();
      }
    } catch (cause) {
      if (mounted.current) setError(message(cause));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function current() {
    if (!template || pending.current) return;
    pending.current = true;
    setBusy(true);
    try {
      const row = await api<Template>(`${base}/${template.id}`);
      if (mounted.current) setLatest(row);
    } catch (cause) {
      if (mounted.current) setError(message(cause));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={
        apply
          ? uiText("템플릿으로 검증 계획 만들기")
          : template
            ? uiText("작업 템플릿 수정")
            : uiText("작업 템플릿 만들기")
      }
      subtitle={uiText("설정을 저장하고 반복 사용하세요. 적용한 계획은 관리자 실행 승인을 기다립니다.")}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      {template && (
        <p className="subtle">
          {template.name} {uiText(" · 검토 버전 ")}{expected} ·{" "}
          {template.status === "active" ? uiText("활성") : uiText("보관됨")}
        </p>
      )}
      <form onSubmit={submit} aria-busy={busy}>
        <fieldset disabled={busy} className="submission-fields">
          {!apply && (
            <>
              <label>
                {uiText("템플릿 이름")}<input
                  name="name"
                  required
                  maxLength={120}
                  defaultValue={template?.name}
                />
              </label>
              <label>
                {uiText("설명")}<textarea
                  name="description"
                  maxLength={2000}
                  rows={2}
                  defaultValue={template?.description}
                />
              </label>
              <label>
                {uiText("분류")}<input
                  name="category"
                  maxLength={80}
                  defaultValue={template?.category}
                  placeholder={uiText("예: 배포 전, 웹 서비스")}
                />
              </label>
            </>
          )}
          <Fields tools={tools} template={template} apply={apply} />
        </fieldset>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {template && error && (
          <button type="button" onClick={current} disabled={busy}>
            {uiText("현재 템플릿 확인")}</button>
        )}
        {latest && (
          <section className="template-conflict">
            <h4>
              {uiText("현재 버전 ")}{latest.revision} · {latest.name}
            </h4>
            <p>{latest.description}</p>
            <p>
              {uiText("분류 ")}{latest.category || uiText("미지정")} {uiText(" · 검사")}{" "}
              {latest.definition.checks.join(", ")} · Worker{" "}
              {latest.definition.workers}{uiText("개")}</p>
            <p className="subtle">
              {uiText("작성한 설정은 그대로 유지합니다. 현재 버전과 비교한 뒤 새 버전에 적용하세요.")}</p>
            <button
              type="button"
              disabled={busy || (latest.status !== "active" && apply)}
              onClick={() => {
                setExpected(latest.revision);
                setLatest(null);
                setError("");
              }}
            >
              {uiText("이 버전을 검토했고 작성한 설정 유지")}</button>
          </section>
        )}
        <div className="modal-actions">
          <button type="button" disabled={busy} onClick={onClose}>
            {uiText("취소")}</button>
          <button type="submit" className="primary" disabled={busy}>
            {busy
              ? uiText("저장 중…")
              : apply
                ? uiText("승인 대기 계획 만들기")
                : uiText("템플릿 저장")}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function TemplateHistory({
  template,
  onClose,
}: {
  template: Template;
  onClose: () => void;
}) {
  const records = useRecords<{
    id: string;
    revision: number;
    action: string;
    actor: { name: string };
    snapshot: Template;
  }>(
    "task_template_history",
    "",
    {},
    undefined,
    `${base}/${template.id}/history`,
    false,
  );
  return (
    <Modal title={uiText("{0} · 버전 이력", [template.name])} onClose={onClose}>
      {!records.ready ? (
        <RecordState records={records} />
      ) : (
        <>
          <Pagination records={records} />
          {records.items.map((row) => (
            <article key={row.id} className="template-history">
              <h4>
                {uiText("버전 ")}{row.revision} · {row.action}
              </h4>
              <p>
                {row.actor.name} · {row.snapshot.name} ·{" "}
                {row.snapshot.category || uiText("분류 미지정")}
              </p>
              <p>{row.snapshot.description}</p>
              <p className="subtle">
                {uiText("검사 ")}{row.snapshot.definition.checks.join(", ")} · Worker{" "}
                {row.snapshot.definition.workers}{uiText("개 ·")}{" "}
                {row.snapshot.status === "active" ? uiText("활성") : uiText("보관됨")}
              </p>
            </article>
          ))}
        </>
      )}
    </Modal>
  );
}

export function TemplateOriginSummary({ origin }: { origin?: TemplateOrigin }) {
  if (!origin) return null;
  return (
    <section className="remote-execution" aria-label={uiText("작업 템플릿 출처")}>
      <h4>{uiText("템플릿 · ")}{origin.name}</h4>
      <p>
        {uiText("버전 ")}{origin.revision} · {origin.category || uiText("분류 미지정")}
      </p>
      <p className="subtle">
        {uiText("이 계획을 만든 당시 설정을 기록했습니다. 이후 템플릿 편집은 기존 승인 계획에 반영되지 않습니다.")}</p>
    </section>
  );
}

export function TaskTemplates({
  tools,
  canOperate,
  search,
  onSearch,
  status,
  onStatus,
  position,
  onPositionChange,
  onTask,
}: {
  tools: Tool[];
  canOperate: boolean;
  search: string;
  onSearch: (value: string) => void;
  status: string;
  onStatus: (value: string) => void;
  position: ListPosition;
  onPositionChange: (value: ListPosition, mode?: HistoryMode) => void;
  onTask: (id: string) => void;
}) {
  const records = useRecords<Template>(
    "task_templates",
    search,
    {
      status: ["active", "archived", "all"].includes(status)
        ? status
        : "active",
    },
    { ...position, onPositionChange },
    base,
  );
  const [modal, setModal] = useState<{
    kind: "create" | "edit" | "apply" | "history";
    template?: Template;
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function archive(template: Template) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await api(`${base}/${template.id}/archive`, "POST", {
        expected_revision: template.revision,
        archived: template.status === "active",
      });
      changed();
    } catch (cause) {
      if (mounted.current) setError(message(cause));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <section className="panel" aria-label={uiText("작업 템플릿")}>
      <div className="panel-head">
        <div>
          <h2>{uiText("작업 템플릿")}</h2>
          <p className="subtle">
            {uiText("검사와 Worker 설정을 저장해 반복 사용합니다. 계획마다 현재 범위를 확인하고 실행을 승인하세요.")}</p>
        </div>
        <button
          className="primary"
          disabled={!canOperate || busy}
          onClick={() => setModal({ kind: "create" })}
        >
          {uiText("템플릿 만들기")}</button>
      </div>
      <div className="template-toolbar">
        <label>
          {uiText("템플릿 검색")}<input
            value={search}
            maxLength={200}
            onChange={(event) => onSearch(event.target.value)}
            placeholder={uiText("이름, 설명, 분류, 검증 목표")}
          />
        </label>
        <label>
          {uiText("보관 상태")}<select
            value={
              ["active", "archived", "all"].includes(status) ? status : "active"
            }
            onChange={(event) => onStatus(event.target.value)}
          >
            <option value="active">{uiText("활성 템플릿")}</option>
            <option value="archived">{uiText("보관된 템플릿")}</option>
            <option value="all">{uiText("전체")}</option>
          </select>
        </label>
      </div>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      {!records.ready ? (
        <RecordState records={records} />
      ) : (
        <>
          <Pagination records={records} />
          <div className="template-cards">
            {records.items.map((template) => (
              <article className="template-card" key={template.id}>
                <h3>{template.name}</h3>
                <p className="subtle">
                  {template.category || uiText("분류 미지정")} {uiText(" · 버전")}{" "}
                  {template.revision} ·{" "}
                  {template.status === "active" ? uiText("활성") : uiText("보관됨")}
                </p>
                <p>{template.description || uiText("설명 없음")}</p>
                <p>
                  {template.definition.checks
                    .map(
                      (id) => tools.find((tool) => tool.id === id)?.name || id,
                    )
                    .join(", ")}
                </p>
                <p className="subtle">
                  Worker {template.definition.workers}{uiText("개 ·")}{" "}
                  {template.definition.planner === "ai"
                    ? uiText("AI 계획")
                    : uiText("규칙 기반")}{" "}
                  · {template.definition.remote_connection_id || uiText("현재 서버")}
                </p>
                <div className="template-actions">
                  <button
                    disabled={
                      !canOperate || busy || template.status !== "active"
                    }
                    onClick={() => setModal({ kind: "apply", template })}
                  >
                    {uiText("계획 만들기")}</button>
                  <button
                    disabled={!canOperate || busy}
                    onClick={() => setModal({ kind: "edit", template })}
                  >
                    {uiText("수정")}</button>
                  <button
                    disabled={busy}
                    onClick={() => setModal({ kind: "history", template })}
                  >
                    {uiText("버전 이력")}</button>
                  <button
                    disabled={!canOperate || busy}
                    onClick={() => void archive(template)}
                  >
                    {template.status === "active" ? uiText("보관") : uiText("복원")}
                  </button>
                </div>
              </article>
            ))}
          </div>
          {!records.items.length && (
            <p className="empty">
              {search
                ? uiText("검색 결과가 없습니다.")
                : uiText("저장된 템플릿이 없습니다. 반복 사용할 검사 설정을 저장하세요.")}
            </p>
          )}
        </>
      )}
      {modal?.kind === "history" && modal.template ? (
        <TemplateHistory
          template={modal.template}
          onClose={() => setModal(null)}
        />
      ) : (
        modal && (
          <TemplateForm
            key={`${modal.kind}:${modal.template?.id || "new"}`}
            template={modal.template}
            apply={modal.kind === "apply"}
            tools={tools}
            onClose={() => setModal(null)}
            onSaved={() => {
              setModal(null);
              records.retry();
            }}
            onTask={onTask}
          />
        )
      )}
    </section>
  );
}
