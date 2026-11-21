import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {FunControlResult} from "./FunControlSchema.jsx";

export default function ConversationVideoForm({session,formId,open}){
  const [receipt,setReceipt]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0),[show,setShow]=useState(false);
  useEffect(()=>{let active=true;
    managementCommand("hermes-agent","hermes-video-form-status",{session_id:session,form_id:formId})
      .then(value=>{if(active){setReceipt(value);setError("");}}).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[session,formId,revision]);
  return <section aria-label="저장된 Wan Fun Control 폼"><p>저장된 생성 폼 · {receipt?.state === "accepted" ? "접수됨" : receipt?.state === "unknown" ? "접수 결과 확인 필요" : receipt?.state === "not_found" ? "미접수" : "접수 상태 확인 중"}</p>
    <button type="button" onClick={()=>open(formId)}>입력 폼 다시 열기</button>
    <button type="button" onClick={()=>refresh(n=>n+1)}>접수 상태 새로고침</button>
    {receipt?.state==="unknown" && <p role="status">접수 여부가 불확실합니다. 생성 이력을 확인하고 자동 재접수하지 않습니다.</p>}
    {receipt?.state==="accepted" && <><button type="button" onClick={()=>setShow(v=>!v)}>{show?"결과 닫기":"결과 열기"}</button>{show && <FunControlResult job={receipt.job_id} folderLink/>}</>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
