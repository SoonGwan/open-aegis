import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "./api";
import { useRecords, Pagination, RecordState } from "./records";

type Message = {
  id: string;
  role: string;
  content: string;
  created_at: number;
  finding_ids?: string[];
};

export function ChatPanel({
  taskId,
  canOperate,
}: {
  taskId: string;
  canOperate: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const active = useRef(true);
  const submitting = useRef(false);
  const attempt = useRef<{ content: string; request_id: string } | null>(null);
  const messageBox = useRef<HTMLDivElement>(null);
  const pendingReply = useRef<string | null>(null);
  const records = useRecords<Message>(
    open ? "messages" : null,
    search,
    {},
    undefined,
    `/tasks/${encodeURIComponent(taskId)}/messages/page`,
  );
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
    if (!attempt.current || attempt.current.content !== question)
      attempt.current = {
        content: question,
        request_id: Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
          byte.toString(16).padStart(2, "0"),
        ).join(""),
      };
    submitting.current = true;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const reply = await api<Message>(
        `/tasks/${encodeURIComponent(taskId)}/messages`,
        "POST",
        attempt.current,
      );
      if (!active.current) return;
      attempt.current = null;
      pendingReply.current = reply.id;
      setQuestion("");
      setSearch("");
      setSaved(true);
      records.reload();
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <details
      className="chat-panel"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        검증 기록에 질문하기 <span>규칙 기반 · 추가 요청 없음</span>
      </summary>
      {open && (
        <section aria-label="검증 대화 이력">
          <label className="task-record-search">
            메시지 내용·역할로 검색
            <input
              aria-label="검증 대화 검색"
              value={search}
              maxLength={200}
              onChange={(e) => setSearch(e.target.value)}
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
          <form onSubmit={submit}>
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
              {busy ? "요약 중…" : error ? "질문 다시 보내기" : "질문하기"}
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
