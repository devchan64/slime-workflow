import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {readBillboardRegistration,confirmedBillboardRegistration} from "./readBillboardRegistration.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export default function BillboardRegistration({onSaved}){
  const [file,setFile]=useState(null),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
  const helpId=useId(),previewRequest=useRef(null),saving=useRef(false),details=useRef(null),previewButton=useRef(null),saveButton=useRef(null),reviewHeading=useRef(null),status=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>{previewRequest.current?.abort();previewRequest.current=null;},[]);
  useEffect(()=>{
    if(busy || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(details.current?.open)restoreLostFocus(document,(review ? reviewHeading : status).current);
  },[busy,review,message]);
  async function preview(){
    if(!file || previewRequest.current)return;
    if(file.size>2_000_000){setMessage("등록 요청 JSON은 2MB 이하여야 합니다. 다른 파일을 선택하세요.");return;}
    restoreFocus.current=document.activeElement===previewButton.current;
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setMessage("");setReview(null);
    try{
      const result=await readBillboardRegistration(file,controller.signal);
      if(previewRequest.current===controller)setReview(result);
    }catch(problem){if(previewRequest.current===controller)setMessage(timedOut ? "등록 검토 시간이 초과됐습니다. 다시 확인하세요." : problem.message || "등록 요청을 확인할 수 없습니다.");}
    finally{clearTimeout(timer);if(previewRequest.current===controller){previewRequest.current=null;setBusy(false);}}
  }
  async function save(){
    if(!review || saving.current)return;
    restoreFocus.current=document.activeElement===saveButton.current;
    saving.current=true;
    setBusy(true);setMessage("");
    let result;
    try{
      result=await managementCommand("map-assets","asset-register",review);
      if(!confirmedBillboardRegistration(review,result))throw new Error("등록 응답이 검토한 대상과 일치하지 않습니다.");
    }catch(problem){
      setMessage((problem.message || "등록 응답을 확인할 수 없습니다.")+" · 접수 "+review.requestId+" · 결과가 불확실합니다. 다시 요청하기 전에 목록과 접수 기록을 확인하세요.");
      setReview(null);return;
    }finally{saving.current=false;setBusy(false);}
    const label=typeof result.asset==="string" ? " · "+result.asset : "";
    setMessage("등록 완료"+label);setReview(null);
    try{onSaved();}catch{setMessage("등록 완료"+label+" · 목록을 새로고침해 확인하세요.");}
  }
  return <details ref={details} onToggle={event=>{if(!event.currentTarget.open)restoreFocus.current=false;}}><summary>신규 빌보드 등록</summary><fieldset disabled={busy}>
    <label>등록 요청 JSON<input type="file" accept=".json,application/json" aria-describedby={helpId} onChange={e=>{
      setFile(e.target.files[0] || null);e.target.value="";setReview(null);setMessage("");
    }}/></label>
    <p id={helpId}>JSON 파일 · 최대 2MB{file && " · 선택: "+file.name}</p>
    <button ref={previewButton} type="button" disabled={!file} onClick={preview}>등록 원본 확인</button>
    {busy && <p role="status">등록 요청을 처리하고 있습니다.</p>}
    {review && <section><h3 ref={reviewHeading} tabIndex={-1}>등록 검토</h3><p>{review.asset.image.path} · {review.asset.image.width} × {review.asset.image.height} px</p>
      <p>접수 {review.requestId} · 예상 DB 세대 {review.expectedGeneration}</p>
      <details><summary>등록 내용</summary><pre>{JSON.stringify(review.asset,null,2)}</pre></details>
      <button ref={saveButton} type="button" onClick={save}>확인 후 신규 등록</button><button type="button" onClick={event=>{const focused=event.currentTarget;setReview(null);requestAnimationFrame(()=>{if(details.current?.open && (document.activeElement===document.body || document.activeElement===focused))previewButton.current?.focus();});}}>등록 취소</button></section>}
    {message && <p ref={status} tabIndex={-1} role="status">{message}</p>}
  </fieldset></details>;
}
