import {
  readCallList,
  updateCallListQuery,
  type CallListState,
} from "./call-navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  readTaskWorker,
  updateTaskWorkerQuery,
  type TaskWorkerState,
  readTaskChat,
  updateTaskChatQuery,
  type TaskChatState,
  readTaskCollection,
  updateTaskCollectionQuery,
  type TaskCollectionKind,
  type TaskCollectionState,
  readFindingCollection,
  updateFindingCollectionQuery,
  type FindingCollectionKind,
  type FindingCollectionState,
  navigateQuery,
  readNavigation,
  updateListQuery,
  readDetail,
  detailQuery,
  type DetailState,
  type ListState,
  type HistoryMode,
} from "./navigation-state";
import { ViewScope } from "./view-action";
const changed = "aegis-navigation-changed";
function metadata() {
  const previous =
    history.state && typeof history.state === "object" ? history.state : {};
  const index =
    Number.isSafeInteger(previous.aegisRouteIndex) &&
    previous.aegisRouteIndex >= 0
      ? previous.aegisRouteIndex
      : 0;
  const maximum =
    Number.isSafeInteger(previous.aegisRouteMaximum) &&
    previous.aegisRouteMaximum >= index
      ? previous.aegisRouteMaximum
      : index;
  return { previous, index, maximum };
}
function commit(query: string, mode: HistoryMode) {
  const target = location.pathname + (query ? "?" + query : "") + location.hash;
  if (target === location.pathname + location.search + location.hash) return;
  const current = metadata();
  const index = mode === "push" ? current.index + 1 : current.index;
  const state = {
    ...current.previous,
    aegisRouteIndex: index,
    aegisRouteMaximum: mode === "push" ? index : current.maximum,
  };
  if (mode === "push") history.pushState(state, "", target);
  else history.replaceState(state, "", target);
  window.dispatchEvent(new Event(changed));
}
export function useNavigation(allowedPages: readonly string[]) {
  const allowedKey = JSON.stringify(allowedPages);
  const actionScope = useRef(new ViewScope());
  const [state, setState] = useState(() => ({
    ...readNavigation(location.search, allowedPages),
    callList: readCallList(location.search),
    detail: readDetail(location.search),
    taskChat: readTaskChat(location.search),
    taskWorker: readTaskWorker(location.search),
    taskCollections: {
      findings: readTaskCollection(location.search, "findings"),
      events: readTaskCollection(location.search, "events"),
      observations: readTaskCollection(location.search, "observations"),
    },
    findingCollections: {
      evidence: readFindingCollection(location.search, "evidence"),
      retests: readFindingCollection(location.search, "retests"),
      history: readFindingCollection(location.search, "history"),
    },
  }));
  const [position, setPosition] = useState(() => {
    const { index, maximum } = metadata();
    return { index, maximum };
  });
  const maximum = useRef(position.maximum);
  useEffect(() => {
    const sync = (event: Event) => {
      actionScope.current.invalidate();
      const current = metadata();
      maximum.current =
        event.type === changed
          ? current.maximum
          : Math.max(maximum.current, current.index);
      // Store the known forward range on this entry so reload after Back keeps Forward available.
      history.replaceState(
        {
          ...current.previous,
          aegisRouteIndex: current.index,
          aegisRouteMaximum: maximum.current,
        },
        "",
        location.href,
      );
      setPosition({ index: current.index, maximum: maximum.current });
      setState({
        ...readNavigation(location.search, allowedPages),
        callList: readCallList(location.search),
        detail: readDetail(location.search),
        taskChat: readTaskChat(location.search),
        taskWorker: readTaskWorker(location.search),
        taskCollections: {
          findings: readTaskCollection(location.search, "findings"),
          events: readTaskCollection(location.search, "events"),
          observations: readTaskCollection(location.search, "observations"),
        },
        findingCollections: {
          evidence: readFindingCollection(location.search, "evidence"),
          retests: readFindingCollection(location.search, "retests"),
          history: readFindingCollection(location.search, "history"),
        },
      });
    };
    window.addEventListener("popstate", sync);
    window.addEventListener(changed, sync);
    const current = metadata();
    history.replaceState(
      {
        ...current.previous,
        aegisRouteIndex: current.index,
        aegisRouteMaximum: current.maximum,
      },
      "",
      location.href,
    );
    commit(
      navigateQuery(location.search, allowedPages, state.page, false, true),
      "replace",
    );
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener(changed, sync);
    };
  }, [allowedKey]);
  const updateList = useCallback(
    (changes: Partial<ListState>, mode: HistoryMode = "push") => {
      commit(updateListQuery(location.search, allowedPages, changes), mode);
    },
    [allowedKey],
  );
  const navigate = useCallback(
    (page: string, fresh = false) => {
      commit(navigateQuery(location.search, allowedPages, page, fresh), "push");
    },
    [allowedKey],
  );
  const openDetail = useCallback((detail: DetailState | null) => {
    commit(detailQuery(location.search, detail), "push");
  }, []);
  const updateFindingCollection = useCallback(
    (
      kind: FindingCollectionKind,
      changes: Partial<FindingCollectionState>,
      mode: HistoryMode = "push",
    ) => {
      commit(
        updateFindingCollectionQuery(location.search, kind, changes),
        mode,
      );
    },
    [],
  );
  const updateTaskCollection = useCallback(
    (
      kind: TaskCollectionKind,
      changes: Partial<TaskCollectionState>,
      mode: HistoryMode = "push",
    ) => {
      commit(updateTaskCollectionQuery(location.search, kind, changes), mode);
    },
    [],
  );
  const updateTaskChat = useCallback(
    (changes: Partial<TaskChatState>, mode: HistoryMode = "push") => {
      commit(updateTaskChatQuery(location.search, changes), mode);
    },
    [],
  );
  const updateTaskWorker = useCallback(
    (changes: Partial<TaskWorkerState>, mode: HistoryMode = "push") => {
      commit(updateTaskWorkerQuery(location.search, changes), mode);
    }, [],
  );
  const updateCallList = useCallback(
    (changes: Partial<CallListState>, mode: HistoryMode = "push") => {
      commit(updateCallListQuery(location.search, changes), mode);
    },
    [],
  );
  return {
    ...state,
    updateCallList,
    captureActionView: () => actionScope.current.capture(),
    invalidateActionView: () => actionScope.current.invalidate(),
    updateTaskChat,
    updateTaskWorker,
    updateTaskCollection,
    updateFindingCollection,
    updateList,
    navigate,
    openDetail,
    canBack: position.index > 0,
    canForward: position.index < position.maximum,
    back: () => {
      if (metadata().index > 0) history.back();
    },
    forward: () => {
      const value = metadata();
      if (value.index < value.maximum) history.forward();
    },
  };
}
