import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";

export default function MapDatabaseReceipt(){
  const [id,setId]=useState(""),[hash,setHash]=useState("");
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const request=useRef(null),sequence=useRef(0),button=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>{sequence.current++;request.current?.abort();},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)button.current?.focus();}},[busy]);
  const requestId=id.trim(),requestHash=hash.trim().toLowerCase();
  async function lookup(){
    if(request.current)return;
    const controller=new AbortController(),current=++sequence.current;request.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    restoreFocus.current=document.activeElement===button.current;setBusy(true);setNotice("");
    try{
      const receipt=await untilAborted(managementCommand("hermes-agent","hermes-map-database-receipt",{database_request_id:requestId,request_sha256:requestHash},{signal:controller.signal}),controller.signal);
      if(receipt.request_sha256!==requestHash)throw new Error();
      const messages=new Map([
        ["matched","DB 접수의 요청 해시가 일치합니다. 파일 동기화 상태는 별도로 확인하세요."],
        ["mismatch","보관한 요청 해시와 DB 접수 기록이 다릅니다. 원래 요청을 확인하세요."],
        ["not_found","조회 시점에 DB 접수 기록이 없습니다. 진행 중인 작업의 상태를 확인하세요."],
      ]);
      if(!messages.has(receipt.state))throw new Error();
      if(sequence.current===current)setNotice(messages.get(receipt.state));
    }catch{if(sequence.current===current)setNotice(timedOut?"DB 접수 조회 시간이 초과됐습니다. 다시 확인하세요.":"DB 접수를 확인할 수 없습니다. 요청 ID·해시와 에셋 서비스 연결을 확인하세요.");}
    finally{clearTimeout(timer);if(sequence.current===current){request.current=null;setBusy(false);}}
  }
  return <details><summary>맵 DB 변경 접수 확인</summary><fieldset disabled={busy}>
    <label>DB 요청 ID <input value={id} onChange={e=>{setId(e.target.value);setNotice("");}}/></label>
    <label>원본 요청 SHA-256 <input value={hash} aria-describedby="map-receipt-hash-hint" onChange={e=>{setHash(e.target.value);setNotice("");}}/></label>
    <p id="map-receipt-hash-hint">원본 요청에 기록된 64자리 해시를 입력하세요.</p>
    <button ref={button} disabled={!requestId || !/^[a-f0-9]{64}$/.test(requestHash)} onClick={lookup}>DB 접수 확인</button>
    {busy && <p role="status">접수 기록을 조회하고 있습니다.</p>}
    {notice && <p role="status">{notice}</p>}
  </fieldset></details>;
}
