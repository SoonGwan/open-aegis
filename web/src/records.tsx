import { useEffect, useRef, useState } from "react";
import { api } from "./api";

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
) {
  const key = JSON.stringify([kind, search, filters]);
  const [position, setPosition] = useState({
    key,
    offset: 0,
    snapshot: null as number | null,
  });
  const current =
    position.key === key ? position : { key, offset: 0, snapshot: null };
  const [result, setResult] = useState<{ key: string; data: Result<T> }>({
    key: "",
    data: empty,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  const requestKey = `${key}:${current.offset}:${current.snapshot}`;
  useEffect(() => {
    const update = () => setRevision((value) => value + 1);
    const timer = setInterval(update, 4000);
    window.addEventListener("aegis-records-changed", update);
    return () => {
      clearInterval(timer);
      window.removeEventListener("aegis-records-changed", update);
    };
  }, []);
  useEffect(() => {
    const requestSequence = ++sequence.current;
    if (!kind) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
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
        `/records/${kind}?${query}`,
        "GET",
        undefined,
        controller.signal,
      )
        .then((data) => {
          if (sequence.current !== requestSequence || controller.signal.aborted)
            return;
          if (data.total > 0 && current.offset >= data.total) {
            setPosition({
              key,
              offset: Math.floor((data.total - 1) / 25) * 25,
              snapshot: data.snapshot,
            });
          } else setResult({ key: requestKey, data });
        })
        .catch((error) => {
          if (
            !controller.signal.aborted &&
            sequence.current === requestSequence
          )
            setError(error.message);
        })
        .finally(() => {
          if (
            !controller.signal.aborted &&
            sequence.current === requestSequence
          )
            setLoading(false);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [requestKey, revision]);
  const data = result.key === requestKey ? result.data : (empty as Result<T>);
  return {
    ...data,
    loading,
    error,
    next: () =>
      setPosition({
        key,
        offset: current.offset + 25,
        snapshot: data.snapshot,
      }),
    previous: () =>
      setPosition({
        key,
        offset: Math.max(0, current.offset - 25),
        snapshot: data.snapshot,
      }),
    reload: () => {
      setPosition({ key, offset: 0, snapshot: null });
      setRevision((value) => value + 1);
    },
  };
}

export function Pagination({
  records,
}: {
  records: ReturnType<typeof useRecords>;
}) {
  return (
    <nav className="pagination" aria-label="목록 페이지">
      <span aria-live="polite">
        {records.loading
          ? "불러오는 중"
          : records.total
            ? `${records.offset + 1}–${records.offset + records.items.length} / 전체 ${records.total.toLocaleString()}개`
            : "검색 결과 0개"}
      </span>
      {records.error && <span role="alert">{records.error}</span>}
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

type PickerAsset = { id: string; name: string; url: string };
export function AssetPicker({ initialId }: { initialId: string | null }) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>(
    initialId ? { [initialId]: initialId } : {},
  );
  const records = useRecords<PickerAsset>("assets", search, {
    archived: "false",
  });
  const count = Object.keys(selected).length;
  return (
    <fieldset>
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
      {Object.entries(selected).map(([id, name]) => (
        <div className="picker-selected" key={id}>
          <input type="hidden" name="asset" value={id} />
          <span>{name}</span>
          <button
            type="button"
            onClick={() =>
              setSelected((current) => {
                const next = { ...current };
                delete next[id];
                return next;
              })
            }
            aria-label={`${name} 선택 해제`}
          >
            선택 해제
          </button>
        </div>
      ))}
      <div className="selection-list">
        {records.items.map((asset) => (
          <label className="selection" key={asset.id}>
            <input
              type="checkbox"
              checked={asset.id in selected}
              disabled={!(asset.id in selected) && count >= 20}
              onChange={(event) =>
                setSelected((current) => {
                  const next = { ...current };
                  if (event.target.checked) next[asset.id] = asset.name;
                  else delete next[asset.id];
                  return next;
                })
              }
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
  );
}
