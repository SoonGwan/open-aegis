import { t as uiText } from "./i18n-core.ts";
import { useId } from "react";
import {
  validateWorkerDependencies,
  type Dependencies,
  type PickerAsset,
} from "./worker-dependency-state";

export function WorkerDependencyEditor({
  assets,
  dependencies,
  onChange,
}: {
  assets: PickerAsset[];
  dependencies: Dependencies;
  onChange: (next: Dependencies) => void;
}) {
  const helpId = useId(),
    errorId = useId();
  let error = "";
  if (assets.length) {
    try {
      validateWorkerDependencies(
        assets.map((asset) => asset.id),
        dependencies,
      );
    } catch (e) {
      error = (e as Error).message;
    }
  }
  const parentsFor = (id: string) =>
    Object.hasOwn(dependencies, id) ? dependencies[id] : [];
  const count = Object.values(dependencies).reduce(
    (sum, parents) => sum + parents.length,
    0,
  );
  return (
    <fieldset
      className="worker-dependency-editor"
      aria-label={uiText("Worker 실행 순서 설정")}
    >
      <legend>{uiText("Worker 실행 순서 · ")}{count} {uiText(" / 최대 40개 연결")}</legend>
      <p id={helpId} className="subtle">
        {uiText("선행 자산의 검증이 모두 완료된 후 후행 자산을 시작합니다. 지정하지 않으면 독립적으로 실행합니다. 선행 검증이 실패하거나 건너뛰면 후행은 실행하지 않습니다. 자산 선택을 해제하면 관련 의존 관계도 제거합니다.")}</p>
      <input
        type="hidden"
        name="worker_dependencies"
        value={JSON.stringify(dependencies)}
      />
      {assets.length < 2 ? (
        <p className="subtle">
          {uiText("2개 이상의 자산을 선택하면 선행 자산을 지정할 수 있습니다.")}</p>
      ) : (
        assets.map((child) => (
          <details className="finding-record" key={child.id}>
            <summary>
              {child.name} {uiText(" · 선행 ")}{parentsFor(child.id).length}{uiText("개")}</summary>
            <code className="observation-url">{child.url || child.id}</code>
            <div
              className="worker-predecessors"
              role="group"
              aria-label={uiText("{0}의 선행 자산", [child.name])}
            >
              <p className="subtle">{uiText("선행 자산")}</p>
              {assets
                .filter((parent) => parent.id !== child.id)
                .map((parent) => (
                  <label className="checkbox-label" key={parent.id}>
                    <input
                      type="checkbox"
                      data-worker-dependency
                      data-worker-child={child.id}
                      aria-label={uiText("{0}의 선행 자산 {1} ({2})", [child.name, parent.name, parent.url || parent.id])}
                      aria-describedby={`${helpId}${error ? ` ${errorId}` : ""}`}
                      aria-invalid={!!error}
                      checked={parentsFor(child.id).includes(parent.id)}
                      onChange={(event) => {
                        const parents = parentsFor(child.id);
                        const next = {
                          ...dependencies,
                          [child.id]: event.target.checked
                            ? [...parents, parent.id]
                            : parents.filter((id) => id !== parent.id),
                        };
                        if (!next[child.id].length) delete next[child.id];
                        onChange(next);
                      }}
                    />
                    <span>
                      {parent.name}
                      <small className="observation-url">
                        {parent.url || parent.id}
                      </small>
                    </span>
                  </label>
                ))}
            </div>
          </details>
        ))
      )}
      {error && (
        <p className="form-error" id={errorId} role="alert" data-worker-error>
          {error}
        </p>
      )}
      {count > 0 && (
        <button type="button" onClick={() => onChange({})}>
          {uiText("의존 관계 모두 해제")}</button>
      )}
    </fieldset>
  );
}
