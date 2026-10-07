import { t as uiText, getFormatLocale } from "./i18n-core.ts";
import { useCallback } from "react";
import { useRecords, Pagination, RecordState } from "./records";
import { readNavigation, type HistoryMode, type ListPosition, type ListState } from "./navigation-state";

type Event = {
  seq: number; ts: number; level: string; message: string; detail: Record<string,unknown>;
  worker_provenance: {status:string};
  worker_source: {available:boolean; task_id:string; asset_id:string; task_name?:string; asset_name?:string; scope_url?:string; scope_revision?:number};
};
export function WorkerHistory({state,onChange,onWorker,pages}: {
  state:ListState; pages:string[];
  onChange:(changes:Partial<ListState>,mode?:HistoryMode)=>void;
  onWorker:(taskId:string,assetId:string)=>void;
}) {
  const changePosition=useCallback((position:ListPosition,mode?:HistoryMode)=>{
    const current=readNavigation(location.search,pages);
    if(current.page!=="processes" || JSON.stringify(current.list)!==JSON.stringify(state))return;
    onChange(position,mode);
  },[state,onChange,JSON.stringify(pages)]);
  const records=useRecords<Event>("worker-events",state.search,{}, {...state,onPositionChange:changePosition},"/worker-events");
  return <section className="panel worker-process worker-history" aria-label={uiText("전체 Worker 실행 기록")}>
    <label className="task-record-search">{uiText("메시지·수준·작업 ID·자산 ID로 검색")}<input aria-label={uiText("전체 Worker 실행 기록 검색")} maxLength={200} value={state.search}
        onChange={e=>onChange({search:e.target.value},"replace")} />
    </label>
    <p className="subtle">{uiText("자산 출처가 있는 실행 기록입니다. 출처 일치는 저장 메타데이터 비교이며, 검증 성공이나 자산의 안전성을 보장하지 않습니다.")}</p>
    <Pagination records={records} />
    {!records.ready?<RecordState records={records}/>:records.items.length?records.items.map(row=>
      <article className="finding-record execution-entry task-event-record" key={row.seq}>
        <strong>{row.message}</strong>
        <small>{new Date(row.ts*1000).toLocaleString(getFormatLocale())} · {row.level}</small>
        <p>{row.worker_source.task_name||row.worker_source.task_id} · {row.worker_source.asset_name||row.worker_source.asset_id}</p>
        {row.worker_source.scope_url&&<code className="observation-url">{row.worker_source.scope_url}</code>}
        <p className="subtle">{row.worker_provenance.status==="matched"?uiText("Worker 출처 메타데이터 일치"):uiText("Worker 출처 미확인")}</p>
        <button type="button" disabled={!row.worker_source.available}
          onClick={()=>onWorker(row.worker_source.task_id,row.worker_source.asset_id)}>{uiText("Worker 과정 보기")}</button>
        {!row.worker_source.available&&<p className="subtle">{uiText("저장된 원본 작업·승인 범위를 확인할 수 없습니다.")}</p>}
        <details><summary>{uiText("실행 기록 상세")}</summary><pre>{JSON.stringify(row.detail,null,2)}</pre></details>
      </article>
    ):<p className="subtle">{state.search?uiText("검색 결과가 없습니다."):uiText("Worker 실행 기록이 없습니다.")}</p>}
  </section>;
}
