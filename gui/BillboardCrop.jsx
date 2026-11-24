import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ActionButton from "./ActionButton.jsx";

export function validCropPreview(result,texture){
  const dimensions=value=>Array.isArray(value) && value.length===2 && value.every(n=>Number.isInteger(n) && n>0);
  if(!result || result.texture!==texture || typeof result.token!=="string" || !result.token || !Number.isInteger(result.alpha_threshold) || result.alpha_threshold<0 || result.alpha_threshold>254 || typeof result.changed!=="boolean" || !dimensions(result.before) || !dimensions(result.after) || !Array.isArray(result.bounds) || result.bounds.length!==4 || !result.bounds.every(Number.isInteger))return false;
  const [x,y,right,bottom]=result.bounds;
  return x>=0 && y>=0 && right>x && bottom>y && right<=result.before[0] && bottom<=result.before[1] && result.after[0]===right-x && result.after[1]===bottom-y && result.changed===(x!==0 || y!==0 || right!==result.before[0] || bottom!==result.before[1]);
}

export default function BillboardCrop({source,busy,setBusy,onSaved}){
  const [threshold,setThreshold]=useState("5"),[review,setReview]=useState(null),[message,setMessage]=useState("");
  const requestRef=useRef(null),saving=useRef(false);
  useEffect(()=>()=>requestRef.current?.abort(),[]);
  async function preview(auto){
    if(busy || requestRef.current)return;
    const controller=new AbortController();requestRef.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setReview(null);setMessage("");setBusy(true);
    try{
      const request={texture:source.texture,revision:source.revision,alphaThreshold:auto?"auto":Number(threshold)};
      if(!auto && (!threshold || !Number.isInteger(request.alphaThreshold) || request.alphaThreshold<0 || request.alphaThreshold>254)){
        throw new Error("알파 기준은 0~254 사이의 정수입니다.");
      }
      let result=await untilAborted(managementCommand("map-assets","asset-crop-preview",request,{signal:controller.signal}),controller.signal);
      if(!validCropPreview(result,source.texture))throw new Error("크롭 범위를 확인할 수 없습니다.");
      if(auto){
        request.alphaThreshold=result.alpha_threshold;
        setThreshold(String(request.alphaThreshold));
        result=await untilAborted(managementCommand("map-assets","asset-crop-preview",request,{signal:controller.signal}),controller.signal);
      }
      if(!validCropPreview(result,source.texture) || result.alpha_threshold!==request.alphaThreshold)throw new Error("크롭 범위를 확인할 수 없습니다.");
      setReview({result,request:{...request,token:result.token}});
    }catch(error){if(!controller.signal.aborted || timedOut)setMessage(timedOut ? "크롭 범위 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(error));}
    finally{clearTimeout(timeout);if(requestRef.current===controller)requestRef.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function save(){
    if(saving.current || busy || !review)return;
    saving.current=true;
    setBusy(true);setMessage("");
    try{
      const result=await managementCommand("map-assets","asset-crop",review.request);
      if(result.saved!==true)throw new Error("원본 크롭 저장을 확인할 수 없습니다.");
      onSaved();
    }catch(error){setMessage("저장 결과를 확인하지 못했습니다. 다시 요청하기 전에 원본과 이력을 확인하세요. · "+requestErrorMessage(error));}
    finally{saving.current=false;setReview(null);setBusy(false);}
  }
  const result=review?.result;
  return <details className="billboard-crop"><summary>원본 투명 여백 크롭</summary><fieldset disabled={busy}>
    <div className="billboard-crop-controls">
    <label>알파 기준<input type="number" min="0" max="254" value={threshold} onChange={e=>{setThreshold(e.target.value);setReview(null);}}/></label>
    <button onClick={()=>preview(true)}>기준 자동 추천</button><button onClick={()=>preview(false)}>크롭 범위 확인</button>
    </div>
    <p className="billboard-crop-help">알파 기준보다 불투명한 픽셀을 기준으로 여백을 계산합니다. 0~254 사이의 정수를 입력하세요.</p>
    {result && <section><p>분홍색 테두리가 저장할 이미지 범위입니다.</p><svg role="img" aria-label="원본 위 크롭 범위" viewBox={`0 0 ${result.before.join(" ")}`} className="billboard-crop-preview">
      <image href={"/management/map-assets/billboards/"+encodeURIComponent(source.texture)+".png"} width={result.before[0]} height={result.before[1]}/>
      <rect x={result.bounds[0]} y={result.bounds[1]} width={result.bounds[2]-result.bounds[0]} height={result.bounds[3]-result.bounds[1]}
        fill="none" stroke="#ff1e96" vectorEffect="non-scaling-stroke" strokeWidth="2"/></svg>
      <p>{result.before.join(" × ")} → {result.after.join(" × ")} px · {result.changed?"저장 시 표시 높이와 앵커를 함께 보정합니다.":"제거할 여백이 없습니다."}</p>
      <ActionButton reasons={[!result.changed && "제거할 여백이 없어 저장할 필요가 없습니다."]} onClick={save}>확인한 크롭 저장</ActionButton><button type="button" onClick={()=>setReview(null)}>크롭 취소</button>
    </section>}
    {message && <p role="status">{message}</p>}
  </fieldset></details>;
}
