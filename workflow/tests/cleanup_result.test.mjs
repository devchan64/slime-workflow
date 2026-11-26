import test from "node:test";
import assert from "node:assert/strict";
import {validCleanupResult} from "../../gui/formatCleanupResult.mjs";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {untilAborted} from "../../gui/managementCommand.js";
import {requestErrorMessage} from "../../gui/requestError.mjs";
import {restoreLostFocus} from "../../gui/restoreLostFocus.mjs";

test("삭제 결과는 확인된 상태와 유효한 건수·용량이 있어야 한다",()=>{
  const valid={status:"cleared",deleted_jobs:1,deleted_bytes:0};
  assert.equal(validCleanupResult(valid,true),true);
  for(const invalid of [null,{}, {...valid,status:"failed"}, {...valid,deleted_jobs:0},
    {...valid,deleted_bytes:-1}, {...valid,deleted_bytes:NaN}, {...valid,skipped_jobs:{}}])
    assert.equal(validCleanupResult(invalid,true),false);
  assert.equal(validCleanupResult({...valid,deleted_jobs:0},false),true);
});

test("이력 삭제 검토 취소는 사라진 초점만 원래 버튼으로 복구한다",()=>{
  const source=readFileSync(new URL("../../gui/HistoryCleanup.jsx",import.meta.url),"utf8");
  const start=source.indexOf("  function cancelReview()"),end=source.indexOf("  return <details",start);
  for(const scenario of ["lost","moved","outside"]){
    const body={},inside={},other={},document={body,activeElement:scenario==="outside" ? other : inside};let frame,focused=0;
    const context=vm.createContext({document,reviewRef:{current:{contains:element=>element===inside}},reviewOrigin:{current:{isConnected:true,focus:()=>focused++}},reset:()=>{},requestAnimationFrame:fn=>frame=fn});
    vm.runInContext(source.slice(start,end),context);context.cancelReview();
    if(frame){document.activeElement=scenario==="moved" ? other : body;frame();}
    assert.equal(focused,scenario==="lost" ? 1 : 0);
  }
});

test("삭제 응답 지연은 중복을 막고 불확실한 결과의 이력 확인을 안내한다",async()=>{
  const source=readFileSync(new URL("../../gui/HistoryCleanup.jsx",import.meta.url),"utf8");
  const start=source.indexOf("  async function perform("),end=source.indexOf("  function cancelReview()",start);
  let timer,notice='',busy=false,calls=0,deleted=0;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,operationPending:{current:false},restoreErrorFocus:{current:false},containerRef:{current:null},document:{activeElement:null},review:{id:'job'},ack:true,job:'job',eligible:true,service:'test',setBusy:value=>busy=value,setNotice:value=>notice=value,setReview:()=>{},setAck:()=>{},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},managementCommand:()=>{calls++;return new Promise(()=>{});},validCleanupResult:()=>true,formatCleanupResult:()=>'',onDeleted:()=>deleted++});
  vm.runInContext(source.slice(start,end),context);
  const first=context.perform(context.confirm);await context.perform(context.confirm);assert.equal(calls,1);assert.equal(busy,true);
  timer();await first;assert.equal(busy,false);assert.equal(deleted,0);assert.match(notice,/시간이 초과/);assert.match(notice,/불확실.*이력을 확인/);
});

test('삭제 대상 조회 실패는 사라진 초점만 원래 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/HistoryCleanup.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !notice \|\| !restoreErrorFocus\.current\).*?\},\[busy,notice\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},button={isConnected:true,focus:()=>focused++},document={body,activeElement:moved?{}:body};
  const context=vm.createContext({busy:false,notice:'오류',restoreErrorFocus:{current:true},reviewOrigin:{current:button},document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);
 }
});
