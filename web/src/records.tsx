import { useCallback, useEffect, useRef, useState } from "react";
import { WorkerDependencyEditor } from "./WorkerDependencyEditor";
import {
  selectWorkerAsset,
  type WorkerSelection,
  type PickerAsset,
} from "./worker-dependency-state";
import { api } from "./api";
import type { ListPosition, HistoryMode } from "./navigation-state";

type Result<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  snapshot: number;
  has_more: boolean;
};
const empty = {
  items: [],
  total: 0,
  limit: 25,
  offset: 0,
  snapshot: 0,
  has_more: false,
};

export function useRecords<T>(
  kind: string | null,
  search: string,
  filters: Record<string, string>,
  external?: ListPosition & {
    onPositionChange: (position: ListPosition, mode?: HistoryMode) => void;
  },
  endpoint?: string,
  poll = true,
) {
  const key = JSON.stringify([kind, search, filters, endpoint]);
  const [position, setPosition] = useState({
    key,
    offset: 0,
    snapshot: null as number | null,
  });
  const current =
    external ||
    (position.key === key ? position : { key, offset: 0, snapshot: null });
  const onPositionChange = external?.onPositionChange;
  const move = useCallback(
    (next: ListPosition, mode: HistoryMode = "push") => {
      if (onPositionChange) onPositionChange(next, mode);
      else setPosition({ key, ...next });
    },
    [key, onPositionChange],
  );
  const [result, setResult] = useState<{ key: string; data: Result<T> }>({
    key: "",
    data: empty,
  });
  const [request, setRequest] = useState({
    key: "",
    loading: false,
    error: "",
  });
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  const requestKey = JSON.stringify([key, current.offset, current.snapshot]);
  useEffect(() => {
    if (!kind) return;
    const update = () => setRevision((value) => value + 1);
    const mutation = () => {
      move({ offset: current.offset, snapshot: null }, "replace");
      update();
    };
    const timer = poll ? setInterval(update, 4000) : undefined;
    window.addEventListener("aegis-records-changed", mutation);
    return () => {
      if (timer !== undefined) clearInterval(timer);
      window.removeEventListener("aegis-records-changed", mutation);
    };
  }, [kind, requestKey, move, poll]);
  useEffect(() => {
    const requestSequence = ++sequence.current;
    if (!kind) return;
    const controller = new AbortController();
    setRequest({ key: requestKey, loading: true, error: "" });
    const timer = setTimeout(() => {
      const query = new URLSearchParams({
        limit: "25",
        offset: String(current.offset),
        search,
        ...filters,
      });
      if (current.snapshot !== null)
        query.set("snapshot", String(current.snapshot));
      api<Result<T>>(
        `${endpoint || `/records/${kind}`}?${query}`,
        "GET",
        undefined,
        controller.signal,
      )
        .then((data) => {
          if (sequence.current !== requestSequence || controller.signal.aborted)
            return;
          const last = Math.max(0, Math.floor((data.total - 1) / 25) * 25);
          if (current.offset > last)
            move({ offset: last, snapshot: data.snapshot }, "replace");
          else setResult({ key: requestKey, data });
        })
        .catch((error) => {
          if (
            !controller.signal.aborted &&
            sequence.current === requestSequence
          )
            setRequest({
              key: requestKey,
              loading: false,
              error: error.message,
            });
        })
        .finally(() => {
          if (
            !controller.signal.aborted &&
            sequence.current === requestSequence
          )
            setRequest((value) => ({ ...value, loading: false }));
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [requestKey, revision, move]);
  const ready = result.key === requestKey;
  const data = ready ? result.data : (empty as Result<T>);
  const error = request.key === requestKey ? request.error : "";
  const loading =
    Boolean(kind) &&
    ((!ready && !error) || (request.key === requestKey && request.loading));
  return {
    ...data,
    offset: current.offset,
    loading,
    ready,
    error,
    next: () => move({ offset: current.offset + 25, snapshot: data.snapshot }),
    previous: () =>
      move({
        offset: Math.max(0, current.offset - 25),
        snapshot: data.snapshot,
      }),
    reload: () => {
      move({ offset: 0, snapshot: null });
      setRevision((value) => value + 1);
    },
    retry: () => setRevision((value) => value + 1),
  };
}

/** Use before an empty-state: an unfinished or failed query is not an empty result. */
export function RecordState({
  records,
}: {
  records: ReturnType<typeof useRecords>;
}) {
  return (
    <div className="record-state" aria-busy={records.loading}>
      {records.error ? (
        <>
          <p role="alert">{records.error}</p>
          <button
            type="button"
            onClick={records.reload}
            disabled={records.loading}
          >
            목록 다시 불러오기
          </button>
        </>
      ) : (
        <p role="status">목록을 불러오는 중…</p>
      )}
    </div>
  );
}

export function Pagination({
  records,
}: {
  records: ReturnType<typeof useRecords>;
}) {
  return (
    <nav className="pagination" aria-label="목록 페이지">
      <span aria-live="polite">
        {records.error
          ? records.ready
            ? "조회 실패 · 마지막으로 받은 목록"
            : "목록 조회 실패"
          : records.loading
            ? records.ready
              ? "목록 갱신 중"
              : "불러오는 중"
            : records.total
              ? `${records.offset + 1}–${records.offset + records.items.length} / 전체 ${records.total.toLocaleString()}개`
              : "검색 결과 0개"}
      </span>
      {records.error && records.ready && (
        <span role="alert">{records.error}</span>
      )}
      <button
        type="button"
        onClick={records.previous}
        disabled={records.loading || !records.offset}
      >
        이전
      </button>
      <button
        type="button"
        onClick={records.next}
        disabled={records.loading || !records.has_more}
      >
        다음
      </button>
      <button type="button" onClick={records.reload} disabled={records.loading}>
        최신 목록
      </button>
    </nav>
  );
}

export function AssetPicker({
  initialId,
  initialAsset,
  initialSelection,
  onDraftChange,
}: {
  initialId: string | null;
  initialAsset?: PickerAsset;
  initialSelection?: WorkerSelection;
  onDraftChange?: () => void;
}) {
  const [search, setSearch] = useState("");
  const [selection, setSelection] = useState<WorkerSelection>(() => initialSelection || ({
    selected: initialId
      ? {
          [initialId]: initialAsset || {
            id: initialId,
            name: initialId,
            url: "",
          },
        }
      : {},
    dependencies: {},
  }));
  const selected = selection.selected;
  const records = useRecords<PickerAsset>("assets", search, {
    archived: "false",
  });
  const count = Object.keys(selected).length;
  return (
    <>
      <fieldset className="asset-picker">
        <legend>
          검증 자산 <span>{count} / 최대 20개 선택</span>
        </legend>
        <label>
          자산 검색
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="이름, 주소, 소유자"
            maxLength={200}
          />
        </label>
        {Object.entries(selected).map(([id, asset]) => (
          <div className="picker-selected" key={id}>
            <input type="hidden" name="asset" value={id} />
            <span>{asset.name}</span>
            <button
              type="button"
              onClick={() => {
                onDraftChange?.();
                setSelection((current) =>
                  selectWorkerAsset(current, asset, false),
                );
              }}
              aria-label={`${asset.name} 선택 해제`}
            >
              선택 해제
            </button>
          </div>
        ))}
        {!records.ready && <RecordState records={records} />}
        <div className="selection-list">
          {records.items.map((asset) => (
            <label className="selection" key={asset.id}>
              <input
                type="checkbox"
                checked={Object.hasOwn(selected, asset.id)}
                disabled={!Object.hasOwn(selected, asset.id) && count >= 20}
                onChange={(event) => {
                  const checked = event.target.checked;
                  onDraftChange?.();
                  setSelection((current) =>
                    selectWorkerAsset(current, asset, checked),
                  );
                }}
              />
              <div>
                <strong>{asset.name}</strong>
                <small>{asset.url}</small>
              </div>
            </label>
          ))}
        </div>
        <Pagination records={records} />
      </fieldset>
      <WorkerDependencyEditor
        assets={Object.values(selected)}
        dependencies={selection.dependencies}
        onChange={(dependencies) => {
          onDraftChange?.();
          setSelection((current) => ({ ...current, dependencies }));
        }}
      />
    </>
  );
}
