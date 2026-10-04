import { useEffect, useRef, useState } from "react";
import { api, ApiError, captureSession } from "./api";
import { useRecords, Pagination, RecordState } from "./records";
import { pendingStorage } from "./chat-pending";
import {
  draftOf,
  changesOf,
  rebaseDraft,
  readTodoPending,
  writeTodoPending,
  clearTodoPending,
  type Todo,
  type TodoDraft,
  type TodoCreation,
  type TodoStatus,
} from "./todo-state";

const statuses: Record<TodoStatus, string> = {
  open: "미완료",
  in_progress: "진행 중",
  done: "완료",
  cancelled: "취소",
};
type Person = { id: string; name: string; username: string };
type History = {
  id: string;
  action: string;
  revision: number;
  created_at: number;
  reason: string;
  actor: { name: string };
  changes: Record<string, { before: unknown; after: unknown }>;
};
const labels: Record<string, string> = {
  title: "제목",
  description: "설명",
  status: "상태",
  assignee_id: "담당자 ID",
  assignee_name: "담당자",
  resolution_note: "완료·취소 사유",
};
function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "없음";
  return typeof value === "string"
    ? statuses[value as TodoStatus] || value
    : JSON.stringify(value);
}

function AssigneePicker({
  value,
  selected,
  disabled,
  onChange,
}: {
  value: string | null;
  selected: Person | null;
  disabled: boolean;
  onChange: (person: Person | null) => void;
}) {
  const [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0);
  const [page, setPage] = useState<{ items: Person[]; has_more: boolean }>({
    items: [],
    has_more: false,
  });
  const [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      api<typeof page>(
        `/assignees?${new URLSearchParams({ search, offset: String(offset), limit: "25" })}`,
        "GET",
        undefined,
        controller.signal,
      )
        .then((p) => {
          if (!controller.signal.aborted) setPage(p);
        })
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search, offset, reload]);
  const options =
    selected && !page.items.some((p) => p.id === selected.id)
      ? [selected, ...page.items]
      : page.items;
  return (
    <div className="todo-assignee">
      <label>
        담당자 검색
        <input
          aria-label="할 일 담당자 검색"
          value={search}
          maxLength={100}
          disabled={disabled}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </label>
      <label>
        담당자
        <select
          aria-label="할 일 담당자"
          value={value || ""}
          disabled={disabled || loading || !!error}
          onChange={(e) =>
            onChange(options.find((p) => p.id === e.target.value) || null)
          }
        >
          <option value="">미지정</option>
          {options.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} · {p.username}
            </option>
          ))}
        </select>
      </label>
      {loading && <p role="status">담당자 목록을 불러오는 중…</p>}
      {error && (
        <div role="alert">
          {error}{" "}
          <button
            type="button"
            disabled={disabled}
            onClick={() => setReload((n) => n + 1)}
          >
            담당자 목록 다시 불러오기
          </button>
        </div>
      )}
      <div className="pagination">
        <button
          type="button"
          disabled={disabled || loading || offset === 0}
          onClick={() => setOffset((n) => Math.max(0, n - 25))}
        >
          이전 담당자
        </button>
        <button
          type="button"
          disabled={disabled || loading || !!error || !page.has_more}
          onClick={() => setOffset((n) => n + 25)}
        >
          다음 담당자
        </button>
      </div>
    </div>
  );
}
function personOf(row: Todo): Person | null {
  return row.assignee_id
    ? {
        id: row.assignee_id,
        name: row.assignee_name || row.assignee_id,
        username: row.assignee_username || "",
      }
    : null;
}

function TodoEditor({
  row,
  taskId,
  captureView,
  onSaved,
  onClose,
}: {
  row: Todo;
  taskId: string;
  captureView: () => () => boolean;
  onSaved: (row: Todo) => void;
  onClose: () => void;
}) {
  const [base, setBase] = useState(row),
    [draft, setDraft] = useState<TodoDraft>(() => draftOf(row));
  const [person, setPerson] = useState(() => personOf(row));
  const [latest, setLatest] = useState<Todo | null>(null),
    [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const active = useRef(true),
    submitting = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (submitting.current) return;
    const changes = changesOf(draftOf(base), draft);
    if (!Object.keys(changes).length) {
      setError("변경한 내용이 없습니다.");
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    const current = captureView(),
      session = captureSession();
    try {
      const value = await api<Todo>(
        `/tasks/${taskId}/todos/${row.id}`,
        "PATCH",
        { expected_revision: base.revision, ...changes },
      );
      if (session()) {
        window.dispatchEvent(new Event("aegis-records-changed"));
        if (active.current && current()) {
          setBase(value);
          setDraft(draftOf(value));
          setPerson(personOf(value));
          setLatest(null);
          setConflict(false);
          onSaved(value);
        }
      }
    } catch (e) {
      if (session() && active.current && current()) {
        setError((e as Error).message);
        if (e instanceof ApiError && e.status === 409) {
          setConflict(true);
          setLatest(null);
        }
      }
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  async function compare() {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    const current = captureView(),
      session = captureSession();
    try {
      const value = await api<Todo>(`/tasks/${taskId}/todos/${row.id}`);
      if (session() && active.current && current()) setLatest(value);
    } catch (e) {
      if (session() && active.current && current())
        setError((e as Error).message);
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <form className="todo-form" onSubmit={save} aria-label="할 일 편집">
      <p>
        편집 기준 버전 {base.revision} · 목록이 갱신되어도 입력은 유지됩니다.
      </p>
      <label>
        제목
        <input
          aria-label="할 일 편집 제목"
          required
          maxLength={200}
          value={draft.title}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, title: e.target.value })}
        />
      </label>
      <label>
        설명
        <textarea
          aria-label="할 일 편집 설명"
          maxLength={4000}
          value={draft.description}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
        />
      </label>
      <AssigneePicker
        value={draft.assignee_id}
        selected={person}
        disabled={busy}
        onChange={(p) => {
          setPerson(p);
          setDraft({ ...draft, assignee_id: p?.id || null });
        }}
      />
      <label>
        상태
        <select
          aria-label="할 일 상태"
          value={draft.status}
          disabled={busy}
          onChange={(e) =>
            setDraft({
              ...draft,
              status: e.target.value as TodoStatus,
              resolution_note: "",
            })
          }
        >
          {Object.entries(statuses).map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        완료·취소 사유
        <textarea
          aria-label="할 일 완료·취소 사유"
          required={draft.status === "done" || draft.status === "cancelled"}
          maxLength={2000}
          value={draft.resolution_note}
          disabled={busy}
          onChange={(e) =>
            setDraft({ ...draft, resolution_note: e.target.value })
          }
        />
      </label>
      {error && <p role="alert">{error}</p>}
      {conflict && (
        <div className="todo-conflict">
          <p>
            내 입력은 유지했습니다. 최신 기록을 비교한 후 편집 기준을
            선택하세요.
          </p>
          <button type="button" disabled={busy} onClick={() => void compare()}>
            최신 기록 비교
          </button>
          {latest && (
            <>
              <h5>최신 기록 · 버전 {latest.revision}</h5>
              <dl>
                {Object.entries(draftOf(latest)).map(([k, v]) => (
                  <div key={k}>
                    <dt>{labels[k] || k}</dt>
                    <dd>
                      {k === "assignee_id"
                        ? latest.assignee_name || display(v)
                        : display(v)}
                    </dd>
                  </div>
                ))}
              </dl>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setDraft(rebaseDraft(draftOf(base), draft, latest));
                  if (draft.assignee_id === base.assignee_id)
                    setPerson(personOf(latest));
                  setBase(latest);
                  setLatest(null);
                  setConflict(false);
                }}
              >
                내 변경을 최신 기준으로 다시 준비
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setBase(latest);
                  setDraft(draftOf(latest));
                  setPerson(personOf(latest));
                  setLatest(null);
                  setConflict(false);
                }}
              >
                내 입력을 버리고 최신 내용으로 편집
              </button>
            </>
          )}
        </div>
      )}
      <div className="modal-actions">
        <button type="submit" disabled={busy || conflict}>
          {busy ? "저장 처리 중…" : "할 일 변경 저장"}
        </button>
        <button type="button" disabled={busy} onClick={onClose}>
          편집 닫기
        </button>
      </div>
    </form>
  );
}
function TodoHistory({ taskId, todoId }: { taskId: string; todoId: string }) {
  const [search, setSearch] = useState("");
  const records = useRecords<History>(
    "todo_history",
    search,
    {},
    undefined,
    `/tasks/${taskId}/todos/${todoId}/history`,
  );
  return (
    <section aria-label="할 일 변경 이력">
      <h5>변경 이력</h5>
      <label>
        이력 검색
        <input
          value={search}
          maxLength={200}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready &&
        records.items.map((h) => (
          <article key={h.id}>
            <p>
              {h.action === "created" ? "생성" : "변경"} · 버전 {h.revision} ·{" "}
              {h.actor.name} · {new Date(h.created_at * 1000).toLocaleString()}
            </p>
            <dl>
              {Object.entries(h.changes).map(([k, v]) => (
                <div key={k}>
                  <dt>{labels[k] || k}</dt>
                  <dd>
                    {display(v.before)} → {display(v.after)}
                  </dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      {records.ready && !records.error && !records.items.length && (
        <p>변경 이력이 없습니다.</p>
      )}
      <Pagination records={records} />
    </section>
  );
}
export function SharedTodos({
  taskId,
  actorId,
  canOperate,
  captureView,
}: {
  taskId: string;
  actorId: string;
  canOperate: boolean;
  captureView: () => () => boolean;
}) {
  const [search, setSearch] = useState(""),
    [selected, setSelected] = useState<Todo | null>(null),
    [editing, setEditing] = useState(false);
  const records = useRecords<Todo>(
    "todos",
    search,
    {},
    undefined,
    `/tasks/${taskId}/todos`,
  );
  const [pending, setPending] = useState<TodoCreation | null>(() =>
    readTodoPending(pendingStorage(), actorId, taskId),
  );
  const [title, setTitle] = useState(pending?.title || ""),
    [description, setDescription] = useState(pending?.description || "");
  const [person, setPerson] = useState<Person | null>(
    pending?.assignee_id
      ? { id: pending.assignee_id, name: pending.assignee_id, username: "" }
      : null,
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const active = useRef(true),
    submitting = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (submitting.current) return;
    const request = pending || {
      title: title.trim(),
      description: description.trim(),
      assignee_id: person?.id || null,
      request_id: Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
        b.toString(16).padStart(2, "0"),
      ).join(""),
    };
    if (!request.title) {
      setError("할 일 제목을 입력하세요.");
      return;
    }
    // Persist before dispatch: an unknown commit must be retried with exactly the same payload.
    if (!writeTodoPending(pendingStorage(), actorId, taskId, request)) {
      setError(
        "재시도 정보를 보관할 수 없어 전송하지 않았습니다. 브라우저 저장소 사용을 확인하세요.",
      );
      return;
    }
    setPending(request);
    submitting.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    const current = captureView(),
      session = captureSession();
    try {
      const row = await api<Todo>(`/tasks/${taskId}/todos`, "POST", request);
      // Matching request may be reconciled after navigation, but never after a session change.
      if (session()) {
        const cleared = clearTodoPending(
          pendingStorage(),
          actorId,
          taskId,
          request.request_id,
        );
        window.dispatchEvent(new Event("aegis-records-changed"));
        if (active.current && current()) {
          setPending(cleared ? null : request);
          setSelected(row);
          setEditing(false);
          if (cleared) {
            setTitle("");
            setDescription("");
            setPerson(null);
          }
          setNotice(
            cleared
              ? "할 일을 저장했습니다."
              : "저장은 확인했지만 재시도 정보 정리에 실패했습니다. 같은 요청을 다시 확인하세요.",
          );
        }
      }
    } catch (e) {
      if (session() && active.current && current()) {
        setError((e as Error).message);
        if (
          e instanceof ApiError &&
          e.status === 422 &&
          clearTodoPending(
            pendingStorage(),
            actorId,
            taskId,
            request.request_id,
          )
        )
          setPending(null);
      }
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <section className="shared-todos" aria-label="계획 회차 공유 할 일">
      <h4 className="detail-heading">공유 할 일</h4>
      <p>
        후속·재실행·교체 계획에서 함께 보는 검증 과제입니다. 완료 표시는 사람의
        조치 기록이며 실행 승인이나 검증 성공을 뜻하지 않습니다.
      </p>
      {canOperate && (
        <form className="todo-form" onSubmit={create} aria-label="새 할 일">
          <label>
            제목
            <input
              aria-label="새 할 일 제목"
              required
              maxLength={200}
              value={title}
              disabled={busy || !!pending}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            설명
            <textarea
              aria-label="새 할 일 설명"
              maxLength={4000}
              value={description}
              disabled={busy || !!pending}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <AssigneePicker
            value={person?.id || null}
            selected={person}
            disabled={busy || !!pending}
            onChange={setPerson}
          />
          {pending && (
            <p role="status">
              저장 응답 확인이 필요합니다. 내용을 유지한 채 같은 요청을 다시
              보내 중복 생성을 방지합니다.
            </p>
          )}
          {error && <p role="alert">{error}</p>}
          {notice && <p role="status">{notice}</p>}
          <button type="submit" disabled={busy}>
            {busy
              ? "저장 확인 중…"
              : pending
                ? "같은 할 일 저장 다시 확인"
                : "할 일 추가"}
          </button>
        </form>
      )}
      <label>
        할 일 검색
        <input
          aria-label="공유 할 일 검색"
          value={search}
          maxLength={200}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {(!records.ready || records.error) && <RecordState records={records} />}
      {records.ready &&
        records.items.map((row) => (
          <article className="todo-row" key={row.id}>
            <button
              type="button"
              onClick={() => {
                setSelected(row);
                setEditing(false);
              }}
            >
              {row.title}
            </button>
            <span>
              {statuses[row.status]} · {row.assignee_name || "미지정"} · 버전{" "}
              {row.revision}
            </span>
          </article>
        ))}
      {records.ready && !records.error && !records.items.length && (
        <p>공유 할 일이 없습니다.</p>
      )}
      <Pagination records={records} />
      {selected && (
        <section className="todo-detail" aria-label="선택한 할 일">
          <h5>{selected.title}</h5>
          <p>{selected.description || "설명 없음"}</p>
          <p>
            {statuses[selected.status]} · {selected.assignee_name || "미지정"} ·
            버전 {selected.revision}
          </p>
          {selected.resolution_note && (
            <p>완료·취소 사유: {selected.resolution_note}</p>
          )}
          {!editing && canOperate && (
            <button type="button" onClick={() => setEditing(true)}>
              할 일 편집
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setSelected(null);
              setEditing(false);
            }}
          >
            할 일 상세 닫기
          </button>
          {editing && (
            <TodoEditor
              key={`editor-${selected.id}`}
              row={selected}
              taskId={taskId}
              captureView={captureView}
              onSaved={(value) => {
                setSelected(value);
                setNotice("변경을 저장했습니다.");
              }}
              onClose={() => setEditing(false)}
            />
          )}
          <TodoHistory
            key={`history-${selected.id}`}
            taskId={taskId}
            todoId={selected.id}
          />
        </section>
      )}
    </section>
  );
}
