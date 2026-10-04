export type PickerAsset = { id: string; name: string; url: string };
export type Dependencies = Record<string, string[]>;
export type WorkerSelection = {
  selected: Record<string, PickerAsset>;
  dependencies: Dependencies;
};

export function selectWorkerAsset(
  state: WorkerSelection,
  asset: PickerAsset,
  checked: boolean,
): WorkerSelection {
  const selected = { ...state.selected };
  if (checked) {
    if (
      !Object.hasOwn(selected, asset.id) &&
      Object.keys(selected).length >= 20
    )
      return state;
    Object.defineProperty(selected, asset.id, {
      value: asset,
      enumerable: true,
      writable: true,
      configurable: true,
    });
  } else delete selected[asset.id];
  const dependencies = Object.fromEntries(
    Object.entries(state.dependencies)
      .filter(([id]) => Object.hasOwn(selected, id))
      .map(([id, parents]) => [
        id,
        parents.filter((parent) => Object.hasOwn(selected, parent)),
      ])
      .filter(([, parents]) => (parents as string[]).length),
  );
  return { selected, dependencies };
}

export class WorkerDependencyError extends Error {
  child: string | null;
  constructor(message: string, child: string | null = null) {
    super(message);
    this.child = child;
  }
}

export function validateWorkerDependencies(
  assetIds: unknown[],
  value: unknown,
): asserts value is Dependencies {
  if (
    !assetIds.length ||
    assetIds.length > 20 ||
    assetIds.some((id) => typeof id !== "string") ||
    new Set(assetIds).size !== assetIds.length
  )
    throw new WorkerDependencyError("검증 자산을 1–20개 선택하세요.");
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.keys(value).length > 20
  )
    throw new WorkerDependencyError("Worker 의존 관계를 확인하세요.");
  const dependencies = value as Dependencies;
  let edges = 0;
  for (const [child, parents] of Object.entries(dependencies)) {
    if (
      !assetIds.includes(child) ||
      !Array.isArray(parents) ||
      parents.length > 20 ||
      parents.some(
        (parent) =>
          typeof parent !== "string" ||
          !assetIds.includes(parent) ||
          parent === child,
      ) ||
      new Set(parents).size !== parents.length
    )
      throw new WorkerDependencyError(
        "선택한 서로 다른 자산만 선행 자산으로 지정할 수 있습니다.",
        child,
      );
    edges += parents.length;
  }
  if (edges > 40)
    throw new WorkerDependencyError("Worker 의존 연결은 최대 40개입니다.");
  const visited = new Set<string>(),
    active = new Set<string>();
  const visit = (id: string) => {
    if (active.has(id))
      throw new WorkerDependencyError(
        "Worker 의존 관계에 순환이 있습니다. 선행 자산 설정을 수정하세요.",
        id,
      );
    if (visited.has(id)) return;
    active.add(id);
    for (const parent of Object.hasOwn(dependencies, id)
      ? dependencies[id]
      : [])
      visit(parent);
    active.delete(id);
    visited.add(id);
  };
  for (const id of assetIds as string[]) visit(id);
}
