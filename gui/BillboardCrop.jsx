import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function BillboardCrop({source,busy,setBusy,onSaved}){
  const [threshold,setThreshold]=useState("5"),[review,setReview]=useState(null),[message,setMessage]=useState("");
  async function preview(auto){
    setReview(null);setMessage("");setBusy(true);
    try{
      const request={texture:source.texture,revision:source.revision,alphaThreshold:auto?"auto":Number(threshold)};
      if(!auto && (!threshold || !Number.isInteger(request.alphaThreshold) || request.alphaThreshold<0 || request.alphaThreshold>254)){
        throw new Error("알파 기준은 0~254 사이의 정수입니다.");
      }
      let result=await managementCommand("map-assets","asset-crop-preview",request);
      if(auto){
        request.alphaThreshold=result.alpha_threshold;
        setThreshold(String(request.alphaThreshold));
        result=await managementCommand("map-assets","asset-crop-preview",request);
      }
      if(result.texture!==source.texture || !result.token || result.bounds?.length!==4)throw new Error("크롭 범위를 확인할 수 없습니다.");
      setReview({result,request:{...request,token:result.token}});
    }catch(error){setMessage(error.message);}
    finally{setBusy(false);}
  }
  async function save(){
    setBusy(true);setMessage("");
    try{
      const result=await managementCommand("map-assets","asset-crop",review.request);
      if(result.saved!==true)throw new Error("원본 크롭 저장을 확인할 수 없습니다.");
      onSaved();
    }catch(error){setMessage(error.message);}
    finally{setReview(null);setBusy(false);}
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
      <button disabled={!result.changed} onClick={save}>확인한 크롭 저장</button><button onClick={()=>setReview(null)}>크롭 취소</button>
    </section>}
    {message && <p role="status">{message}</p>}
  </fieldset></details>;
}
