import { test } from "node:test";
import assert from "node:assert/strict";
import { detailQuery, navigateQuery, readTaskWorker, updateTaskWorkerQuery, updateTaskCollectionQuery, readNavigation, updateListQuery } from "../src/navigation-state.ts";

const source = "page=tasks&tasks_q=source&tasks_offset=25&detail=task&detail_id=task-one";
const empty = {search:"",offset:0,snapshot:null};
function bookmark() {
  let query = updateTaskWorkerQuery(source, {assetId:"asset-one"});
  query = updateTaskWorkerQuery(query, {expanded:true,events:{...empty,search:"한글 & ?"}});
  query = updateTaskWorkerQuery(query, {observations:{...empty,search:"link"}});
  return updateTaskWorkerQuery(query, {events:{search:"한글 & ?",offset:25,snapshot:123},
    observations:{search:"link",offset:0,snapshot:456}});
}
test("Worker bookmark preserves independent searches, snapshot domains and surrounding task lists", () => {
  const query = updateTaskCollectionQuery(bookmark(),"events",{search:"task-wide"});
  assert.deepEqual(readTaskWorker(query),{assetId:"asset-one",expanded:true,
    events:{search:"한글 & ?",offset:25,snapshot:123},observations:{search:"link",offset:0,snapshot:456}});
  assert.equal(new URLSearchParams(query).get("task_events_q"),"task-wide");
  assert.equal(new URLSearchParams(query).get("tasks_offset"),"25");
  assert.deepEqual(readTaskWorker(navigateQuery(query,["tasks"],"tasks",false,true)),readTaskWorker(query));
});
test("Worker search resets only that collection while changing asset clears both positions and expansion", () => {
  const old = bookmark();
  const searched = updateTaskWorkerQuery(old,{events:{search:"new",offset:25,snapshot:123}});
  assert.deepEqual(readTaskWorker(searched).events,{search:"new",offset:0,snapshot:null});
  assert.deepEqual(readTaskWorker(searched).observations,readTaskWorker(old).observations);
  const changed = updateTaskWorkerQuery(old,{assetId:"asset-two",expanded:true});
  assert.deepEqual(readTaskWorker(changed),{assetId:"asset-two",expanded:false,events:empty,observations:empty});
  assert.equal(readTaskWorker(old).events.offset,25);
});
test("Worker state is removed when closing, changing task, switching detail kind or page", () => {
  for (const detail of [null,{kind:"task" as const,id:"two"},{kind:"finding" as const,id:"finding-one"}]) {
    const query = detailQuery(bookmark(),detail);
    assert.equal([...new URLSearchParams(query).keys()].some(k=>k.startsWith("task_worker_")),false);
    assert.deepEqual(readTaskWorker(query),{assetId:"",expanded:false,events:empty,observations:empty});
  }
  assert.equal(new URLSearchParams(navigateQuery(bookmark(),["tasks","assets"],"assets")).has("task_worker_asset"),false);
  assert.equal(updateTaskWorkerQuery("page=tasks",{assetId:"no-task",expanded:true}),"page=tasks");
});
test("Malformed bookmark IDs and unsafe integer positions never become API positions", () => {
  const query=detailQuery(source+"&task_worker_asset=asset-one&task_worker_open=true&task_worker_events_offset=49&task_worker_events_snapshot=1e5&task_worker_observations_offset=-25",{kind:"task",id:"task-one"});
  assert.deepEqual(readTaskWorker(query).events,{search:"",offset:25,snapshot:null});
  assert.deepEqual(readTaskWorker(query).observations,empty);
  const bounded=updateTaskWorkerQuery(query,{events:{search:"x".repeat(199)+"😀",offset:Infinity,snapshot:NaN}});
  assert.deepEqual(readTaskWorker(bounded).events,{search:"x".repeat(199),offset:0,snapshot:null});
  for (const assetId of ["../../other","x".repeat(81),"<script>"]) {
    const bad=updateTaskWorkerQuery(bookmark(),{assetId,expanded:true});
    assert.deepEqual(readTaskWorker(bad),{assetId:"",expanded:false,events:empty,observations:empty});
    assert.equal(new URLSearchParams(bad).has("task_worker_asset"),false);
  }
});

test("workspace process search position survives opening a Worker source and resets on search", () => {
  const source="page=processes&processes_q=Owned&processes_offset=25&processes_snapshot=91";
  let query=detailQuery(source,{kind:"task",id:"one"});
  query=updateTaskWorkerQuery(query,{assetId:"asset-one"});
  query=updateTaskWorkerQuery(query,{expanded:true});
  const closed=detailQuery(query,null);
  assert.equal(new URLSearchParams(closed).get("processes_offset"),"25");
  assert.equal(new URLSearchParams(closed).get("processes_snapshot"),"91");
  assert.equal(new URLSearchParams(closed).get("processes_q"),"Owned");
  assert.equal(readTaskWorker(query).expanded,true);
  assert.equal(readTaskWorker(closed).assetId,"");
  const searched=updateListQuery(closed,["processes"],{search:"new"});
  assert.equal(readNavigation(searched,["processes"]).list.offset,0);
  assert.equal(readNavigation(searched,["processes"]).list.snapshot,null);
});
