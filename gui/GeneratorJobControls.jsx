import React, {useEffect,useId,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {generationResumeCommand} from "./generationResumeCommand.mjs";
import {validateGenerationControlResponse} from "./generationControlResponse.mjs";

export default function GeneratorJobControls({service,id,state,refresh,showLog=true,showActions=true,showUnavailable=false,resumeEnabled=true,disabled=false,renderPriority=null,onInteractionChange}) {
  const [review,setReview]=useState(null);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [log,setLog]=useState(null);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(review));return ()=>onInteractionChange?.(false);},[busy,review,onInteractionChange]);
  const resumeCommand=generationResumeCommand(service);
  const reasonId=useId();
  const canResume=resumeEnabled && Boolean(resumeCommand) && ["failed","cancelled","paused"].includes(state);
  const canStop=["queued","running","paused"].includes(state);
  const resumeReason=!state ? "현재 작업 상태를 확인하세요." : !resumeEnabled ? "이 생성기의 재개는 보류 중입니다." : !resumeCommand ? "이 생성기는 검토 기반 재개를 제공하지 않습니다." : "실패·중단된 작업만 재개할 수 있습니다.";
  const stopReason=!state ? "현재 작업 상태를 확인하세요." : "대기·실행·검수 대기 중인 작업만 중지할 수 있습니다.";
  async function perform(action) {
    setBusy(true);setNotice("");
    try {await action();}
    catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function prepareResume() {
    const checked=await managementCommand(service,"resume-preview",{id});
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
    setReview({command:"resume",payload});
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
      throw new Error(problem.message+" · 결과가 불확실할 수 있습니다. 다시 요청하기 전에 이력과 작업 상태를 확인하세요.");
    } finally {
      refresh();
    }
  }
  return <section className={showUnavailable ? "history-job-actions" : undefined} aria-label="작업 제어">
    {showLog && <button type="button" disabled={busy} onClick={()=>perform(async()=>{
      const result=await managementCommand(service,"logs",{id});
      setLog(result.log || "기록된 로그가 없습니다.");
    })}>작업 로그 조회</button>}
    {log!==null && <pre>{log}</pre>}
    {showActions && (!review || showUnavailable) && (showUnavailable || ["failed","cancelled","paused"].includes(state)) &&
      <button className={showUnavailable ? "history-action-resume" : undefined} type="button" disabled={disabled || busy || Boolean(review) || !canResume} aria-describedby={!canResume ? reasonId : undefined} onClick={()=>perform(prepareResume)}>생성 재개 검토</button>}
    {showActions && renderPriority?.(disabled || busy || Boolean(review))}
    {showActions && (!review || showUnavailable) && (showUnavailable || ["queued","running","paused"].includes(state)) &&
      <button className={showUnavailable ? "history-action-stop" : undefined} type="button" disabled={disabled || busy || Boolean(review) || !canStop} aria-describedby={!canStop ? reasonId : undefined} onClick={()=>setReview({command:"cancel",payload:{id}})}>작업 중지 검토</button>}
    {showActions && !review && ((!canResume && showUnavailable) || (!canStop && showUnavailable) || (!resumeCommand && ["failed","cancelled","paused"].includes(state))) &&
      <p className={showUnavailable ? "history-action-detail" : undefined} id={reasonId}>{[!canResume && resumeReason,!canStop && stopReason].filter(Boolean).filter((value,index,array)=>array.indexOf(value)===index).join(" ")}</p>}
    {showActions && review && <section className={showUnavailable ? "history-action-detail" : undefined}><p>{id} · {review.command==="resume"?"저장된 입력으로 GPU 대기열에 다시 등록합니다.":"선택한 작업에 중지를 요청합니다."}</p>
      <button type="button" disabled={disabled || busy} onClick={()=>setReview(null)}>취소</button>
      <button type="button" disabled={disabled || busy} onClick={()=>perform(confirm)}>{review.command==="resume"?"확인 후 재개":"확인 후 중지"}</button>
    </section>}
    <p className={showUnavailable ? "history-action-detail" : undefined} role="status">{notice}</p>
  </section>;
}
