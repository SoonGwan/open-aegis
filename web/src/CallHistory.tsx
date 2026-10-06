import { useCallback } from "react";
import { useRecords, Pagination, RecordState } from "./records";
import {
  readCallList,
  CALL_STATES,
  type CallListState,
  type CallListChange,
} from "./call-navigation";
import type { ListPosition, HistoryMode } from "./navigation-state";
import { CallCost, type CallCostRecord } from "./CallCost";
export type ProviderCall = {
  id: string;
  source: string;
  state: string;
  task_id: string;
  actor_id: string | null;
  model: string;
  provider_origin: string | null;
  prompt_snapshot?: { purpose: string; revision: number; template: string; fingerprint: string };
  model_profile_snapshot?: { kind: string; purpose: string; selection_revision: number; model: string; destination_id: string; profile_id?: string; profile_revision?: number; task_model_snapshot?: { task_id: string; revision: number; profile_id: string | null } };
  started_at: number;
  observed_at: number;
  settled_at?: number;
  record_kind?: string;
  record_id?: string;
  outcome: string;
  cost?: CallCostRecord;
  tokens: {
    status: string;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  };
};
const states: Record<string, string> = {
  started: "호출 중 · 관찰 없음",
  observed: "응답 관찰 · 저장 미확정",
  committed: "결과 저장",
  uncommitted: "결과 미저장",
  interrupted: "재시작 중단",
};
const outcomes: Record<string, string> = {
  accepted: "응답 형식 수용",
  invalid_plan: "계획 형식 거절",
  invalid_answer: "답변 형식 거절",
  request_failed: "응답 확인 실패",
  unknown: "미확인",
};
const usage: Record<string, string> = {
  reported: "제공자 보고값 · 형식 검증됨",
  partial: "일부 보고값",
  missing: "보고 사용량 없음",
  invalid: "사용량 형식 또는 합계 오류",
};
const date = (value: number) => new Date(value * 1000).toLocaleString("ko-KR");
export function CallHistory({
  state,
  onChange,
  onTask,
}: {
  state: CallListState;
  onChange: CallListChange;
  onTask: (id: string) => void;
}) {
  const changePosition = useCallback(
    (position: ListPosition, mode?: HistoryMode) => {
      if (
        JSON.stringify(readCallList(location.search)) === JSON.stringify(state)
      )
        onChange(position, mode);
    },
    [state, onChange],
  );
  const filters: Record<string, string> = {};
  if (state.source) filters.source = state.source;
  if (state.state) filters.state = state.state;
  if (state.taskId) filters.task_id = state.taskId;
  const records = useRecords<ProviderCall>(
    "llm_calls",
    state.search,
    filters,
    { ...state, onPositionChange: changePosition },
    "/llm/calls",
  );
  return (
    <section
      className="panel settings-panel call-history"
      aria-label="AI 호출 시도 이력"
    >
      <div className="panel-head">
        <h3>AI 호출 시도 이력</h3>
      </div>
      <p className="subtle">
        저장 실패·중단을 포함한 개별 시도입니다. 응답 형식 수용과 결과 저장은
        별도 상태이며, 전송·청구 여부는 제공자 기록과 비교하세요. 도입 전 호출은
        포함하지 않습니다.
      </p>
      <div className="call-history-filters">
        <label>
          호출 검색
          <input
            maxLength={200}
            value={state.search}
            placeholder="ID·모델·작업 ID"
            onChange={(e) => onChange({ search: e.target.value }, "replace")}
          />
        </label>
        <label>
          시도 종류
          <select
            value={state.source}
            onChange={(e) => onChange({ source: e.target.value })}
          >
            <option value="">전체 종류</option>
            <option value="planner">계획</option>
            <option value="conversation">대화</option>
          </select>
        </label>
        <label>
          저장 상태
          <select
            value={state.state}
            onChange={(e) => onChange({ state: e.target.value })}
          >
            <option value="">전체 상태</option>
            {CALL_STATES.map((value) => (
              <option key={value} value={value}>
                {states[value]}
              </option>
            ))}
          </select>
        </label>
        <label>
          작업 ID
          <input
            maxLength={80}
            value={state.taskId}
            onChange={(e) => onChange({ taskId: e.target.value }, "replace")}
          />
        </label>
      </div>
      <Pagination records={records} />
      {!records.ready ? (
        <RecordState records={records} />
      ) : records.items.length ? (
        records.items.map((call) => (
          <article className="call-history-record" key={call.id}>
            <h4>
              {call.source === "planner" ? "계획" : "대화"} ·{" "}
              {states[call.state] || "알 수 없는 저장 상태"}
            </h4>
            <p>
              {call.model} · {outcomes[call.outcome] || "미확인"}
            </p>
            <p>
              시도 ID: <code>{call.id}</code>
            </p>
            <p>시작: {date(call.started_at)}</p>
            <button type="button" onClick={() => onTask(call.task_id)}>
              작업 보기 · {call.task_id}
            </button>
            <details>
              <summary>호출 상세 · 사용량과 가격 근거</summary>
              <p>제공자: {call.provider_origin || "미확인"}</p>
              <section aria-label="호출 당시 모델 설정">
                <h5>호출 당시 모델 선택</h5>
                {call.model_profile_snapshot ? <>
                  <p>용도: {call.model_profile_snapshot.purpose === "planner" ? "검증 순서 계획" : "기록 기반 대화"} · 선택 버전 {call.model_profile_snapshot.selection_revision}</p>
                  {call.model_profile_snapshot.task_model_snapshot && <p>작업별 선택 버전 {call.model_profile_snapshot.task_model_snapshot.revision} · {call.model_profile_snapshot.task_model_snapshot.profile_id ? "작업 고정 프로필" : "워크스페이스 용도별 선택 따름"}</p>}
                  <p>모델: {call.model_profile_snapshot.model} · 고정 수신처: {call.model_profile_snapshot.destination_id}</p>
                  <p>{call.model_profile_snapshot.kind === "profile" ? `프로필 ${call.model_profile_snapshot.profile_id} · 버전 ${call.model_profile_snapshot.profile_revision}` : "기본 환경 설정"}</p>
                </> : <p>모델 선택 스냅샷 기록 없음</p>}
              </section>
              <section aria-label="호출 당시 프롬프트">
                <h5>호출 당시 추가 지침</h5>
                {call.prompt_snapshot ? <><p>프롬프트 버전 {call.prompt_snapshot.revision}</p><pre className="prompt-text">{call.prompt_snapshot.template || "기본 프롬프트 · 추가 지침 없음"}</pre></> : <p>프롬프트 스냅샷 기록 없음</p>}
              </section>
              <p>호출자 ID: {call.actor_id || "기록 없음"}</p>
              <p>{usage[call.tokens.status] || "알 수 없는 사용량 상태"}</p>
              <dl>
                {(
                  [
                    ["입력", call.tokens.prompt_tokens],
                    ["출력", call.tokens.completion_tokens],
                    ["합계", call.tokens.total_tokens],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label}>
                    <dt>{label} 토큰</dt>
                    <dd>
                      {value === null
                        ? "미확인"
                        : value.toLocaleString("ko-KR")}
                    </dd>
                  </div>
                ))}
              </dl>
              {call.outcome === "unknown" ? (
                <p>관찰된 응답 없음 · 사용량 미확인</p>
              ) : (
                <p>응답 관찰: {date(call.observed_at)}</p>
              )}
              {call.settled_at && (
                <p>저장 상태 확정: {date(call.settled_at)}</p>
              )}
              {call.record_id && (
                <p>
                  연결된 {call.record_kind === "messages" ? "답변" : "계획"} ID:{" "}
                  <code>{call.record_id}</code>
                </p>
              )}
              {(call.state === "uncommitted" ||
                call.state === "interrupted") && (
                <p>
                  결과가 저장되지 않았거나 저장 여부를 확인하지 못했습니다.
                  세션·저장·서버 기록을 함께 확인하세요. 이 기록만으로 정확한
                  실패 원인을 단정하지 않습니다.
                </p>
              )}
              <CallCost cost={call.cost} />
            </details>
          </article>
        ))
      ) : (
        <p className="subtle">조건에 맞는 호출 시도 기록이 없습니다.</p>
      )}
    </section>
  );
}
