import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {generationResumeCommand} from "./generationResumeCommand.mjs";
import {validateGenerationControlResponse} from "./generationControlResponse.mjs";
import {requestErrorMessage} from "./requestError.mjs";

export default function GeneratorJobControls(props) {
  return <GeneratorJobControlsForJob key={props.service+"/"+props.id} {...props}/>;
}

function GeneratorJobControlsForJob({service,id,state,refresh,showLog=true,showActions=true,showUnavailable=false,resumeEnabled=true,disabled=false,renderPriority=null,onInteractionChange}) {
  const [review,setReview]=useState(null);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [log,setLog]=useState(null);
  const logRequest=useRef(null),previewRequest=useRef(null),controlsRef=useRef(null),logButton=useRef(null),reviewRef=useRef(null),reviewTrigger=useRef(null),restorePreviewFocus=useRef(false),restoreLogFocus=useRef(false);
  useEffect(()=>()=>{logRequest.current?.abort();previewRequest.current?.abort();},[]);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(review));return ()=>onInteractionChange?.(false);},[busy,review,onInteractionChange]);
  useEffect(()=>{if(review && (document.activeElement===document.body || document.activeElement===reviewTrigger.current))reviewRef.current?.focus();},[review]);
  useEffect(()=>{if(!busy && restorePreviewFocus.current){restorePreviewFocus.current=false;if(notice && !review && document.activeElement===document.body && reviewTrigger.current?.isConnected && !reviewTrigger.current.disabled)reviewTrigger.current.focus();}},[busy,notice,review]);
  useEffect(()=>{if(!busy && restoreLogFocus.current){restoreLogFocus.current=false;if(document.activeElement===document.body && logButton.current?.isConnected && !logButton.current.disabled)logButton.current.focus();}},[busy,log,notice]);
  const resumeCommand=generationResumeCommand(service);
  const resumeReasonId=useId(),stopReasonId=useId(),lockedId=useId(),confirmReasonId=useId();
  const lockedReason=busy ? "작업 제어 요청을 처리하고 있습니다." : review ? "열린 작업 제어 검토를 마치거나 취소하세요." : disabled ? "다른 작업 검토를 마치거나 취소하세요." : "";
  const canResume=resumeEnabled && Boolean(resumeCommand) && ["failed","cancelled","paused"].includes(state);
  const canStop=["queued","running","paused"].includes(state);
  const reviewOutdated=Boolean(review && review.state!==state);
  const resumeReason=!state ? "현재 작업 상태를 확인하세요." : !resumeEnabled ? "이 생성기의 재개는 보류 중입니다." : !resumeCommand ? "이 생성기는 검토 기반 재개를 제공하지 않습니다." : "실패·중단된 작업만 재개할 수 있습니다.";
  const stopReason=!state ? "현재 작업 상태를 확인하세요." : "대기·실행·검수 대기 중인 작업만 중지할 수 있습니다.";
  async function perform(action) {
    setBusy(true);setNotice("");
    try {await action();}
    catch(problem){setNotice(requestErrorMessage(problem));}
    finally{setBusy(false);}
  }
  async function prepareResume() {
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    let checked;
    try{checked=await untilAborted(managementCommand(service,"resume-preview",{id},{signal:controller.signal}),controller.signal);}
    catch(problem){if(timedOut)throw new Error("재개 검토 조회 시간이 초과됐습니다. 다시 확인하세요.");throw problem;}
    finally{clearTimeout(timer);if(previewRequest.current===controller)previewRequest.current=null;}
    if(checked.id!==id || checked.service!==service || checked.status!==state ||
        !/^[a-f0-9]{64}$/.test(checked.expected_resume_fingerprint))
      throw new Error("검토한 작업과 상태가 일치하지 않습니다. 상태를 갱신하세요.");
    if(checked.resume_availability && checked.resume_availability!=="available"){
      const reasons={download_running:"모델 다운로드가 진행 중입니다.",other_preparation:"다른 모델 준비 작업이 진행 중입니다."};
      throw new Error(reasons[checked.resume_availability] || "재개 가능 상태를 확인할 수 없습니다.");
    }
    const payload={id,expected_resume_fingerprint:checked.expected_resume_fingerprint};
    if(service==="kimodo"){
      if(checked.keyframe_fingerprint!==null && !/^[a-f0-9]{64}$/.test(checked.keyframe_fingerprint))
        throw new Error("키프레임 확인값을 확인할 수 없습니다.");
      if(checked.resume_availability!=="available")throw new Error("재개 가능 상태를 확인할 수 없습니다.");
      payload.keyframe_fingerprint=checked.keyframe_fingerprint;
    }
    setReview({command:"resume",payload,state});
  }
  async function confirm() {
    const {command,payload}=review;
    setReview(null);
    try {
      const response=await managementCommand(service,command==="resume"?resumeCommand:command,payload);
      if(!validateGenerationControlResponse(command,id,response))
        throw new Error("응답에서 요청 접수를 확인할 수 없습니다. 다시 요청하기 전에 이력과 작업 상태를 확인하세요.");
      setNotice(command==="resume"?"재개를 접수했습니다. 실제 실행 상태를 확인하세요.":"중지를 요청했습니다. 실제 종료 상태를 확인하세요.");
    } catch(problem) {
      throw new Error(requestErrorMessage(problem)+" · 결과가 불확실할 수 있습니다. 다시 요청하기 전에 이력과 작업 상태를 확인하세요.");
    } finally {
      refresh();
    }
  }
  return <section ref={controlsRef} tabIndex={-1} className={showUnavailable ? "history-job-actions ui-focus-target" : "ui-focus-target"} aria-label="작업 제어">
    {showLog && <button ref={logButton} type="button" disabled={busy} aria-describedby={busy ? lockedId : undefined} aria-expanded={log!==null} onClick={event=>{if(log!==null){setLog(null);return;}restoreLogFocus.current=document.activeElement===event.currentTarget;perform(async()=>{
      const controller=new AbortController();logRequest.current=controller;let timedOut=false;
      const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try{
        const result=await untilAborted(managementCommand(service,"logs",{id},{signal:controller.signal}),controller.signal);
        if(!result || typeof result!=="object" || (result.log!=null && typeof result.log!=="string"))throw new Error("작업 로그 응답 형식을 확인할 수 없습니다.");
        setLog(result.log || "기록된 로그가 없습니다.");
      }catch(error){if(timedOut)throw new Error("작업 로그 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
      finally{clearTimeout(timer);if(logRequest.current===controller)logRequest.current=null;}
    });}}>{log!==null ? "작업 로그 닫기" : "작업 로그 조회"}</button>}
    {log!==null && <pre className="generator-job-log" tabIndex={0} aria-label="작업 로그">{log}</pre>}
    {showActions && (!review || showUnavailable) && (showUnavailable || ["failed","cancelled","paused"].includes(state)) &&
      <button className={showUnavailable ? "history-action-resume" : undefined} type="button" disabled={disabled || busy || Boolean(review) || !canResume} aria-describedby={lockedReason ? lockedId : !canResume ? resumeReasonId : undefined} onClick={event=>{reviewTrigger.current=event.currentTarget;restorePreviewFocus.current=document.activeElement===event.currentTarget;perform(prepareResume);}}>생성 재개 검토</button>}
    {showActions && renderPriority?.(disabled || busy || Boolean(review))}
    {showActions && (!review || showUnavailable) && (showUnavailable || ["queued","running","paused"].includes(state)) &&
      <button className={showUnavailable ? "history-action-stop" : undefined} type="button" disabled={disabled || busy || Boolean(review) || !canStop} aria-describedby={lockedReason ? lockedId : !canStop ? stopReasonId : undefined} onClick={event=>{reviewTrigger.current=event.currentTarget;setReview({command:"cancel",payload:{id},state});}}>작업 중지 검토</button>}
    {lockedReason && <p id={lockedId} className={showUnavailable ? "history-action-detail" : undefined}>{lockedReason}</p>}
    {showActions && !review && !canResume && (showUnavailable || ["failed","cancelled","paused"].includes(state)) &&
      <p className={showUnavailable ? "history-action-detail" : undefined} id={resumeReasonId}>{resumeReason}</p>}
    {showActions && !review && !canStop && showUnavailable &&
      <p className="history-action-detail" id={stopReasonId}>{stopReason}</p>}
    {showActions && review && <section ref={reviewRef} tabIndex={-1} aria-label="작업 제어 확인" className={showUnavailable ? "history-action-detail ui-focus-target" : "ui-focus-target"}><p>{id} · {review.command==="resume"?"저장된 입력으로 GPU 대기열에 다시 등록합니다.":"선택한 작업에 중지를 요청합니다."}</p>
      {(reviewOutdated || busy || disabled) && <p id={confirmReasonId} role="status">{busy ? "작업 제어 요청을 처리하고 있습니다." : reviewOutdated ? "검토한 뒤 작업 상태가 변경됐습니다. 취소하고 현재 상태에서 다시 검토하세요." : "다른 작업 검토를 마치거나 취소하세요."}</p>}
      <button type="button" disabled={busy} onClick={event=>{const focused=document.activeElement===event.currentTarget;setReview(null);if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body){if(reviewTrigger.current?.isConnected && !reviewTrigger.current.disabled)reviewTrigger.current.focus();else controlsRef.current?.focus();}});}}>취소</button>
      <button type="button" disabled={disabled || busy || reviewOutdated} aria-describedby={disabled || busy || reviewOutdated ? confirmReasonId : undefined} onClick={()=>perform(confirm)}>{review.command==="resume"?"확인 후 재개":"확인 후 중지"}</button>
    </section>}
    <p className={showUnavailable ? "history-action-detail" : undefined} role="status">{busy ? "작업 제어 요청을 처리하고 있습니다." : notice}</p>
  </section>;
}
