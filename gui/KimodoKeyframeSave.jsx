import React,{useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";

async function command(name,payload){
  const controller=new AbortController();let timedOut=false;
  const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{return await managementCommand("hermes-agent","hermes-kimodo-keyframe-"+name,payload,{signal:controller.signal});}
  catch(problem){if(timedOut)throw new Error(name==="save" ? "저장 응답 시간이 초과됐습니다. 저장 접수 조회로 처리 여부를 확인하세요." : "키프레임 조회 시간이 초과됐습니다. 다시 확인하세요.");if(name==="save")throw new Error(requestErrorMessage(problem)+" 저장 접수 조회로 처리 여부를 확인하세요.");throw problem;}
  finally{clearTimeout(timeout);}
}

export default function KimodoKeyframeSave({preview,choose}){
  const [tag,setTag]=useState(""),[review,setReview]=useState(null),[receipt,setReceipt]=useState(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const pending=useRef(false);
  async function readReceipt(requestId){
    const value=await command("receipt",{request_id:requestId});
    if(value.request_id!==requestId || !["completed","unknown","not_found"].includes(value.state))
      throw new Error("접수 상태를 확인할 수 없습니다.");
    setReceipt(value);
  }
  async function run(action){
    if(pending.current)return;
    pending.current=true;setBusy(true);setError("");
    try{await action();}catch(problem){setError(requestErrorMessage(problem));}finally{pending.current=false;setBusy(false);}
  }
  async function inspect(){
    setReview(null);setReceipt(null);
    const source={job_id:preview.job_id,attempt_id:preview.attempt_id,frame:preview.frame,tag:tag.trim()};
    const result=await command("source-review",source);
    if(Object.entries(source).some(([key,value])=>result[key]!==value) || result.image_sha256!==preview.image_sha256 || !/^[a-f0-9]{64}$/.test(result.review_sha256))
      throw new Error("원본이 변경되었습니다. 프레임을 다시 조회하세요.");
    const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(JSON.stringify(["source-history",source])));
    const requestId="keyframe_"+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
    setReview({payload:{...source,request_id:requestId,review_sha256:result.review_sha256},ready:result.chat_save_readiness==="ready",motion:result.source_motion});
    await readReceipt(requestId);
  }
  async function save(){
    setReceipt(null);
    await command("save",review.payload);
    await readReceipt(review.payload.request_id);
  }
  return <fieldset disabled={busy}><legend>독립 키프레임 저장</legend>
    {busy && <p role="status">키프레임 요청을 처리하고 있습니다.</p>}
    <label>키프레임 태그 <input maxLength={80} value={tag} onChange={e=>{setTag(e.target.value);setReview(null);setReceipt(null);setError("");}}/></label>
    <button type="button" disabled={!tag.trim()} onClick={()=>run(inspect)}>저장할 원본 검토</button>
    {review && <><p>{review.motion} · {preview.frame}프레임 · {tag.trim()}</p>
      {receipt?.state==="not_found" && (review.ready?<button type="button" onClick={()=>run(save)}>검토한 키프레임 저장</button>:<p>기존 키프레임 접수 기록 확인이 필요합니다.</p>)}
      {receipt?.state==="unknown" && <p role="status">{receipt.message}</p>}
      {receipt?.state==="completed" && <button type="button" onClick={()=>choose("Kimodo 키프레임",receipt.keyframe_id)}>저장된 {receipt.keyframe_id} 대화 입력에 추가</button>}
      <button type="button" onClick={()=>run(()=>readReceipt(review.payload.request_id))}>저장 접수 조회</button></>}
    {error && <p role="alert">{error}</p>}
  </fieldset>;
}
