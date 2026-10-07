import { t as uiText, localizeLabels } from "./i18n-core.ts";
export const coverageNames: Record<string, string> = localizeLabels({
  not_started: "미실행",
  running: "실행 중",
  completed: "완료",
  skipped: "건너뜀",
  failed: "실패",
  cancelled: "취소",
  interrupted: "중단",
  not_recorded: "기록 없음",
  stale: "이전 범위",
});
export type Coverage = {
  targets?: {
    observation_id: string;
    url: string;
    status: string;
    error_type?: string;
  }[];
  id: string;
  asset_id: string;
  task_id: string;
  check: string;
  status: string;
  asset_revision?: number;
  reason?: string;
  error_type?: string;
};
export type CoverageSummary = {
  expected: number;
  completed: number;
  percent?: number;
  counts: Record<string, number>;
};

export function CoverageOverview({ summary }: { summary?: CoverageSummary }) {
  if (!summary) return null;
  return (
    <section className="panel coverage-panel">
      <div className="panel-head">
        <h3>{uiText("도구별 검증 커버리지")}</h3>
        <span className="subtle">
          {uiText("완료 ")}{summary.completed} / {summary.expected}
        </span>
      </div>
      <p className="footnote">
        {uiText("활성 자산 × 등록된 6개 도구 기준입니다. 도구마다 가장 최근 승인한 계획의 결과를 사용하며, 자산을 수정하면 이전 범위의 결과로 표시합니다. 완료는 검증 수행 여부입니다.")}</p>
      <div className="coverage-statuses">
        {Object.entries(coverageNames).map(([status, name]) => (
          <div key={status} className={`coverage-count ${status}`}>
            <span>{name}</span>
            <strong>{(summary.counts[status] || 0).toLocaleString()}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function CoverageTable({
  rows,
  assets,
  tools,
}: {
  rows: Coverage[];
  assets: { id: string; name: string }[];
  tools: { id: string; name: string }[];
}) {
  return (
    <div
      className="table-scroll coverage-table"
      tabIndex={0}
      role="region"
      aria-label={uiText("도구별 결과표 · 좌우 스크롤로 근거 확인")}
    >
      <table>
        <caption>{uiText("선택한 자산과 도구별 실행 결과")}</caption>
        <thead>
          <tr>
            <th scope="col">{uiText("자산")}</th>
            <th scope="col">{uiText("검증 도구")}</th>
            <th scope="col">{uiText("결과")}</th>
            <th scope="col">{uiText("근거")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                {assets.find((asset) => asset.id === row.asset_id)?.name ||
                  row.asset_id}
              </td>
              <td>
                {tools.find((tool) => tool.id === row.check)?.name || row.check}
              </td>
              <td>
                <span className={`coverage-state ${row.status}`}>
                  {coverageNames[row.status] || uiText("기록 없음")}
                </span>
              </td>
              <td>
                {row.reason ||
                  (row.status === "completed"
                    ? uiText("이전 기록의 완료 결과")
                    : uiText("상세 기록 없음"))}
                {row.error_type && <small> ({row.error_type})</small>}
                {row.targets && (
                  <details>
                    <summary>{uiText("관찰 URL별 결과 · ")}{row.targets.length}{uiText("개")}</summary>
                    {row.targets.map((target) => (
                      <p key={target.observation_id}>
                        <code>{target.url}</code> ·{" "}
                        {coverageNames[target.status] || uiText("기록 없음")}
                        {target.error_type && (
                          <small> ({target.error_type})</small>
                        )}
                      </p>
                    ))}
                  </details>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
