import { t as uiText, localizeLabels, getFormatLocale } from "./i18n-core.ts";
import { useCallback } from "react";
import {
  readDetail,
  readFindingCollection,
  type FindingCollectionState,
  type FindingCollectionKind,
  type HistoryMode,
  type ListPosition,
} from "./navigation-state";
import { useRecords, Pagination, RecordState } from "./records";

type Evidence = {
  id: string;
  task_id: string;
  check: string;
  created_at: number;
  observation: unknown;
};
type Retest = {
  id: string;
  task_id: string;
  conclusion: string;
  created_at: number;
  state_note?: string;
};
const conclusions: Record<string, string> = localizeLabels({
  reproduced: "재현됨",
  resolved: "해결 확인",
  inconclusive: "판정 불가",
});
function timestamp(value: number) {
  return new Date(value * 1000).toLocaleString(getFormatLocale());
}

export function FindingRecords({
  findingId,
  checkNames,
  collections,
  onChange,
}: {
  findingId: string;
  checkNames: Record<string, string>;
  collections: Record<FindingCollectionKind, FindingCollectionState>;
  onChange: (
    kind: FindingCollectionKind,
    changes: Partial<FindingCollectionState>,
    mode?: HistoryMode,
  ) => void;
}) {
  return (
    <>
      <FindingCollection
        findingId={findingId}
        kind="evidence"
        state={collections.evidence}
        onChange={onChange}
        checkNames={checkNames}
      />
      <FindingCollection
        findingId={findingId}
        kind="retests"
        state={collections.retests}
        onChange={onChange}
        checkNames={checkNames}
      />
    </>
  );
}
function FindingCollection({
  findingId,
  kind,
  state,
  onChange,
  checkNames,
}: {
  findingId: string;
  kind: "evidence" | "retests";
  state: FindingCollectionState;
  onChange: (
    kind: FindingCollectionKind,
    changes: Partial<FindingCollectionState>,
    mode?: HistoryMode,
  ) => void;
  checkNames: Record<string, string>;
}) {
  const { search, expanded } = state;
  const changePosition = useCallback(
    (position: ListPosition, mode?: HistoryMode) => {
      const detail = readDetail(location.search);
      if (
        detail?.kind !== "finding" ||
        detail.id !== findingId ||
        JSON.stringify(readFindingCollection(location.search, kind)) !==
          JSON.stringify(state)
      )
        return;
      onChange(kind, position, mode);
    },
    [findingId, kind, state, onChange],
  );
  const records = useRecords<Evidence | Retest>(
    expanded ? kind : null,
    search,
    {},
    { ...state, onPositionChange: changePosition },
    `/findings/${encodeURIComponent(findingId)}/${kind}`,
  );
  const name = kind === "evidence" ? uiText("증거 이력") : uiText("재검증 이력");
  return (
    <section className="finding-collection" aria-label={name}>
      <h4 className="detail-heading">{name}</h4>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => onChange(kind, { expanded: !expanded })}
      >
        {expanded ? uiText("{0} 접기", [name]) : uiText("{0} 보기", [name])}
      </button>
      {expanded && (
        <div className="finding-collection-content">
          <label>
            {kind === "evidence"
              ? uiText("도구 ID 또는 작업 ID로 검색")
              : uiText("판정·사유 또는 작업 ID로 검색")}
            <input
              aria-label={uiText("{0} 검색", [name])}
              value={search}
              maxLength={200}
              onChange={(e) =>
                onChange(kind, { search: e.target.value }, "replace")
              }
            />
          </label>
          <Pagination records={records} />
          {!records.ready ? (
            <RecordState records={records} />
          ) : records.items.length ? (
            records.items.map((record) => (
              <article className="finding-record" key={record.id}>
                <strong>
                  {kind === "evidence"
                    ? checkNames[(record as Evidence).check] ||
                      (record as Evidence).check
                    : conclusions[(record as Retest).conclusion] ||
                      (record as Retest).conclusion}
                </strong>
                <small>{timestamp(record.created_at)}</small>
                {kind === "evidence" && (
                  <p>
                    {uiText("도구 ID ")}<code>{(record as Evidence).check}</code>
                  </p>
                )}
                <p>
                  {uiText("작업 ")}<code>{record.task_id}</code>
                </p>
                {kind === "evidence" ? (
                  <details>
                    <summary>{uiText("증거 원본 · ")}{record.id}</summary>
                    <pre>
                      {JSON.stringify(
                        (record as Evidence).observation,
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                ) : (
                  (record as Retest).state_note && (
                    <p>{(record as Retest).state_note}</p>
                  )
                )}
              </article>
            ))
          ) : (
            <p className="subtle">
              {search ? uiText("검색 결과가 없습니다.") : uiText("저장된 {0}이 없습니다.", [name])}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
