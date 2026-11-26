import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {executeGpuHandoffCommand} from "./readGpuHandoffStatus.mjs";
import {handoffUncertaintyKey,handoffSessionStorage,readHandoffUncertainty,markHandoffUncertainty,clearHandoffUncertainty} from "./handoffUncertainty.mjs";
import JobIdentifier from "./JobIdentifier.jsx";
import {requestErrorMessage} from "./requestError.mjs";

const labels={approved:"승인됨",waiting_release:"헤르메스 작업 종료 및 모델 해제 대기",submitting:"생성 접수 확인 중",running:"생성 작업 진행 중",reload_queued:"Qwen 3.8 재적재 대기",reloading:"Qwen 3.8 재적재 중",cancel_waiting_release:"중지 후 모델 해제 확인 중",cancel_reload_queued:"중지 후 Qwen 3.8 재적재 대기",cancel_reloading:"중지 후 Qwen 3.8 재적재 중",rejected_reload_queued:"요청 검증 실패 · Qwen 3.8 재적재 대기",rejected_reloading:"요청 검증 실패 · Qwen 3.8 재적재 중",rejected:"요청 검증 실패 · Qwen 3.8 재적재 완료",ready:"Qwen 3.8 재적재 완료",cancelled:"취소 완료",withdrawn:"미접수 요청 철회 완료",needs_attention:"확인 필요",not_found:"접수 여부 확인 필요",checking:"접수 확인 중"};
const targetLabels={completed:"완료",failed:"실패",cancelled:"취소됨"};
const recoverable=["헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.","취소 후 헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다."];

export default function GpuHandoffStatus(props){
  return <GpuHandoffScope key={handoffUncertaintyKey(props.session,props.id,props.service)} {...props}/>;
}

function GpuHandoffScope({session,id,service,status,onUpdate,onClose,children}){
  const busyId=useId();
  const uncertaintyKey=handoffUncertaintyKey(session,id,service);
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const [uncertain,setUncertain]=useState(()=>readHandoffUncertainty(handoffSessionStorage(),uncertaintyKey).uncertain);
  const [storageAvailable,setStorageAvailable]=useState(()=>readHandoffUncertainty(handoffSessionStorage(),uncertaintyKey).available);
  const [confirmReload,setConfirmReload]=useState(false);
  const statusRequest=useRef(null),actionPending=useRef(false),reloadTriggerRef=useRef(null),reloadConfirmRef=useRef(null),statusButtonRef=useRef(null);
  const scope=JSON.stringify([session,id,service]),currentScope=useRef(scope);currentScope.current=scope;
  useEffect(()=>()=>{statusRequest.current?.abort();statusRequest.current=null;},[session,id,service]);
  useEffect(()=>{
    const focused=reloadConfirmRef.current?.contains(document.activeElement) ? document.activeElement : null;
    setConfirmReload(false);
    if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)(reloadTriggerRef.current || statusButtonRef.current)?.focus();});
  },[session,id,status?.revision]);
  function closeReloadConfirm(){
    const focused=document.activeElement;setConfirmReload(false);
    requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)(reloadTriggerRef.current || statusButtonRef.current)?.focus();});
  }
  async function perform(command,payload,mutation=false){
    if(actionPending.current || (mutation && uncertain))return;
    if(mutation && !markHandoffUncertainty(handoffSessionStorage(),uncertaintyKey)){
      setStorageAvailable(false);setUncertain(true);setError("브라우저 저장소를 사용할 수 없어 요청 상태를 보관할 수 없습니다. 저장소를 확인한 뒤 다시 시도하세요.");return;
    }
    actionPending.current=true;setBusy(true);setError("");
    const controller=new AbortController();statusRequest.current=controller;let timedOut=false;
    const requestScope=scope;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const value=await executeGpuHandoffCommand(managementCommand,command,payload,session,id,service,controller.signal);
      if(statusRequest.current===controller && currentScope.current===requestScope){
        onUpdate(value);
        if(clearHandoffUncertainty(handoffSessionStorage(),uncertaintyKey)){setStorageAvailable(true);setUncertain(false);}
        else {setStorageAvailable(false);setUncertain(true);setError("브라우저 저장소에서 요청 확인 표시를 지우지 못했습니다. 저장소를 확인한 뒤 상태를 다시 조회하세요.");}
      }
    }catch(problem){
      if(statusRequest.current===controller && currentScope.current===requestScope){
        if(mutation)setUncertain(true);
        setError(mutation ? "요청 결과를 확인하지 못했습니다. 다시 변경하기 전에 GPU 양도 상태를 확인하세요." : timedOut ? "GPU 양도 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : problem?.message ? requestErrorMessage(problem) : "GPU 양도 상태를 확인할 수 없습니다. 다시 확인하세요.");
      }
    }finally{clearTimeout(timeout);if(statusRequest.current===controller){statusRequest.current=null;actionPending.current=false;setBusy(false);}}
  }
  const summary=status?.target_summary;
  const cancelRecovery=status?.reason?.startsWith("취소 후");
  return <section className="kimodo-submission-status" aria-label="GPU 양도 상태"><h3>GPU 양도 상태</h3>
    <p>접수 ID</p><JobIdentifier id={id} label="접수 ID" compact/><p>{labels[status?.state] || "상태 확인 필요"}</p>
    {busy && <p id={busyId} role="status">GPU 양도 요청을 처리하고 있습니다.</p>}
    {uncertain && <p role="status">{storageAvailable ? "이전 요청의 결과가 확인되지 않았습니다. GPU 양도 상태를 먼저 확인하세요." : "브라우저 저장소를 사용할 수 없습니다. 저장소를 확인한 뒤 GPU 양도 상태를 다시 조회하세요."}</p>}
    {targetLabels[status?.target_status] && <><p role={status.target_status==="failed" ? "alert" : undefined}>생성 작업 {targetLabels[status.target_status]}</p>{status.job_id && <JobIdentifier id={status.job_id} compact/>}</>}
    {status?.reason && <p role="alert">{status.reason}</p>}
    {status?.state==="needs_attention" && recoverable.includes(status.reason) && summary && <>
      <p>기존 요청: {[summary.mode,summary.prompt,summary.frames ? `${summary.frames}프레임` : summary.width && summary.height ? `${summary.width}×${summary.height}` : null,summary.steps != null ? `${summary.steps}단계` : null,summary.seed != null ? `시드 ${summary.seed}` : null].filter(Boolean).join(" · ") || "입력 요약 없음"}</p>
      <button type="button" disabled={busy || uncertain} onClick={()=>{if(window.confirm(cancelRecovery ? "모델 해제와 생성 미접수 여부를 다시 확인한 뒤 Qwen 3.8을 재적재할까요?" : "모델 해제와 생성 미접수 여부를 다시 확인한 뒤 기존 요청을 계속하고 작업 후 Qwen 3.8을 재적재할까요?"))perform("hermes-gpu-handoff-recover-release",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true},true);}}>{cancelRecovery ? "확인 후 모델 재적재" : "확인 후 기존 요청 계속"}</button>
    </>}
    {status?.state==="needs_attention" && status.reason==="대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다." && <>
      <p>기존 접수 영수증을 다시 확인합니다. 새 생성은 접수하지 않습니다.</p>
      <button type="button" disabled={busy || uncertain} onClick={()=>{if(window.confirm("확인된 기존 생성 작업의 추적을 다시 시작할까요?"))perform("hermes-gpu-handoff-recover-submission",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true},true);}}>기존 접수 확인 후 추적</button>
    </>}
    {status?.state==="needs_attention" && status.reason==="3.8 재적재 또는 GPU 예약을 확인할 수 없습니다." && <>
      <p>기존 Qwen 3.8 재적재가 준비됐는지 다시 확인합니다. 새 작업은 접수하지 않습니다.</p>
      <button type="button" disabled={busy || uncertain} onClick={()=>{if(window.confirm("기존 재적재의 모델과 GPU 예약을 다시 확인할까요?"))perform("hermes-gpu-handoff-recover-reload",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true},true);}}>기존 재적재 상태 확인</button>
      {status.reload_retry === 0 && !confirmReload && <button ref={reloadTriggerRef} type="button" disabled={busy || uncertain} onClick={()=>setConfirmReload(true)}>정리 확인 후 재적재 재시도</button>}
      {status.reload_retry === 0 && confirmReload && <div ref={reloadConfirmRef} role="group" aria-label="재적재 재시도 확인" onKeyDown={event=>{if(event.key==="Escape"){event.preventDefault();event.stopPropagation();closeReloadConfirm();}}}>
        <p>실패한 재적재의 정리 상태를 확인하고 Qwen 3.8을 한 번 다시 적재할까요?</p>
        <button type="button" disabled={busy} autoFocus onClick={closeReloadConfirm}>취소</button>
        <button type="button" disabled={busy || uncertain} onClick={()=>{const focused=document.activeElement;setConfirmReload(false);requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)statusButtonRef.current?.focus();});perform("hermes-gpu-handoff-retry-reload",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true},true);}}>재적재 확인</button>
      </div>}
    </>}
    {children}
    <button ref={statusButtonRef} type="button" aria-disabled={busy} aria-describedby={busy?busyId:undefined} onClick={()=>perform("hermes-gpu-handoff-status",{session_id:session,request_id:id})}>{busy ? "GPU 양도 요청 처리 중…" : "GPU 양도 상태 확인"}</button>
    {status?.state==="not_found" && <button type="button" disabled={busy || uncertain} onClick={()=>{if(window.confirm("아직 접수되지 않은 이 요청을 철회할까요? 이미 접수됐다면 기존 상태를 표시합니다."))perform("hermes-gpu-handoff-withdraw",{session_id:session,request_id:id,service,confirmed:true},true);}}>미접수 요청 철회</button>}
    {["approved","waiting_release","running"].includes(status?.state) && <button type="button" disabled={busy || uncertain} onClick={()=>{if(window.confirm("이 생성 요청을 중지하고, 해제된 Qwen 3.8은 다시 적재할까요?"))perform("hermes-gpu-handoff-cancel",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true},true);}}>생성 중지</button>}
    {onClose && ["ready","cancelled","rejected","withdrawn"].includes(status?.state) && <button type="button" disabled={busy || uncertain} onClick={onClose}>상태 닫기</button>}
    {error && <p role="alert">{error}{status && " · 위 상태는 마지막으로 확인한 내용입니다."}</p>}
  </section>;
}
