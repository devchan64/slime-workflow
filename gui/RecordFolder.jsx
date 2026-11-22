import React, {useEffect,useRef,useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";
import {untilAborted} from "./managementCommand.js";
import {writeClipboardText} from "./clipboardWrite.mjs";

export default function RecordFolder({service,id,direct=false}) {
  const [path,setPath]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  const [stale,setStale]=useState(false);
  const pathInput=useRef(null),copyButton=useRef(null),copySequence=useRef(0),pending=useRef(null);
  useEffect(()=>()=>pending.current?.abort(),[]);
  async function request(action) {
    if(pending.current)return;
    const controller=new AbortController();pending.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const focused=document.activeElement?.tagName==="BUTTON" ? document.activeElement : null;
    copySequence.current++;
    setBusy(true);setNotice("");
    try {
      const result=await untilAborted((async()=>{const response=await fetch("/management/record-folder/"+action,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({service,id}),signal:controller.signal});const data=await response.json();if(!response.ok || typeof data?.path!=="string" || !data.path || (data.message!=null && typeof data.message!=="string"))throw new Error(typeof data?.error==="string" ? data.error : "기록 폴더를 확인할 수 없습니다.");return data;})(),controller.signal);
      if(controller.signal.aborted)return;
      setPath(result.path);setStale(false);setNotice(result.message || "");
    } catch(problem) {if(!controller.signal.aborted || timedOut){if(action==="inspect" && path)setStale(true);setNotice(action==="open" ? "폴더 열기 결과를 확인하지 못했습니다. 이미 열렸는지 확인하세요."+(timedOut ? "" : " "+requestErrorMessage(problem)) : timedOut ? "폴더 경로 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}}
    finally {clearTimeout(timeout);if(pending.current===controller)pending.current=null;if(!controller.signal.aborted || timedOut){setBusy(false);if(focused)requestAnimationFrame(()=>{if(focused.isConnected && !focused.disabled && document.activeElement===document.body)focused.focus();});}}
  }
  async function copy() {
    const sequence=++copySequence.current;
    try {await writeClipboardText(path);if(sequence===copySequence.current)setNotice("기록 폴더 경로를 복사했습니다.");}
    catch {if(sequence!==copySequence.current)return;if(document.activeElement===document.body || document.activeElement===copyButton.current){pathInput.current?.focus();pathInput.current?.select();}setNotice("경로를 선택해 복사 단축키를 사용하세요.");}
  }
  const openButton=<button type="button" disabled={busy} onClick={()=>request("open")}>{direct ? "결과 폴더 열기" : "기록 폴더 열기"}</button>;
  const feedback=<p role="status">{busy ? "기록 폴더 확인 중…" : notice}</p>;
  return <>{direct && openButton}<details className="record-folder" onToggle={event=>{if(!event.currentTarget.open)copySequence.current++;else if(!path && !busy)request("inspect");}}>
    <summary>{direct ? "폴더 경로 확인" : "기록 폴더"}</summary>
    {path && <label>기록 폴더 경로<input ref={pathInput} aria-label="기록 폴더 경로" readOnly value={path} onFocus={event=>event.currentTarget.select()}/></label>}
    {stale && <p role="status">표시된 경로는 마지막으로 확인한 값입니다. 현재 폴더 상태는 확인하지 못했습니다.</p>}
    <div className="choice-buttons"><button type="button" disabled={busy} onClick={()=>request("inspect")}>경로 다시 확인</button>
      <button ref={copyButton} type="button" disabled={busy || !path} onClick={copy}>경로 복사</button>
      {!direct && openButton}</div>
    {!direct && feedback}
  </details>{direct && feedback}</>;
}
