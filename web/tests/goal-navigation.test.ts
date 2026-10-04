import { test } from "node:test";
import assert from "node:assert/strict";
import { detailQuery, navigateQuery, readTaskGoal, updateTaskGoalQuery, goalCollectionMatches,
  updateTaskWorkerQuery, readTaskWorker } from "../src/navigation-state.ts";
const source="page=tasks&tasks_q=원본&tasks_offset=25&detail=task&detail_id=task-one";
const row={expanded:true,search:"",offset:0,snapshot:null};
function bookmark(){
  let query=updateTaskGoalQuery(source,{expanded:true,objectives:{g1:{...row,search:"한글 & ?"},g2:{...row,search:"cookie"}}});
  return updateTaskGoalQuery(query,{objectives:{g1:{...row,search:"한글 & ?",offset:25,snapshot:123},g2:{...row,search:"cookie",offset:50,snapshot:456}}});
}
test("goal bookmark restores multiple independent objective searches and evidence snapshots",()=>{
  const query=updateTaskWorkerQuery(bookmark(),{assetId:"asset-one"});
  assert.deepEqual(readTaskGoal(query),{expanded:true,objectives:{
    g1:{expanded:true,search:"한글 & ?",offset:25,snapshot:123},
    g2:{expanded:true,search:"cookie",offset:50,snapshot:456}}});
  assert.equal(readTaskWorker(query).assetId,"asset-one");
  assert.equal(new URLSearchParams(query).get("tasks_offset"),"25");
  assert.deepEqual(readTaskGoal(navigateQuery(query,["tasks"],"tasks",false,true)),readTaskGoal(query));
});
test("new objective search clears only that objective position; closing discards hidden positions",()=>{
  const old=bookmark();
  const searched=updateTaskGoalQuery(old,{objectives:{g1:{...row,search:"new",offset:25,snapshot:123}}});
  assert.deepEqual(readTaskGoal(searched).objectives.g1,{...row,search:"new"});
  assert.deepEqual(readTaskGoal(searched).objectives.g2,readTaskGoal(old).objectives.g2);
  const closed=updateTaskGoalQuery(old,{objectives:{g1:{...row,expanded:false}}});
  assert.equal(readTaskGoal(closed).objectives.g1,undefined);
  assert.deepEqual(readTaskGoal(closed).objectives.g2,readTaskGoal(old).objectives.g2);
  assert.deepEqual(readTaskGoal(updateTaskGoalQuery(old,{expanded:false})),{expanded:false,objectives:{}});
});
test("leaving task removes goal evidence state and Back's old query stays restorable",()=>{
  const old=bookmark();
  for(const detail of [null,{kind:"task" as const,id:"other"},{kind:"finding" as const,id:"finding-one"}]){
    const query=detailQuery(old,detail);
    assert.deepEqual(readTaskGoal(query),{expanded:false,objectives:{}});
    assert.equal([...new URLSearchParams(query).keys()].some(k=>k.startsWith("task_goal_")),false);
  }
  assert.deepEqual(readTaskGoal(navigateQuery(old,["tasks","assets"],"assets")),{expanded:false,objectives:{}});
  assert.equal(readTaskGoal(old).objectives.g1.offset,25);
  assert.equal(updateTaskGoalQuery("page=tasks",{expanded:true}),"page=tasks");
});
test("untrusted goal bookmark is bounded, canonical and cannot request unknown objectives",()=>{
  const raw=source+"&task_goal_open=true&task_goal_g1_open=true&task_goal_g1_offset=49&task_goal_g1_snapshot=1e5&task_goal_g99_open=true&task_goal_unknown=x";
  const normalized=detailQuery(raw,{kind:"task",id:"task-one"});
  assert.deepEqual(readTaskGoal(normalized).objectives.g1,{...row,offset:25});
  assert.equal(new URLSearchParams(normalized).has("task_goal_g99_open"),false);
  assert.equal(new URLSearchParams(normalized).has("task_goal_unknown"),false);
  const bounded=updateTaskGoalQuery(bookmark(),{objectives:{g1:{...row,search:"x".repeat(199)+"😀",offset:Infinity,snapshot:NaN},g12:{...row,offset:-25,snapshot:9007199254740992}}});
  assert.deepEqual(readTaskGoal(bounded).objectives.g1,{...row,search:"x".repeat(199)});
  assert.deepEqual(readTaskGoal(bounded).objectives.g12,row);
  assert.equal(detailQuery(normalized,{kind:"task",id:"task-one"}),normalized);
});
test("late objective response cannot move another task, a closed objective or a newer search",()=>{
  const old=bookmark(), expected=readTaskGoal(old).objectives.g1;
  assert.equal(goalCollectionMatches(old,"task-one","g1",expected),true);
  assert.equal(goalCollectionMatches(old,"other","g1",expected),false);
  assert.equal(goalCollectionMatches(old,"task-one","g2",expected),false);
  const searched=updateTaskGoalQuery(old,{objectives:{g1:{...row,search:"new"}}});
  assert.equal(goalCollectionMatches(searched,"task-one","g1",expected),false);
  assert.equal(goalCollectionMatches(detailQuery(old,{kind:"finding",id:"finding-one"}),"task-one","g1",expected),false);
  assert.equal(goalCollectionMatches(updateTaskGoalQuery(old,{expanded:false}),"task-one","g1",expected),false);
});
