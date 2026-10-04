import { toolContractsMatch, type ToolManifest } from "./tool-contract-state";
export function ToolContracts({
  snapshot,
  current,
  selected,
  names,
  pending,
}: {
  snapshot?: ToolManifest;
  current?: ToolManifest;
  selected: string[];
  names: Record<string, string>;
  pending: boolean;
}) {
  const matches = toolContractsMatch(snapshot, selected, current);
  return (
    <section
      className="tool-contract-summary"
      aria-label="계획의 검증 도구 계약"
    >
      {!matches && (
        <p className="subtle">
          {pending
            ? "도구 계약이 없거나 현재 도구와 다릅니다. 현재 자산과 도구로 새 계획을 만들고 승인하세요."
            : "현재 도구와 계약이 다르거나 이전 기록에 계약이 없습니다. 이 화면은 당시의 기록을 보여줍니다."}
        </p>
      )}
      {snapshot && Array.isArray(snapshot.checks) && (
        <details>
          <summary>계획의 도구 계약</summary>
          <p className="subtle">
            승인과 실행 전에 도구 버전 및 코드 지문을 다시 확인합니다. 지문은
            버전 비교용이며 전자서명이 아닙니다.
          </p>
          <dl className="runtime-policy">
            {snapshot.checks
              .filter((contract) => contract && typeof contract.id === "string")
              .map((contract) => (
                <div className="setting-row" key={contract.id}>
                  <dt>
                    {names[contract.id] || contract.id} · v{contract.version}
                  </dt>
                  <dd>
                    {contract.method} · 발견 최대 {contract.max_findings}개 ·
                    링크 최대 {contract.max_observations}개 · 결과 최대{" "}
                    {Math.floor(contract.max_result_bytes / 1024)} KiB
                  </dd>
                </div>
              ))}
          </dl>
          <p>
            계획 생성 시 코드 지문 <code>{snapshot.package_sha256}</code>
          </p>
        </details>
      )}
    </section>
  );
}
