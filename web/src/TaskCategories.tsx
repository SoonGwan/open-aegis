import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import Modal from "./components/Modal";
import { Pagination, RecordState, useRecords } from "./records";
import type { ListPosition, HistoryMode } from "./navigation-state";

export type Category = {
  id: string;
  name: string;
  revision: number;
  status: "active" | "archived";
};
type CategorizedTask = {
  id: string;
  name: string;
  category_ref?: Pick<Category, "id" | "name" | "revision"> | null;
  category_revision?: number;
};
const base = "/task-categories";
const changed = () => window.dispatchEvent(new Event("aegis-records-changed"));
const message = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "저장하지 못했습니다. 다시 시도하세요.";
function useMounted() {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return mounted;
}

function CategoryEditor({
  category,
  onClose,
}: {
  category?: Category;
  onClose: () => void;
}) {
  const [name, setName] = useState(category?.name || "");
  const [revision, setRevision] = useState(category?.revision || 0);
  const [latest, setLatest] = useState<Category | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const pending = useRef(false),
    mounted = useMounted();
  const retry = useRef<{ body: string; id: string } | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const body = JSON.stringify({ name: name.trim() });
      if (!retry.current || retry.current.body !== body)
        retry.current = { body, id: crypto.randomUUID() };
      await api(
        category ? `${base}/${category.id}` : base,
        category ? "PUT" : "POST",
        category
          ? { name: name.trim(), expected_revision: revision }
          : { name: name.trim(), request_id: retry.current.id },
      );
      if (mounted.current) {
        changed();
        onClose();
      }
    } catch (error) {
      if (mounted.current) setError(message(error));
      if (category)
        try {
          const record = await api<Category>(`${base}/${category.id}`);
          if (mounted.current && record.revision !== revision)
            setLatest(record);
        } catch {
          /* Keep the draft and original failure. */
        }
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={category ? "작업 분류 수정" : "작업 분류 만들기"}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <form onSubmit={submit}>
        <label>
          분류 이름
          <input
            autoComplete="off"
            required
            maxLength={80}
            value={name}
            disabled={busy}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        {error && <p role="alert">{error}</p>}
        {latest && (
          <div className="panel">
            <p>
              현재 분류: {latest.name} · 버전 {latest.revision} ·{" "}
              {latest.status === "active" ? "활성" : "보관"}
            </p>
            <p>
              입력한 이름은 유지됩니다. 최신 버전을 확인하고 다시 저장하세요.
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setRevision(latest.revision);
                setLatest(null);
                setError("");
              }}
            >
              최신 버전으로 다시 검토
            </button>
          </div>
        )}
        <div className="modal-actions">
          <button type="button" disabled={busy} onClick={onClose}>
            취소
          </button>
          <button className="primary" disabled={busy || Boolean(latest)}>
            {busy ? "저장 중…" : "저장"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CategoryArchive({
  category,
  onClose,
}: {
  category: Category;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const pending = useRef(false),
    mounted = useMounted();
  const archived = category.status === "active";
  async function submit() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await api(`${base}/${category.id}/archive`, "POST", {
        expected_revision: category.revision,
        archived,
      });
      if (mounted.current) {
        changed();
        onClose();
      }
    } catch (error) {
      if (mounted.current)
        setError(message(error) + " 창을 닫고 현재 버전을 다시 확인하세요.");
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title={archived ? "작업 분류 보관" : "작업 분류 복원"}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <p>
        {category.name} · 버전 {category.revision}
      </p>
      <p>
        {archived
          ? "기존 작업의 분류와 변경 이력은 유지됩니다. 보관된 분류는 새 작업에 지정할 수 없습니다."
          : "활성 분류로 복원합니다. 같은 이름의 활성 분류가 있으면 이름을 먼저 수정하세요."}
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="modal-actions">
        <button disabled={busy} onClick={onClose}>
          취소
        </button>
        <button
          className="primary"
          disabled={busy}
          onClick={() => void submit()}
        >
          {busy ? "처리 중…" : archived ? "보관" : "복원"}
        </button>
      </div>
    </Modal>
  );
}

function History({
  id,
  name,
  task,
  onClose,
}: {
  id: string;
  name: string;
  task?: boolean;
  onClose: () => void;
}) {
  type Entry = {
    id: string;
    revision: number;
    action: string;
    snapshot?: Category;
    before?: Category | null;
    after?: Category | null;
    actor: { name: string };
    created_at: number;
  };
  const records = useRecords<Entry>(
    "category-history",
    "",
    {},
    undefined,
    task ? `/tasks/${id}/category-history` : `${base}/${id}/history`,
    false,
  );
  return (
    <Modal title={`${name} 분류 이력`} onClose={onClose}>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          <ul>
            {records.items.map((row) => (
              <li key={row.id}>
                <strong>버전 {row.revision}</strong> ·{" "}
                {task
                  ? `${row.before?.name || "미분류"} → ${row.after?.name || "미분류"}`
                  : `${row.action} · ${row.snapshot?.name}`}{" "}
                · {row.actor.name}
                <small>
                  {new Date(row.created_at * 1000).toLocaleString()}
                </small>
              </li>
            ))}
          </ul>
          {records.total === 0 && <p>분류 변경 이력이 없습니다.</p>}
          <Pagination records={records} />
        </>
      )}
    </Modal>
  );
}

function AssignmentPicker({
  selected,
  onClose,
  onSaved,
}: {
  selected: CategorizedTask[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [search, setSearch] = useState("");
  const categories = useRecords<Category>(
    "task-categories",
    search,
    { status: "active" },
    undefined,
    base,
  );
  const [chosen, setChosen] = useState<Category | null | undefined>(undefined);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const pending = useRef(false),
    mounted = useMounted();
  const retry = useRef<{ body: string; id: string } | null>(null);
  async function submit() {
    if (pending.current || chosen === undefined) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const body = {
      task_ids: selected.map((t) => t.id),
      category_id: chosen?.id || null,
      expected_revisions: Object.fromEntries(
        selected.map((t) => [t.id, t.category_revision || 0]),
      ),
    };
    const serialized = JSON.stringify(body);
    if (!retry.current || retry.current.body !== serialized)
      retry.current = { body: serialized, id: crypto.randomUUID() };
    try {
      await api("/tasks/category-assignment", "POST", {
        ...body,
        request_id: retry.current.id,
      });
      if (mounted.current) {
        changed();
        onSaved();
        onClose();
      }
    } catch (error) {
      if (mounted.current) setError(message(error));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <Modal
      title="선택한 작업 분류 변경"
      subtitle={`${selected.length}개 작업 · 실행 승인과 상태는 유지됩니다.`}
      onClose={() => {
        if (!pending.current) onClose();
      }}
    >
      <details>
        <summary>선택한 작업 확인</summary>
        <ul>
          {selected.map((task) => (
            <li key={task.id}>
              {task.name} · {task.category_ref?.name || "미분류"} · 변경 버전{" "}
              {task.category_revision || 0}
            </li>
          ))}
        </ul>
      </details>
      <label>
        활성 분류 검색
        <input
          maxLength={200}
          value={search}
          disabled={busy}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <button
        disabled={busy}
        aria-pressed={chosen === null}
        onClick={() => setChosen(null)}
      >
        미분류로 변경
      </button>
      {(!categories.ready || categories.error) && (
        <RecordState records={categories} />
      )}
      {categories.ready && (
        <>
          <ul className="category-options">
            {categories.items.map((category) => (
              <li key={category.id}>
                <button
                  disabled={busy}
                  aria-pressed={chosen?.id === category.id}
                  onClick={() => setChosen(category)}
                >
                  {category.name}
                </button>
              </li>
            ))}
          </ul>
          <Pagination records={categories} />
        </>
      )}
      <p>
        변경할 분류:{" "}
        <strong>
          {chosen === undefined
            ? "선택하세요"
            : chosen === null
              ? "미분류"
              : chosen.name}
        </strong>
      </p>
      {error && (
        <p role="alert">
          {error} 다른 사람이 분류를 변경했다면 이 창을 닫고 선택을 새로 고친 뒤
          다시 확인하세요.
        </p>
      )}
      <div className="modal-actions">
        <button disabled={busy} onClick={onClose}>
          취소
        </button>
        <button
          className="primary"
          disabled={busy || chosen === undefined}
          onClick={() => void submit()}
        >
          {busy ? "변경 중…" : "분류 변경"}
        </button>
      </div>
    </Modal>
  );
}

function Memberships({
  category,
  canOperate,
  onTask,
  onClose,
}: {
  category: Category | null;
  canOperate: boolean;
  onTask: (id: string) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const records = useRecords<CategorizedTask>(
    "tasks",
    search,
    category ? { category_id: category.id } : {},
  );
  const [selected, setSelected] = useState<Record<string, CategorizedTask>>({});
  const [assign, setAssign] = useState(false),
    [history, setHistory] = useState<CategorizedTask | null>(null);
  // Selection retains the revision actually reviewed. Polling must not silently adopt somebody else's change.
  const picked = Object.values(selected);
  if (assign)
    return (
      <AssignmentPicker
        selected={picked}
        onClose={() => setAssign(false)}
        onSaved={() => setSelected({})}
      />
    );
  if (history)
    return (
      <History
        id={history.id}
        name={history.name}
        task
        onClose={() => setHistory(null)}
      />
    );
  return (
    <Modal
      title={category ? `${category.name}의 작업` : "작업 분류 일괄 변경"}
      onClose={onClose}
    >
      <label>
        작업 이름 검색
        <input
          value={search}
          maxLength={200}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <p>
        {records.total}개 작업 · 선택 {picked.length}/25
      </p>
      {canOperate && (
        <div className="category-actions">
          <button disabled={!picked.length} onClick={() => setAssign(true)}>
            선택한 작업 분류 변경
          </button>
          <button disabled={!picked.length} onClick={() => setSelected({})}>
            선택 해제
          </button>
        </div>
      )}
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready && (
        <>
          <ul className="category-members">
            {records.items.map((task) => (
              <li key={task.id}>
                {canOperate && (
                  <input
                    type="checkbox"
                    aria-label={`${task.name} 선택`}
                    checked={Boolean(selected[task.id])}
                    disabled={!selected[task.id] && picked.length >= 25}
                    onChange={(e) =>
                      setSelected((before) => {
                        const next = { ...before };
                        if (e.target.checked) next[task.id] = task;
                        else delete next[task.id];
                        return next;
                      })
                    }
                  />
                )}
                <button
                  className="table-link"
                  onClick={() => {
                    onClose();
                    onTask(task.id);
                  }}
                >
                  {task.name}
                </button>
                <span>{task.category_ref?.name || "미분류"}</span>
                <button onClick={() => setHistory(task)}>변경 이력</button>
              </li>
            ))}
          </ul>
          {records.total === 0 && <p>일치하는 작업이 없습니다.</p>}
          <Pagination records={records} />
        </>
      )}
    </Modal>
  );
}

export function TaskCategories({
  canOperate,
  search,
  onSearch,
  status,
  onStatus,
  position,
  onPositionChange,
  onTask,
}: {
  canOperate: boolean;
  search: string;
  onSearch: (value: string) => void;
  status: string;
  onStatus: (value: string) => void;
  position: ListPosition;
  onPositionChange: (value: ListPosition, mode?: HistoryMode) => void;
  onTask: (id: string) => void;
}) {
  const records = useRecords<Category>(
    "task-categories",
    search,
    { status },
    { ...position, onPositionChange },
    base,
  );
  const [editor, setEditor] = useState<Category | null | undefined>(undefined);
  const [archive, setArchive] = useState<Category | null>(null),
    [history, setHistory] = useState<Category | null>(null);
  const [members, setMembers] = useState<Category | null | undefined>(
    undefined,
  );
  return (
    <>
      <div className="toolbar category-toolbar">
        <label>
          분류 검색
          <input
            maxLength={200}
            value={search}
            onChange={(e) => onSearch(e.target.value)}
          />
        </label>
        <select
          aria-label="분류 상태"
          value={status}
          onChange={(e) => onStatus(e.target.value)}
        >
          <option value="active">활성 분류</option>
          <option value="archived">보관된 분류</option>
          <option value="all">모든 분류</option>
        </select>
        {canOperate && (
          <button className="primary" onClick={() => setEditor(null)}>
            분류 만들기
          </button>
        )}
        <button onClick={() => setMembers(null)}>
          {canOperate ? "작업 분류 일괄 변경" : "작업 분류 보기"}
        </button>
      </div>
      <section className="panel category-panel">
        <p>
          분류 {records.total}개 · 분류는 작업을 정리하는 용도입니다. 실행
          범위와 승인에는 영향을 주지 않습니다.
        </p>
        {(!records.ready || records.error) && <RecordState records={records} />}
        {records.ready && (
          <>
            <div className="template-cards">
              {records.items.map((category) => (
                <article className="template-card" key={category.id}>
                  <h3>{category.name}</h3>
                  <p>
                    버전 {category.revision} ·{" "}
                    {category.status === "active" ? "활성" : "보관"}
                  </p>
                  <div className="category-actions">
                    <button onClick={() => setMembers(category)}>
                      작업 보기
                    </button>
                    <button onClick={() => setHistory(category)}>
                      분류 이력
                    </button>
                    {canOperate && (
                      <>
                        <button onClick={() => setEditor(category)}>
                          수정
                        </button>
                        <button onClick={() => setArchive(category)}>
                          {category.status === "active" ? "보관" : "복원"}
                        </button>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
            {records.total === 0 && <p>일치하는 분류가 없습니다.</p>}
            <Pagination records={records} />
          </>
        )}
      </section>
      {editor !== undefined && (
        <CategoryEditor
          category={editor || undefined}
          onClose={() => setEditor(undefined)}
        />
      )}
      {archive && (
        <CategoryArchive category={archive} onClose={() => setArchive(null)} />
      )}
      {history && (
        <History
          id={history.id}
          name={history.name}
          onClose={() => setHistory(null)}
        />
      )}
      {members !== undefined && (
        <Memberships
          category={members}
          canOperate={canOperate}
          onTask={onTask}
          onClose={() => setMembers(undefined)}
        />
      )}
    </>
  );
}
