export type RecordedProvenance = {
  version: number;
  mode: string;
  observed_at: number;
  finding_total: number;
  citations: {
    label: string;
    kind: "task" | "finding";
    id: string;
    title: string;
    snapshot: Record<string, string | number>;
    evidence?: {
      label: string; id: string; task_id: string; asset_id: string; check: string;
      created_at: number; excerpt: string; truncated: boolean; matching_count: number;
    } | null;
  }[];
};

const labels: Record<string, string> = {
  status: "상태", assets: "자산 수", done: "처리한 자산",
  completed_checks: "완료한 검증", errors: "오류 수", severity: "심각도",
  confidence: "판정 유형", asset_name: "자산", remediation: "조치 안내",
};

export function MessageProvenance({ provenance }: { provenance?: RecordedProvenance }) {
  if (!provenance || provenance.version !== 1 || provenance.mode !== "recorded_rules") return null;
  return <details className="message-provenance">
    <summary>답변 출처 {provenance.citations.length}개 · 당시 기록 확인</summary>
    <p>답변 생성 시 읽은 기록입니다. 아래 링크는 현재 상태를 열며, 당시 상태와 다를 수 있습니다.</p>
    <p>조회 시각: <time dateTime={new Date(provenance.observed_at * 1000).toISOString()}>
      {new Date(provenance.observed_at * 1000).toLocaleString("ko-KR")}
    </time> · 연결된 발견 사항 {provenance.finding_total}개</p>
    <ol>
      {provenance.citations.map(citation => <li key={`${citation.kind}:${citation.id}`}>
        <strong>[{citation.label}] </strong>
        {/^[A-Za-z0-9_-]{1,80}$/.test(citation.id) ? <a href={`?page=${citation.kind === "task" ? "tasks" : "findings"}&detail=${citation.kind}&detail_id=${encodeURIComponent(citation.id)}`}>
          {citation.title} · 현재 기록 열기
        </a> : <span>{citation.title}</span>}
        <dl>{Object.entries(citation.snapshot).filter(([key]) => key in labels).map(([key,value]) =>
          <div key={key}><dt>{labels[key]}</dt><dd>{value}</dd></div>
        )}</dl>
        {citation.kind === "finding" && "evidence" in citation && (
          citation.evidence ? <div className="message-evidence">
            <strong>[{citation.evidence.label}] 관찰 증거</strong>
            <p>증거 ID <code>{citation.evidence.id}</code> · 도구 <code>{citation.evidence.check}</code></p>
            <p>관찰 시각: <time dateTime={new Date(citation.evidence.created_at * 1000).toISOString()}>
              {new Date(citation.evidence.created_at * 1000).toLocaleString("ko-KR")}
            </time> · 일치하는 증거 {citation.evidence.matching_count}개 중 최근 저장 1개</p>
            <pre tabIndex={0} aria-label={`${citation.evidence.label} 당시 관찰 내용`}>{citation.evidence.excerpt}</pre>
            {citation.evidence.truncated && <p>관찰 내용이 길어 앞부분 4,096자만 보존했습니다. 현재 증거에서 전체 내용을 확인하세요.</p>}
            <a href={`?page=findings&detail=finding&detail_id=${encodeURIComponent(citation.id)}&finding_evidence_open=true&finding_evidence_q=${encodeURIComponent(citation.evidence.id)}`}>
              {citation.evidence.label} · 현재 증거 열기
            </a>
          </div> : <p>이 작업과 출처가 일치하는 관찰 증거를 확인할 수 없습니다.</p>
        )}
      </li>)}
    </ol>
  </details>;
}
