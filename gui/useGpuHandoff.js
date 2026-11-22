import {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";

export default function useGpuHandoff(session,service,onJob,onError){
  const key=session ? `generator-gpu-handoff:${session}:${service}` : "";
  const [review,setReview]=useState(null),[id,setId]=useState(()=>key ? sessionStorage.getItem(key) || "" : ""),[status,setStatus]=useState(null);
  function update(value){setStatus(value);if(value.job_id)onJob(value.job_id);}
  useEffect(()=>{if(!id)return;let active=true;managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id}).then(value=>{
    validateGpuHandoffStatus(value,session,id,service);
    if(active)update(value);
  }).catch(problem=>{if(active)onError(problem.message);});return()=>{active=false;};},[]);
  async function preview(request){
    setReview(null);
    if(!session)return;
    const owner=await managementCommand("hermes-agent","hermes-resident-status",{session_id:session});
    if(owner.session_id!==session || !owner.resident)throw new Error("대화 모델 상태를 확인할 수 없습니다.");
    if(!owner.resident_id){if(owner.resident.state!=="not_found")throw new Error("대화 모델 상태를 확인할 수 없습니다.");return;}
    if(owner.resident.state!=="ready")throw new Error("Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.");
    const value=await managementCommand("hermes-agent","hermes-gpu-handoff-preview",{session_id:session,resident_id:owner.resident_id,service,request});
    if(value.session_id!==session || value.resident_id!==owner.resident_id || value.service!==service || !/^[a-f0-9]{64}$/.test(value.review_hash || ""))throw new Error("GPU 양도 검토 결과가 일치하지 않습니다.");
    setReview(value);
    return value;
  }
  async function approve(request,fixedRequestId){
    const requestId=fixedRequestId || crypto.randomUUID().replaceAll("-","");
    sessionStorage.setItem(key,requestId);setId(requestId);setStatus({state:"checking"});
    const value=await managementCommand("hermes-agent","hermes-gpu-handoff-approve",{request_id:requestId,session_id:session,resident_id:review.resident_id,service,request,review_hash:review.review_hash,confirmed:true});
    validateGpuHandoffStatus(value,session,requestId,service);
    if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready","cancel_waiting_release","cancel_reload_queued","cancel_reloading","cancelled","rejected_reload_queued","rejected_reloading","rejected","needs_attention"].includes(value.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다.");
    update(value);
  }
  function close(){sessionStorage.removeItem(key);setId("");setStatus(null);}
  return {id,status,review,preview,approve,update,close,clearReview:()=>setReview(null)};
}
