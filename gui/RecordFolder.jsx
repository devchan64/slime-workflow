import React, {useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";

export default function RecordFolder({service,id}) {
  const [path,setPath]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  async function request(action) {
    setBusy(true);setNotice("");
    try {
      const response=await fetch("/management/record-folder/"+action,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({service,id})});
      const result=await response.json();
      if(!response.ok || typeof result.path!=="string")throw new Error(result.error || "기록 폴더를 확인할 수 없습니다.");
      setPath(result.path);setNotice(result.message || "");
    } catch(problem) {setNotice(requestErrorMessage(problem));}
    finally {setBusy(false);}
  }
  async function copy() {
    try {await navigator.clipboard.writeText(path);setNotice("기록 폴더 경로를 복사했습니다.");}
    catch {setNotice("복사하지 못했습니다. 표시된 경로를 직접 선택해 복사하세요.");}
  }
  return <details className="record-folder" onToggle={event=>{if(event.currentTarget.open && !path && !busy)request("inspect");}}>
    <summary>기록 폴더</summary>
    {path && <label>기록 폴더 경로<input aria-label="기록 폴더 경로" readOnly value={path} onFocus={event=>event.currentTarget.select()}/></label>}
    <div className="choice-buttons"><button type="button" disabled={busy} onClick={()=>request("inspect")}>경로 다시 확인</button>
      <button type="button" disabled={busy || !path} onClick={copy}>경로 복사</button>
      <button type="button" disabled={busy} onClick={()=>request("open")}>기록 폴더 열기</button></div>
    <p role="status">{busy ? "기록 폴더 확인 중…" : notice}</p>
  </details>;
}
