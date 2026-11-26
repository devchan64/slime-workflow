import React, {useEffect,useId,useRef,useState} from "react";
import {formatCleanupResult,validCleanupResult} from "./formatCleanupResult.mjs";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus,visibleFocusTarget} from "./restoreLostFocus.mjs";

export default function HistoryCleanup({service,job,state,onDeleted,allowSelected=true}) {
  const [review,setReview]=useState(null),[ack,setAck]=useState(false);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const helpId=useId();
  const previewRequest=useRef(null),operationPending=useRef(false);
  const reviewRef=useRef(null),reviewOrigin=useRef(null),restoreErrorFocus=useRef(false),containerRef=useRef(null);
  useEffect(()=>()=>previewRequest.current?.abort(),[]);
  useEffect(()=>{if(review && (document.activeElement===reviewOrigin.current || document.activeElement===document.body))reviewRef.current?.focus();},[review]);
  useEffect(()=>{if(busy || !notice || !restoreErrorFocus.current)return;restoreErrorFocus.current=false;const frame=requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(reviewOrigin.current)));return ()=>cancelAnimationFrame(frame);},[busy,notice]);
  const eligible=["completed","failed","cancelled","paused"].includes(state);
  async function perform(operation) {
    if(operationPending.current)return;
    operationPending.current=true;const focused=containerRef.current?.contains(document.activeElement);
    setBusy(true);setNotice("");
    try {await operation();} catch(error){restoreErrorFocus.current=Boolean(focused);setNotice(requestErrorMessage(error));}
    finally{operationPending.current=false;setBusy(false);}
  }
  function reset() {setReview(null);setAck(false);}
  async function readPreview() {
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try {
      const preview=await untilAborted(managementCommand(service,"history-reset-preview",{},{signal:controller.signal}),controller.signal);
      if(!preview || typeof preview!=="object" || !Array.isArray(preview.jobs) || !Array.isArray(preview.blocked_jobs) || !Number.isSafeInteger(preview.job_count) || preview.job_count!==preview.jobs.length || typeof preview.can_reset!=="boolean" || typeof preview.scope!=="string" || typeof preview.notice!=="string")
        throw new Error("삭제 대상 조회 응답을 확인할 수 없습니다. 다시 조회하세요.");
      return preview;
    } catch(error) {if(timedOut)throw new Error("삭제 대상 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);if(previewRequest.current===controller)previewRequest.current=null;}
  }
  async function inspectAll() {
    reset();
    const preview=await readPreview();
    setReview({all:true,preview});
  }
  async function requestDeletion(command,payload){
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{return await untilAborted(managementCommand(service,command,payload,{signal:controller.signal}),controller.signal);}
    catch(error){if(timedOut)throw new Error("삭제 응답 시간이 초과됐습니다.");throw error;}
    finally{clearTimeout(timeout);}
  }
  async function confirm() {
    if(!review || !ack)return;
    const target=review;
    reset();
    let result,deleteStarted=false;
    try {
    if(target.all) {
      const current=await readPreview();
      if(!current.can_reset || JSON.stringify(current.jobs)!==JSON.stringify(target.preview.jobs))
        throw new Error("삭제 대상이 변경되었습니다. 다시 조회하세요.");
      deleteStarted=true;result=await requestDeletion("history-reset",{action:"reset",expected_jobs:target.preview.jobs});
    } else {
      if(target.id!==job || !eligible)throw new Error("선택 작업의 상태가 변경되었습니다.");
      deleteStarted=true;result=await requestDeletion("history-delete",{id:target.id});
    }
    if(!validCleanupResult(result,!target.all))throw new Error("삭제 응답을 확인할 수 없습니다.");
    onDeleted(formatCleanupResult(result));
    } catch(error) {throw new Error(requestErrorMessage(error)+(deleteStarted ? " · 삭제 결과가 불확실할 수 있습니다. 다시 요청하기 전에 이력을 확인하세요." : " · 삭제 요청은 전송하지 않았습니다."));}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);reset();
    if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body && reviewOrigin.current?.isConnected)reviewOrigin.current.focus();});
  }
  return <details ref={containerRef}><summary>생성 이력 정리</summary>
    <fieldset disabled={busy}>
      {allowSelected && <button type="button" aria-describedby={!job || !eligible ? helpId : undefined} disabled={!job || !eligible} onClick={event=>{reviewOrigin.current=event.currentTarget;setAck(false);setReview({id:job});}}>선택 이력 삭제 검토</button>}
      {allowSelected && (!job || !eligible) && <p id={helpId}>{!job ? "삭제하려면 생성 이력에서 작업 결과를 조회하세요." : !state || state==="unknown" ? "삭제하려면 작업 상태를 다시 확인하세요." : state==="canceled" ? "이 취소 상태는 현재 이력 정리에서 지원하지 않아 삭제할 수 없습니다." : "종료된 작업만 삭제할 수 있습니다. 작업이 종료된 후 다시 확인하세요."}</p>}
      <button type="button" onClick={event=>{reviewOrigin.current=event.currentTarget;perform(inspectAll);}}>전체 이력 삭제 대상 조회</button>
      {review && <section ref={reviewRef} tabIndex={-1} aria-label="이력 삭제 확인" className="history-confirmation">
        <p>{review.all ? service+" · 전체 삭제 대상 "+review.preview.job_count+"건" : "선택 작업 · "+review.id}</p>
        <p>{review.all ? review.preview.scope : "작업 폴더의 입력 사본·결과·로그와 실행 기록을 삭제합니다."}</p>
        {review.all && <p>{review.preview.notice} · 삭제 제한 작업 {review.preview.blocked_jobs.length}건</p>}
        <label><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>삭제 후 복구할 수 없음을 확인했습니다.</label>
        <div className="choice-buttons"><button type="button" onClick={cancelReview}>삭제 취소</button>
        <button type="button" disabled={!ack || (review.all ? !review.preview.can_reset : !eligible)} onClick={()=>perform(confirm)}>확인한 대상 삭제</button></div>
      </section>}
    </fieldset>{busy && <p role="status">이력 정리 요청을 처리하고 있습니다.</p>}<p role="status">{notice}</p>
  </details>;
}
