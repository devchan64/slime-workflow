import React,{useEffect,useId,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {readConversationVideoReceipt} from "./conversationVideoReceipt.mjs";
import {FunControlResult} from "./FunControlSchema.jsx";
import JobIdentifier from "./JobIdentifier.jsx";

export default function ConversationVideoForm({session,formId,open,reuse}){
  const [receipt,setReceipt]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0),[show,setShow]=useState(false),[loading,setLoading]=useState(true);
  const loadingId=useId();
  useEffect(()=>{let active=true,timedOut=false;const controller=new AbortController(),timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    readConversationVideoReceipt(managementCommand,session,formId,controller.signal)
      .then(value=>{if(active){setReceipt(value);setError("");}}).catch(problem=>{if(active)setError(timedOut ? "접수 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}).finally(()=>{clearTimeout(timer);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,formId,revision]);
  return <section aria-label="저장된 Wan Fun Control 폼"><p>저장된 생성 폼 · {receipt?.state === "accepted" ? "접수됨" : receipt?.state === "unknown" ? "접수 결과 확인 필요" : receipt?.state === "not_found" ? "미접수" : receipt?.state === "rejected" ? "접수 거절됨" : error ? "접수 상태 확인 실패" : "접수 상태 확인 중"}</p>
    {receipt?.state==="accepted" && <JobIdentifier id={receipt.job_id}/>}
    <button type="button" onClick={()=>open(formId)}>입력 폼 다시 열기</button>
    <button type="button" aria-disabled={loading} aria-describedby={loading ? loadingId : undefined} onClick={()=>{if(!loading)refresh(n=>n+1);}}>접수 상태 새로고침</button>
    {loading && <p id={loadingId} role="status">접수 상태를 확인하고 있습니다.{receipt && " 이전에 확인한 상태를 표시합니다."}</p>}
    {receipt?.state==="unknown" && <p role="status">접수 여부가 불확실합니다. 생성 이력을 확인하고 자동 재접수하지 않습니다.</p>}
    {receipt?.state==="accepted" && <><button type="button" onClick={()=>setShow(v=>!v)}>{show?"결과 닫기":"결과 열기"}</button>{show && <FunControlResult job={receipt.job_id} folderLink onReuse={()=>reuse(receipt.job_id)}/>}</>}
    {error && <p role="alert">{error}{receipt && " 이전에 확인한 상태를 표시합니다."}</p>}
  </section>;
}
