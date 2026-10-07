import { t as uiText, getFormatLocale } from "./i18n-core.ts";
import { useEffect, useState } from "react";
import { api } from "./api";
export type ExecutionPolicy = {
  target_rps: number;
  target_parallel: number;
  request_timeout: number;
  dns_timeout: number;
  task_timeout: number;
  queue_timeout: number;
  request_budget: number;
  request_retries: number;
  retry_delay: number;
  concurrent_tasks: number;
  pending_limit: number;
};
type Runtime = {
  event_planner?: {
    alive: boolean; errors: number; last_error_at: number | null;
    progress?: {status: "current" | "uninitialized" | "replay_required" | "invalid";
      after: number | null; latest_event_seq: number; pending_events: number | null;
      oldest_pending_seconds: number | null; sampled_at: number;
      asset_page: {event_seq: number; task_offset: number} | null};
  };
  authentication?: {
    active: number;
    parallel: number;
    tracked_addresses: number;
    address_limit: number;
    denied: { rate: number; capacity: number; busy: number };
  };
  exports?: {
    policy: { parallel: number; timeout: number };
    active: number;
    completed: number;
    cancelled: number;
    timed_out: number;
    failed: number;
    rejected: number;
  };
  policy: ExecutionPolicy;
  tasks: Record<string, number>;
  oldest_queue_seconds: number;
  timeouts: number;
  requests: {
    requests: number;
    active_requests: number;
    throttled_requests: number;
    throttle_seconds: number;
    retries: number;
  };
  dns: { active: number; queued: number; workers: number; queue_limit: number };
  generated_at: number;
  counter_scope: string;
  queue_watchdog: {
    alive: boolean;
    errors: number;
    last_error_at: number | null;
  };
};
export function PolicySummary({ policy }: { policy: ExecutionPolicy }) {
  return (
    <dl className="runtime-policy">
      {[
        [
          uiText("대상별 요청 속도"),
          uiText("{0}회/초 · 동시 {1}개", [policy.target_rps, policy.target_parallel]),
        ],
        [
          uiText("HTTP / DNS 시간 제한"),
          uiText("{0}초 / {1}초", [policy.request_timeout, policy.dns_timeout]),
        ],
        [
          uiText("작업 / 대기열 시간 제한"),
          uiText("{0}초 / {1}초", [policy.task_timeout, policy.queue_timeout]),
        ],
        [uiText("자산별 요청 예산"), uiText("{0}회 · 재시도 포함", [policy.request_budget])],
        [
          uiText("요청 재시도"),
          uiText("최대 {0}회 · 기본 대기 {1}초", [policy.request_retries, policy.retry_delay]),
        ],
        [
          uiText("동시 작업 / 대기·실행 한도"),
          uiText("{0}개 / {1}개", [policy.concurrent_tasks, policy.pending_limit]),
        ],
      ].map(([name, value]) => (
        <div className="setting-row" key={name}>
          <dt>{name}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
export function RuntimePanel() {
  const [data, setData] = useState<Runtime | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let controller: AbortController | undefined;
    let inFlight = false;
    const load = async () => {
      if (inFlight) return;
      inFlight = true;
      controller = new AbortController();
      try {
        const value = await api<Runtime>(
          "/runtime",
          "GET",
          undefined,
          controller.signal,
        );
        if (active) {
          setData(value);
          setError("");
        }
      } catch (e) {
        if (active && !controller.signal.aborted)
          setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    };
    void load();
    const timer = setInterval(load, 4000);
    return () => {
      active = false;
      controller?.abort();
      clearInterval(timer);
    };
  }, []);
  return (
    <section
      className="panel runtime-panel"
      aria-label={uiText("실행 대기열과 요청 지표")}
    >
      <div className="panel-head">
        <h3>{uiText("실행 대기열과 요청 지표")}</h3>
        <span className="section-eyebrow">{uiText("4초마다 갱신")}</span>
      </div>
      {error && (
        <p role="alert">
          {error} {data ? uiText("아래는 마지막으로 받은 지표입니다.") : ""}
        </p>
      )}
      {!data && !error ? (
        <p role="status">{uiText("실행 지표를 불러오는 중…")}</p>
      ) : (
        data && (
          <>
            {(!data.queue_watchdog.alive || data.queue_watchdog.errors > 0) && (
              <p role="alert">
                {uiText("대기열 감시: ")}{data.queue_watchdog.alive ? uiText("동작 중") : uiText("중단됨")}{" "}
                {uiText("· 누적 오류 ")}{data.queue_watchdog.errors}{uiText("회")}{data.queue_watchdog.last_error_at &&
                  uiText(" · 마지막 오류 {0}", [new Date(data.queue_watchdog.last_error_at * 1000).toLocaleString(getFormatLocale())])}
              </p>
            )}
            <div className="runtime-metrics">
              {[
                [uiText("승인 대기"), data.tasks.pending || 0],
                [uiText("실행 대기"), data.tasks.queued || 0],
                [uiText("실행 중"), data.tasks.running || 0],
                [uiText("중지 중"), data.tasks.stopping || 0],
                [
                  uiText("가장 오래 기다린 작업"),
                  uiText("{0}초", [data.oldest_queue_seconds.toFixed(1)]),
                ],
                [uiText("누적 시간 초과"), data.timeouts],
                [uiText("진행 중 요청"), data.requests.active_requests],
                [uiText("이번 서버 요청 시도"), data.requests.requests],
                [uiText("속도 제한 대기 요청"), data.requests.throttled_requests],
                [
                  uiText("속도 제한 누적 대기"),
                  uiText("{0}초", [data.requests.throttle_seconds.toFixed(1)]),
                ],
                [uiText("요청 재시도"), data.requests.retries],
                [uiText("DNS 처리 / 대기"), `${data.dns.active} / ${data.dns.queued}`],
                ...(data.authentication
                  ? [
                      [
                        uiText("로그인 검증 / 한도"),
                        `${data.authentication.active} / ${data.authentication.parallel}`,
                      ],
                      [
                        uiText("로그인 제한 주소 기록 / 한도"),
                        `${data.authentication.tracked_addresses} / ${data.authentication.address_limit}`,
                      ],
                      [
                        uiText("로그인 거절 · 횟수 / 주소 / 동시"),
                        `${data.authentication.denied.rate} / ${data.authentication.denied.capacity} / ${data.authentication.denied.busy}`,
                      ],
                    ]
                  : []),
                ...(data.exports
                  ? [
                      [
                        uiText("보고서 다운로드 / 한도"),
                        `${data.exports.active} / ${data.exports.policy.parallel}`,
                      ],
                      [uiText("보고서 시간 제한"), uiText("{0}초", [data.exports.policy.timeout])],
                      [uiText("이번 서버 보고서 완료"), data.exports.completed],
                      [uiText("보고서 동시 실행 한도 거절"), data.exports.rejected],
                      [uiText("보고서 시간 초과"), data.exports.timed_out],
                      [uiText("보고서 다운로드 중단"), data.exports.cancelled],
                      [uiText("보고서 처리 오류"), data.exports.failed],
                    ]
                  : []),
              ].map(([label, value]) => (
                <div className="runtime-metric" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            {data.event_planner?.progress && <section aria-label={uiText("자동 계획 이벤트 처리")}>
              <h4>{uiText("자동 계획 이벤트 처리")}</h4>
              <p role={data.event_planner.progress.status === "invalid" || !data.event_planner.alive || data.event_planner.errors > 0 ? "alert" : "status"}>
                {data.event_planner.alive ? uiText("동작 중") : uiText("중단됨")} {uiText(" · 누적 오류 ")}{data.event_planner.errors}{uiText("회")}{data.event_planner.progress.status === "invalid" ? uiText(" · 저장된 처리 위치를 확인할 수 없습니다. 운영 기록을 확인하세요.") :
                  data.event_planner.progress.status === "replay_required" ? uiText(" · 정책 변경으로 이전 이벤트를 다시 처리해야 합니다.") :
                  data.event_planner.progress.status === "uninitialized" ? uiText(" · 최초 처리 위치를 준비하고 있습니다.") : ""}
                {data.event_planner.last_error_at && uiText(" · 마지막 오류 {0}", [new Date(data.event_planner.last_error_at * 1000).toLocaleString(getFormatLocale())])}
              </p>
              <dl className="runtime-policy">
                <div className="setting-row"><dt>{uiText("처리 위치 / 최신 이벤트")}</dt><dd>{data.event_planner.progress.after ?? uiText("미확인")} / {data.event_planner.progress.latest_event_seq}</dd></div>
                <div className="setting-row"><dt>{uiText("남은 이벤트")}</dt><dd>{data.event_planner.progress.pending_events === null ? uiText("미확인") : uiText("{0}건", [data.event_planner.progress.pending_events])}</dd></div>
                <div className="setting-row"><dt>{uiText("가장 오래 기다린 이벤트")}</dt><dd>{data.event_planner.progress.oldest_pending_seconds === null ? (data.event_planner.progress.pending_events === 0 ? uiText("없음") : uiText("미확인")) : uiText("{0}초", [data.event_planner.progress.oldest_pending_seconds.toFixed(1)])}</dd></div>
                {data.event_planner.progress.asset_page && <div className="setting-row"><dt>{uiText("자산 작업 조회 위치")}</dt><dd>{uiText("이벤트 ")}{data.event_planner.progress.asset_page.event_seq} · {data.event_planner.progress.asset_page.task_offset}{uiText("개 항목 뒤")}</dd></div>}
              </dl>
              <p className="subtle">{uiText("남은 이벤트는 저장된 실제 건수이며 작업 수나 실행 승인 수가 아닙니다. 처리 위치는 재시작 후 이어집니다. 대기 시간은 저장된 시각 기준으로 시스템 시계 변경의 영향을 받습니다.")}</p>
            </section>}
            <p className="subtle">
              {uiText("작업 수와 시간 초과는 저장된 전체 기록 기준입니다. 요청·재시도·속도 제한·보고서·로그인 지표는 서버를 재시작하면 초기화됩니다.")}</p>
            <p className="subtle">
              {uiText("마지막 갱신:")}{" "}
              {new Date(data.generated_at * 1000).toLocaleString(getFormatLocale())}
            </p>
            <PolicySummary policy={data.policy} />
            <p className="subtle">
              {uiText("같은 origin의 자산과 작업은 요청 속도와 동시 요청 제한을 공유합니다. 재실행 계획에는 새 승인이 필요합니다.")}</p>
          </>
        )
      )}
    </section>
  );
}
