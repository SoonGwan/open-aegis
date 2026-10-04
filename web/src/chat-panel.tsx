import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { ArrowRight } from "lucide-react";
import { api } from "./api";
import { MessageProvenance, type RecordedProvenance } from "./MessageProvenance";
import { useRecords, Pagination, RecordState } from "./records";
import {
  readDetail,
  readTaskChat,
  type TaskChatState,
  type HistoryMode,
  type ListPosition,
} from "./navigation-state";

import {
  pendingStorage,
  readPending,
  writePending,
  clearPending,
  type PendingQuestion,
} from "./chat-pending";

type Message = {
  id: string;
  role: string;
  content: string;
  created_at: number;
  finding_ids?: string[];
  provenance?: RecordedProvenance;
  assistant_generation?: {
    model: string; outcome: string;
    tokens: {status: string; prompt_tokens: number|null; completion_tokens: number|null; total_tokens: number|null};
  };
};

export function ChatPanel({
  taskId,
  actorId,
  canOperate,
  state,
  onChange,
  captureView,
  onSaved,
}: {
  taskId: string;
  actorId: string;
  canOperate: boolean;
  state: TaskChatState;
  onChange: (changes: Partial<TaskChatState>, mode?: HistoryMode) => void;
  captureView: () => () => boolean;
  onSaved: (current: boolean) => void;
}) {
  const [restored] = useState(() =>
    readPending(pendingStorage(), actorId, taskId),
  );
  const [unconfirmed, setUnconfirmed] = useState(!!restored);
  const [storageWarning, setStorageWarning] = useState("");
  const { expanded: open, search } = state;
  const [question, setQuestion] = useState(restored?.content ?? "");
  const [mode,setMode] = useState<"rules"|"ai">(restored?.mode ?? "rules");
  const [aiReady,setAiReady] = useState(false);
  const [aiConfigurationError,setAiConfigurationError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const active = useRef(true);
  const submitting = useRef(false);
  const attempt = useRef<PendingQuestion | null>(restored);
  const persistedAttempt = useRef(restored?.request_id ?? null);
  const messageBox = useRef<HTMLDivElement>(null);
  const pendingReply = useRef<string | null>(null);
  const changePosition = useCallback(
    (position: ListPosition, mode?: HistoryMode) => {
      const detail = readDetail(location.search);
      if (
        detail?.kind !== "task" ||
        detail.id !== taskId ||
        JSON.stringify(readTaskChat(location.search)) !== JSON.stringify(state)
      )
        return;
      onChange(position, mode);
    },
    [taskId, state, onChange],
  );
  const records = useRecords<Message>(
    open ? "messages" : null,
    search,
    {},
    { ...state, onPositionChange: changePosition },
    `/tasks/${encodeURIComponent(taskId)}/messages/page`,
  );
  useEffect(()=>{
    if(!open) return;
    let current=true;
    api<{llm_chat_configured:boolean}>("/settings").then(value=>{
      if(current) {setAiReady(value.llm_chat_configured);setAiConfigurationError("");}
    }).catch(()=>{if(current) {setAiReady(false);setAiConfigurationError("AI 설정을 확인하지 못했습니다. 대화를 접었다 다시 펼쳐 재시도하세요.");}});
    return ()=>{current=false;};
  },[open,taskId]);
  useEffect(() => {
    const detail = readDetail(location.search);
    if (restored && detail?.kind === "task" && detail.id === taskId)
      onChange({ expanded: true }, "replace");
  }, [restored, taskId, onChange]);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    if (open && records.ready && messageBox.current)
      messageBox.current.scrollTop = messageBox.current.scrollHeight;
  }, [open, records.ready, records.offset, search]);
  useEffect(() => {
    if (
      pendingReply.current &&
      records.items.some((m) => m.id === pendingReply.current)
    ) {
      if (messageBox.current)
        messageBox.current.scrollTop = messageBox.current.scrollHeight;
      pendingReply.current = null;
    }
  }, [records.items]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (submitting.current || !canOperate || !question.trim()) return;
    if (!attempt.current || attempt.current.content !== question || (attempt.current.mode ?? "rules") !== mode)
      attempt.current = {
        content: question,
        mode,
        request_id: Array.from(
          crypto.getRandomValues(new Uint8Array(16)),
          (byte) => byte.toString(16).padStart(2, "0"),
        ).join(""),
      };
    const pending = attempt.current;
    const isCurrent = captureView();
    const persisted = writePending(pendingStorage(), actorId, taskId, pending);
    if (persisted) persistedAttempt.current = pending.request_id;
    setStorageWarning(
      persisted
        ? ""
        : "이 탭에 질문을 보관할 수 없습니다. 화면을 닫거나 새로고침하면 재시도 정보가 사라집니다.",
    );
    setUnconfirmed(true);
    submitting.current = true;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const reply = await api<Message>(
        `/tasks/${encodeURIComponent(taskId)}/messages`,
        "POST",
        pending,
      );
      const cleared = clearPending(
        pendingStorage(),
        actorId,
        taskId,
        pending.request_id,
      );
      const current = active.current && isCurrent();
      onSaved(current);
      if (!active.current) return;
      attempt.current = null;
      setUnconfirmed(false);
      setStorageWarning(
        !cleared && persistedAttempt.current === pending.request_id
          ? "답변은 저장됐지만 이 탭의 재시도 정보를 지우지 못했습니다. 다시 열면 기존 답변을 다시 확인할 수 있습니다."
          : "",
      );
      if (cleared) persistedAttempt.current = null;
      if (current) pendingReply.current = reply.id;
      setQuestion("");
      setSaved(true);
      if (current) {
        records.reload();
        onChange(
          { expanded: true, search: "", offset: 0, snapshot: null },
          "replace",
        );
      }
    } catch (e) {
      if (active.current && isCurrent()) setError((e as Error).message);
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <details className="chat-panel" open={open}>
      <summary
        onClick={(event) => {
          event.preventDefault();
          onChange({ expanded: !open });
        }}
      >
        검증 기록에 질문하기 <span>{mode === "ai" ? "AI 초안 선택 · 대상 실행 없음" : "규칙 기반 · 추가 요청 없음"}</span>
      </summary>
      {open && (
        <section aria-label="검증 대화 이력">
          <label className="task-record-search">
            메시지 내용·역할로 검색
            <input
              aria-label="검증 대화 검색"
              value={search}
              maxLength={200}
              onChange={(e) => onChange({ search: e.target.value }, "replace")}
            />
          </label>
          <p className="subtle">
            최신 25개부터 표시합니다. 다음 페이지에서 과거 대화를 확인하세요.
            페이지 안에서는 오래된 메시지부터 표시합니다.
          </p>
          <Pagination records={records} />
          <div
            ref={messageBox}
            className="chat-messages"
            role="region"
            tabIndex={0}
            aria-label="대화 메시지"
          >
            {!records.ready ? (
              <RecordState records={records} />
            ) : records.items.length ? (
              [...records.items].reverse().map((m) => (
                <article className={`chat-message ${m.role}`} key={m.id}>
                  <small>
                    {m.role === "user" ? "질문" : "Evidence Assistant"} ·{" "}
                    <time
                      dateTime={new Date(m.created_at * 1000).toISOString()}
                    >
                      {new Date(m.created_at * 1000).toLocaleString("ko-KR")}
                    </time>
                  </small>
                  <p>{m.content}</p>
                  {m.assistant_generation && <div className="message-generation">
                    <p>AI 대화 · {m.assistant_generation.model} · {m.assistant_generation.outcome === "accepted" ? "초안 저장" : "규칙 요약으로 복구"}</p>
                    <p>사용량: {m.assistant_generation.tokens.status} · 입력 {m.assistant_generation.tokens.prompt_tokens ?? "미확인"} / 출력 {m.assistant_generation.tokens.completion_tokens ?? "미확인"} / 합계 {m.assistant_generation.tokens.total_tokens ?? "미확인"}</p>
                  </div>}
                  <MessageProvenance provenance={m.provenance} />
                  {!!m.finding_ids?.length && (
                    <small>연결된 발견 사항 {m.finding_ids.length}개</small>
                  )}
                </article>
              ))
            ) : (
              <p className="subtle">
                {search
                  ? "검색 결과가 없습니다."
                  : "저장된 대화가 없습니다. 검증 결과나 수정 우선순위를 질문해 보세요."}
              </p>
            )}
          </div>
          {unconfirmed && !busy && (
            <div className="chat-recovery">
              <p role="status">
                응답을 확인하지 못한 질문이 있습니다. 같은 내용으로 다시 보내면
                기존 답변을 확인합니다. 내용을 바꾸면 새 질문으로 보냅니다.
              </p>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  if (attempt.current) {
                    const cleared = clearPending(
                      pendingStorage(),
                      actorId,
                      taskId,
                      attempt.current.request_id,
                    );
                    if (
                      !cleared &&
                      persistedAttempt.current === attempt.current.request_id
                    ) {
                      setStorageWarning(
                        "이 탭의 재시도 정보를 지우지 못했습니다. 브라우저 저장소 설정을 확인하고 다시 시도하세요.",
                      );
                      return;
                    }
                    if (cleared) persistedAttempt.current = null;
                    if (question === attempt.current.content) setQuestion("");
                  }
                  attempt.current = null;
                  setUnconfirmed(false);
                  setError("");
                  setStorageWarning("");
                }}
              >
                미확인 전송 지우기
              </button>
              <p className="subtle">
                이 탭의 재시도 정보만 지웁니다. 서버에 저장된 대화는 이력에
                남습니다.
              </p>
            </div>
          )}
          {storageWarning && (
            <p role="alert" className="form-error">
              {storageWarning}
            </p>
          )}
          <form onSubmit={submit}>
            <label>답변 방식
              <select value={mode} disabled={busy || unconfirmed || !canOperate}
                onChange={e=>setMode(e.target.value as "rules"|"ai")}>
                <option value="rules">기록의 규칙 기반 요약</option>
                <option value="ai" disabled={!aiReady}>AI 초안{aiReady ? "" : " · 서버 설정 필요"}</option>
              </select>
            </label>
            {mode === "ai" && <p className="subtle">질문과 저장된 작업·발견·관찰 발췌를 서버에 설정된 AI 제공자로 보냅니다. 인용 소속을 검사한 초안이며 사실성은 직접 검토하세요. 추가 실행은 하지 않습니다.</p>}
            {aiConfigurationError && <p role="status">{aiConfigurationError}</p>}
            <label>
              검증 질문
              <input
                maxLength={2000}
                required
                value={question}
                disabled={busy || !canOperate}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="저장된 검증 기록에 대해 질문하세요"
              />
            </label>
            <button
              className="primary"
              disabled={busy || !canOperate || !question.trim()}
            >
              {busy
                ? "요약 중…"
                : unconfirmed || error
                  ? "질문 다시 보내기"
                  : "질문하기"}
              <ArrowRight size={14} />
            </button>
          </form>
          {!canOperate && (
            <p className="subtle">
              조회 권한으로 저장된 대화를 확인할 수 있습니다.
            </p>
          )}
          {saved && <p role="status">질문과 답변을 저장했습니다.</p>}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </section>
      )}
    </details>
  );
}
