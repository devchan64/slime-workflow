import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ActionButton from "./ActionButton.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export function invalidCropThreshold(value){
  return value==null || String(value).trim()==="" || !Number.isInteger(Number(value)) || Number(value)<0 || Number(value)>254;
}

export function validCropPreview(result,texture){
  const dimensions=value=>Array.isArray(value) && value.length===2 && value.every(n=>Number.isInteger(n) && n>0);
  if(!result || result.texture!==texture || typeof result.token!=="string" || !result.token || !Number.isInteger(result.alpha_threshold) || result.alpha_threshold<0 || result.alpha_threshold>254 || typeof result.changed!=="boolean" || !dimensions(result.before) || !dimensions(result.after) || !Array.isArray(result.bounds) || result.bounds.length!==4 || !result.bounds.every(Number.isInteger))return false;
  const [x,y,right,bottom]=result.bounds;
  return x>=0 && y>=0 && right>x && bottom>y && right<=result.before[0] && bottom<=result.before[1] && result.after[0]===right-x && result.after[1]===bottom-y && result.changed===(x!==0 || y!==0 || right!==result.before[0] || bottom!==result.before[1]);
}

export function validCropSave(result,request){
  return Boolean(request && result?.saved===true && validCropPreview(result,request.texture) && result.token===request.token && result.alpha_threshold===request.alphaThreshold);
}

export default function BillboardCrop({source,busy,setBusy,onSaved}){
  const [threshold,setThreshold]=useState("5"),[review,setReview]=useState(null),[message,setMessage]=useState(""),[saveWarning,setSaveWarning]=useState("");
  const thresholdHelpId=useId(),thresholdErrorId=useId(),busyHelpId=useId();
  const invalidThreshold=invalidCropThreshold(threshold);
  const requestRef=useRef(null),saveRequest=useRef(null),saving=useRef(false),restoreFocus=useRef(false),messageRef=useRef(null),saveWarningRef=useRef(null),reviewRef=useRef(null),rangeButton=useRef(null);
  useEffect(()=>()=>{requestRef.current?.abort();const current=saveRequest.current;saveRequest.current=null;current?.abort();},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;restoreLostFocus(document,message ? messageRef.current : review ? reviewRef.current : saveWarning ? saveWarningRef.current : rangeButton.current);}},[busy,message,review,saveWarning]);
  async function preview(auto){
    if(busy || requestRef.current)return;
    const controller=new AbortController();requestRef.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setReview(null);setMessage("");setBusy(true);
    try{
      const request={texture:source.texture,revision:source.revision,alphaThreshold:auto?"auto":Number(threshold)};
      if(!auto && invalidCropThreshold(threshold)){
        throw new Error("알파 기준은 0~254 사이의 정수입니다.");
      }
      let result=await untilAborted(managementCommand("map-assets","asset-crop-preview",request,{signal:controller.signal}),controller.signal);
      if(!validCropPreview(result,source.texture))throw new Error("크롭 범위를 확인할 수 없습니다.");
      if(auto){
        request.alphaThreshold=result.alpha_threshold;
        result=await untilAborted(managementCommand("map-assets","asset-crop-preview",request,{signal:controller.signal}),controller.signal);
      }
      if(!validCropPreview(result,source.texture) || result.alpha_threshold!==request.alphaThreshold)throw new Error("크롭 범위를 확인할 수 없습니다.");
      if(auto)setThreshold(String(request.alphaThreshold));
      setReview({result,request:{...request,token:result.token}});
    }catch(error){if(!controller.signal.aborted || timedOut)setMessage(timedOut ? "크롭 범위 조회 시간이 초과됐습니다. 다시 확인하세요." : "크롭 범위를 확인하지 못했습니다. 입력을 확인하거나 다시 시도하세요. · "+requestErrorMessage(error));}
    finally{clearTimeout(timeout);if(requestRef.current===controller)requestRef.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function save(){
    if(saving.current || busy || !review)return;
    saving.current=true;
    const controller=new AbortController();saveRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setMessage("");setSaveWarning("");
    try{
      const result=await untilAborted(managementCommand("map-assets","asset-crop",review.request,{signal:controller.signal}),controller.signal);
      if(saveRequest.current!==controller)return;
      if(!validCropSave(result,review.request))throw new Error("원본 크롭 저장 결과의 대상을 확인할 수 없습니다.");
      onSaved({restoreFocus:restoreFocus.current});
    }catch(error){if(saveRequest.current===controller)setSaveWarning("저장 결과를 확인하지 못했습니다. 서버에서 처리가 진행 중일 수 있으므로 다시 요청하기 전에 원본과 이력을 확인하세요. · "+(timedOut ? "응답 시간이 초과됐습니다." : requestErrorMessage(error)));}
    finally{clearTimeout(timeout);if(saveRequest.current===controller){saveRequest.current=null;saving.current=false;setReview(null);setBusy(false);}}
  }
  const result=review?.result;
  return <details className="billboard-crop"><summary>원본 투명 여백 크롭</summary>{busy && <p id={busyHelpId} role="status">빌보드 요청이 끝날 때까지 기다리세요.</p>}<fieldset disabled={busy} aria-describedby={busy ? busyHelpId : undefined}>
    <div className="billboard-crop-controls">
    <div><label>알파 기준<input type="number" required min="0" max="254" step="1" value={threshold} aria-invalid={invalidThreshold || undefined} aria-describedby={[thresholdHelpId,invalidThreshold && thresholdErrorId].filter(Boolean).join(" ")} onChange={e=>{setThreshold(e.target.value);setReview(null);}}/></label>{invalidThreshold && <small id={thresholdErrorId}>0~254 사이의 정수를 입력하세요.</small>}</div>
    <button type="button" onClick={event=>{restoreFocus.current=document.activeElement===event.currentTarget;preview(true);}}>기준 자동 추천</button><ActionButton buttonRef={rangeButton} reasons={[invalidThreshold && "알파 기준을 0~254의 정수로 수정하세요."]} onClick={event=>{restoreFocus.current=document.activeElement===event.currentTarget;preview(false);}}>크롭 범위 확인</ActionButton>
    </div>
    <p id={thresholdHelpId} className="billboard-crop-help">알파 기준보다 불투명한 픽셀을 기준으로 여백을 계산합니다. 0~254 사이의 정수를 입력하세요.</p>
    {result && <section ref={reviewRef} tabIndex={-1} aria-label="크롭 범위 확인"><p>밝고 어두운 외곽선이 있는 분홍색 테두리가 저장할 이미지 범위입니다.</p><svg role="img" aria-label="원본 위 크롭 범위" viewBox={`0 0 ${result.before.join(" ")}`} className="billboard-crop-preview">
      <image href={"/management/map-assets/billboards/"+encodeURIComponent(source.texture)+".png"} width={result.before[0]} height={result.before[1]}/>
      {[5,3].map((width,index)=><rect key={width} x={result.bounds[0]} y={result.bounds[1]} width={result.bounds[2]-result.bounds[0]} height={result.bounds[3]-result.bounds[1]}
        fill="none" stroke={index===0?"#111":"#fff"} vectorEffect="non-scaling-stroke" strokeWidth={width}/>)}
      <rect x={result.bounds[0]} y={result.bounds[1]} width={result.bounds[2]-result.bounds[0]} height={result.bounds[3]-result.bounds[1]}
        fill="none" stroke="#ff1e96" vectorEffect="non-scaling-stroke" strokeWidth="1"/></svg>
      <p>{result.before.join(" × ")} → {result.after.join(" × ")} px · {result.changed?"저장 시 표시 높이와 앵커를 함께 보정합니다.":"제거할 여백이 없습니다."}</p>
      <p>원본 왼쪽 위 기준 크롭 경계 좌표 · 왼쪽 {result.bounds[0]} px, 위 {result.bounds[1]} px, 오른쪽 {result.bounds[2]} px, 아래 {result.bounds[3]} px</p>
      <ActionButton reasons={[!result.changed && "제거할 여백이 없어 저장할 필요가 없습니다."]} onClick={event=>{restoreFocus.current=document.activeElement===event.currentTarget;save();}}>확인한 크롭 저장</ActionButton><button type="button" onClick={event=>{if(document.activeElement===event.currentTarget && !rangeButton.current?.disabled)rangeButton.current?.focus();setReview(null);}}>크롭 취소</button>
    </section>}
    {message && <p ref={messageRef} tabIndex={-1} role="alert">{message}</p>}
    {saveWarning && <p ref={saveWarningRef} tabIndex={-1} role="alert">{saveWarning}</p>}
  </fieldset></details>;
}
