import { t as uiText } from "./i18n-core.ts";
export function WorkerDependencies({
  dependencies,
  assets,
}: {
  dependencies?: Record<string, string[]>;
  assets: { id: string; name: string; url?: string }[];
}) {
  const entries = Object.entries(dependencies || {}).filter(
    ([, parents]) => parents.length > 0,
  );
  if (!entries.length) return null;
  const name = (id: string) => {
    const asset = assets.find((asset) => asset.id === id);
    return asset ? `${asset.name}${asset.url ? ` · ${asset.url}` : ""}` : id;
  };
  return (
    <section className="finding-collection" aria-label={uiText("Worker 의존 관계")}>
      <h4 className="detail-heading">{uiText("Worker 실행 의존 관계")}</h4>
      <p className="subtle">
        {uiText("선행 자산의 선택한 검증이 모두 완료된 후 시작합니다. 선행 검증이 실패하거나 건너뛰면 후행 자산은 요청하지 않습니다.")}</p>
      {entries.map(([child, parents]) => (
        <p className="finding-record" key={child}>
          <strong>{name(child)}</strong> {uiText(" · 선행 자산:")}{" "}
          {parents.map(name).join(", ")}
        </p>
      ))}
    </section>
  );
}
