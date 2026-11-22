import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";

const labels={approved:"승인됨",waiting_release:"헤르메스 작업 종료 및 모델 해제 대기",submitting:"생성 접수 확인 중",running:"생성 작업 진행 중",reload_queued:"Qwen 3.8 재적재 대기",reloading:"Qwen 3.8 재적재 중",cancel_waiting_release:"중지 후 모델 해제 확인 중",cancel_reload_queued:"중지 후 Qwen 3.8 재적재 대기",cancel_reloading:"중지 후 Qwen 3.8 재적재 중",rejected_reload_queued:"요청 검증 실패 · Qwen 3.8 재적재 대기",rejected_reloading:"요청 검증 실패 · Qwen 3.8 재적재 중",rejected:"요청 검증 실패 · Qwen 3.8 재적재 완료",ready:"Qwen 3.8 재적재 완료",cancelled:"취소 완료",withdrawn:"미접수 요청 철회 완료",needs_attention:"확인 필요",not_found:"접수 여부 확인 필요",checking:"접수 확인 중"};
const targetLabels={completed:"완료",failed:"실패",cancelled:"취소됨"};
const recoverable=["헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.","취소 후 헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다."];

export default function GpuHandoffStatus({session,id,service,status,onUpdate,onClose,children}){
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function perform(action){setBusy(true);setError("");try{await action();}catch(problem){setError(problem.message || "GPU 양도 상태를 확인할 수 없습니다.");}finally{setBusy(false);}}
  async function refresh(){
    const value=await managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id});
    onUpdate(validateGpuHandoffStatus(value,session,id,service));
  }
  const summary=status?.target_summary;
  const cancelRecovery=status?.reason?.startsWith("취소 후");
  return <section className="kimodo-submission-status" aria-label="GPU 양도 상태"><h3>GPU 양도 상태</h3>
    <p>접수 ID <code>{id}</code></p><p>{labels[status?.state] || "상태 확인 필요"}</p>
    {targetLabels[status?.target_status] && <p role={status.target_status==="failed" ? "alert" : undefined}>생성 작업 {targetLabels[status.target_status]}{status.job_id && <> · <code>{status.job_id}</code></>}</p>}
    {status?.reason && <p role="alert">{status.reason}</p>}
    {status?.state==="needs_attention" && recoverable.includes(status.reason) && summary && <>
      <p>기존 요청: {[summary.mode,summary.prompt,summary.frames ? `${summary.frames}프레임` : summary.width && summary.height ? `${summary.width}×${summary.height}` : null,summary.steps != null ? `${summary.steps}단계` : null,summary.seed != null ? `시드 ${summary.seed}` : null].filter(Boolean).join(" · ") || "입력 요약 없음"}</p>
      <button type="button" disabled={busy} onClick={()=>{if(window.confirm(cancelRecovery ? "모델 해제와 생성 미접수 여부를 다시 확인한 뒤 Qwen 3.8을 재적재할까요?" : "모델 해제와 생성 미접수 여부를 다시 확인한 뒤 기존 요청을 계속하고 작업 후 Qwen 3.8을 재적재할까요?"))perform(async()=>{
        const value=await managementCommand("hermes-agent","hermes-gpu-handoff-recover-release",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
      });}}>{cancelRecovery ? "확인 후 모델 재적재" : "확인 후 기존 요청 계속"}</button>
    </>}
    {status?.state==="needs_attention" && status.reason==="대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다." && <>
      <p>기존 접수 영수증을 다시 확인합니다. 새 생성은 접수하지 않습니다.</p>
      <button type="button" disabled={busy} onClick={()=>{if(window.confirm("확인된 기존 생성 작업의 추적을 다시 시작할까요?"))perform(async()=>{
        const value=await managementCommand("hermes-agent","hermes-gpu-handoff-recover-submission",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
      });}}>기존 접수 확인 후 추적</button>
    </>}
    {status?.state==="needs_attention" && status.reason==="3.8 재적재 또는 GPU 예약을 확인할 수 없습니다." && <>
      <p>기존 Qwen 3.8 재적재가 준비됐는지 다시 확인합니다. 새 작업은 접수하지 않습니다.</p>
      <button type="button" disabled={busy} onClick={()=>{if(window.confirm("기존 재적재의 모델과 GPU 예약을 다시 확인할까요?"))perform(async()=>{
        const value=await managementCommand("hermes-agent","hermes-gpu-handoff-recover-reload",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
      });}}>기존 재적재 상태 확인</button>
      {status.reload_retry === 0 && <button type="button" disabled={busy} onClick={()=>{if(window.confirm("실패한 재적재의 정리 상태를 확인하고 Qwen 3.8을 한 번 다시 적재할까요?"))perform(async()=>{
        const value=await managementCommand("hermes-agent","hermes-gpu-handoff-retry-reload",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
      });}}>정리 확인 후 재적재 재시도</button>}
    </>}
    {children}
    <button type="button" disabled={busy} onClick={()=>perform(refresh)}>GPU 양도 상태 확인</button>
    {status?.state==="not_found" && <button type="button" disabled={busy} onClick={()=>{if(window.confirm("아직 접수되지 않은 이 요청을 철회할까요? 이미 접수됐다면 기존 상태를 표시합니다."))perform(async()=>{
      const value=await managementCommand("hermes-agent","hermes-gpu-handoff-withdraw",{session_id:session,request_id:id,service,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
    });}}>미접수 요청 철회</button>}
    {["approved","waiting_release","running"].includes(status?.state) && <button type="button" disabled={busy} onClick={()=>{if(window.confirm("이 생성 요청을 중지하고, 해제된 Qwen 3.8은 다시 적재할까요?"))perform(async()=>{
      const value=await managementCommand("hermes-agent","hermes-gpu-handoff-cancel",{session_id:session,request_id:id,expected_revision:status.revision,confirmed:true});onUpdate(validateGpuHandoffStatus(value,session,id,service));
    });}}>생성 중지</button>}
    {onClose && ["ready","cancelled","rejected","withdrawn"].includes(status?.state) && <button type="button" disabled={busy} onClick={onClose}>상태 닫기</button>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
