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
      </li>)}
    </ol>
  </details>;
}
