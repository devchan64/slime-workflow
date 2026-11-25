import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ActionButton from "./ActionButton.jsx";

export function validMapReceiptId(value){return typeof value==="string" && Array.from(value.trim()).length>0 && Array.from(value.trim()).length<=180;}

export default function MapDatabaseReceipt(){
  const [id,setId]=useState(""),[hash,setHash]=useState("");
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[noticeError,setNoticeError]=useState(false);
  const idHint=useId(),idError=useId(),hashHint=useId(),hashError=useId(),busyId=useId();
  const request=useRef(null),sequence=useRef(0),inputRevision=useRef(0),button=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>{sequence.current++;request.current?.abort();},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)button.current?.focus();}},[busy]);
  const requestId=id.trim(),requestHash=hash.trim().toLowerCase();
  const invalidId=Boolean(requestId && !validMapReceiptId(requestId));
  const invalidHash=Boolean(requestHash && !/^[a-f0-9]{64}$/.test(requestHash));
  async function lookup(){
    if(request.current)return;
    const controller=new AbortController(),current=++sequence.current,inputVersion=inputRevision.current;request.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    restoreFocus.current=document.activeElement===button.current;setBusy(true);setNotice("");setNoticeError(false);
    try{
      const receipt=await untilAborted(managementCommand("hermes-agent","hermes-map-database-receipt",{database_request_id:requestId,request_sha256:requestHash},{signal:controller.signal}),controller.signal);
      if(receipt.request_sha256!==requestHash)throw new Error();
      const messages=new Map([
        ["matched","DB 접수의 요청 해시가 일치합니다. 파일 동기화 상태는 별도로 확인하세요."],
        ["mismatch","보관한 요청 해시와 DB 접수 기록이 다릅니다. 원래 요청을 확인하세요."],
        ["not_found","조회 시점에 DB 접수 기록이 없습니다. 진행 중인 저장이 없거나 재접수가 안전하다는 뜻은 아닙니다. 작업 상태를 확인하세요."],
      ]);
      if(!messages.has(receipt.state))throw new Error();
      if(sequence.current===current && inputRevision.current===inputVersion)setNotice(messages.get(receipt.state));
    }catch(problem){if(sequence.current===current && inputRevision.current===inputVersion){setNoticeError(true);setNotice(timedOut?"DB 접수 조회 시간이 초과됐습니다. 다시 확인하세요.":typeof problem?.message==="string" && problem.message.includes("SLIME_CONTENT_SERVICE_ORIGIN") ? "콘텐츠 서비스 주소가 설정되지 않았거나 유효하지 않습니다. 서비스 설정을 확인하세요." : "DB 접수를 확인할 수 없습니다. 요청 ID·해시와 에셋 서비스 연결을 확인하세요.");}}
    finally{clearTimeout(timer);if(sequence.current===current){request.current=null;setBusy(false);}}
  }
  return <details><summary>맵 DB 변경 접수 확인</summary><fieldset disabled={busy} aria-describedby={busy ? busyId : undefined}><legend className="generator-visually-hidden">맵 DB 접수 조회 입력</legend>
    <label>DB 요청 ID <input value={id} aria-invalid={invalidId || undefined} aria-describedby={[idHint,invalidId ? idError : null].filter(Boolean).join(" ")} onChange={e=>{inputRevision.current++;setId(e.target.value);setNotice("");}}/></label>
    <p id={idHint}>요청 ID는 180자 이내로 입력하세요.</p>
    {invalidId && <p id={idError} role="alert">요청 ID는 180자 이내여야 합니다.</p>}
    <label>원본 요청 SHA-256 <input value={hash} aria-invalid={invalidHash || undefined} aria-describedby={[hashHint,invalidHash ? hashError : null].filter(Boolean).join(" ")} onChange={e=>{inputRevision.current++;setHash(e.target.value);setNotice("");}}/></label>
    <p id={hashHint}>원본 요청에 기록된 64자리 해시를 입력하세요.</p>
    {invalidHash && <p id={hashError} role="alert">SHA-256 해시는 0~9와 a~f로 된 64자리여야 합니다.</p>}
    <ActionButton buttonRef={button} reasons={[!validMapReceiptId(requestId) && "180자 이내의 DB 요청 ID를 입력하세요.",!/^[a-f0-9]{64}$/.test(requestHash) && "원본 요청 SHA-256 해시 64자리를 입력하세요."]} onClick={lookup}>DB 접수 확인</ActionButton>
    {busy && <p id={busyId} role="status">접수 기록을 조회하고 있습니다.</p>}
    {notice && <p role={noticeError ? "alert" : "status"}>{notice}</p>}
  </fieldset></details>;
}
