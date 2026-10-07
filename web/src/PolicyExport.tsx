import { t as uiText } from "./i18n-core.ts";
import { useId } from "react";
import { Download } from "lucide-react";
import { ReportDownload } from "./ReportDownload";
import { policyExportReason, type PolicyTask } from "./policy-export";

export function PolicyExport({ task }: { task: PolicyTask }) {
  const description = useId();
  const reason = policyExportReason(task);
  return (
    <section className="policy-export">
      <h4 className="detail-heading">{uiText("API 정책 재현")}</h4>
      <p className="subtle">
        {uiText("승인 당시의 GET 범위·응답 규칙을 별도 환경에서 검사할 수 있습니다. 인증 값과 응답 원문은 파일에 포함하지 않습니다.")}</p>
      {reason ? (
        <>
          <p id={description} className="subtle">
            {reason}
          </p>
          <button type="button" disabled aria-describedby={description}>
            <Download size={15} />
            {uiText("API 정책 JSON")}</button>
        </>
      ) : (
        <ReportDownload
          key={task.id}
          format="policy"
          taskId={task.id}
          label={uiText("API 정책 JSON")}
        />
      )}
      <details className="form-details">
        <summary>{uiText("내려받은 정책 사용하기")}</summary>
        <p>
          {uiText("Open Aegis 패키지를 설치한 환경에서 파일을 검사하세요. 기본 동작은 대상 요청을 보내지 않습니다.")}</p>
        <code className="policy-command">
          aegis-replay-policy --source aegis-api-policy.json
        </code>
        <p>
          {uiText("현재 검증 권한과 테스트 계정을 확인한 뒤 --run을 지정해야 GET 검증을 실행합니다. 파일 자체는 현재 실행 권한을 증명하지 않습니다.")}</p>
      </details>
    </section>
  );
}
