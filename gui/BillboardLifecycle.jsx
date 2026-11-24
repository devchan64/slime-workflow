import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export function validRetirementPreview(result,texture){
  return Boolean(result && result.texture===texture && typeof result.token==="string" && /^[a-f0-9]{64}$/.test(result.token) && Array.isArray(result.maps) && result.maps.every(map=>map && typeof map.map==="string" && Number.isSafeInteger(map.removed) && map.removed>=0));
}
export function validResizeResult(result,plan,texture){
  if(!result || typeof result!=="object")return false;
  const database=Boolean(plan.request.texture),dimensions=database ? result.after : result.size;
  return (database ? result.texture===texture : result.path===plan.request.path) && Array.isArray(dimensions) && dimensions.length===2 && dimensions.every((value,index)=>Number.isSafeInteger(value) && value>0 && value<=plan.before[index]) && Math.max(...dimensions)===plan.request.size;
}

export default function BillboardLifecycle({texture,onComplete,onInteractionChange}){
  const [size,setSize]=useState(128),[plan,setPlan]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  const previewRequest=useRef(null);
  useEffect(()=>()=>previewRequest.current?.abort(),[]);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(plan));return ()=>onInteractionChange?.(false);},[busy,plan,onInteractionChange]);
  async function prepare(kind){
    if(previewRequest.current)return;
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setPlan(null);setMessage("");
    try{
      const catalog=await untilAborted(managementCommand("map-assets","asset-list",{},{signal:controller.signal}),controller.signal);
      if(!catalog || !Array.isArray(catalog.assets) || typeof catalog.revision!=="string")throw new Error("에셋 목록 응답을 확인할 수 없습니다.");
      const asset=catalog.assets.find(item=>item.texture===texture);
      if(!asset)throw new Error("등록 목록에서 선택한 에셋을 찾을 수 없습니다.");
      const identity={texture,revision:catalog.revision};
      if(kind==="retire"){
        const result=await untilAborted(managementCommand("map-assets","asset-retire-preview",identity,{signal:controller.signal}),controller.signal);
        if(!validRetirementPreview(result,texture))throw new Error("폐기 영향을 확인할 수 없습니다.");
        setPlan({kind,request:{...identity,token:result.token},maps:result.maps,storage:result.storage});
      }else{
        if(!Array.isArray(asset.size) || asset.size.length!==2 || asset.size.some(value=>!Number.isSafeInteger(value) || value<=0) || (catalog.storage!=="database" && typeof asset.image!=="string"))throw new Error("에셋 원본 크기나 경로를 확인할 수 없습니다.");
        if(asset.metadata?.length)throw new Error("프레임 메타데이터가 있는 시트입니다.");
        if(size>=Math.max(...asset.size))throw new Error("현재 "+asset.size.join(" × ")+"px보다 작은 긴 변을 선택하세요.");
        let request={...identity,size};
        if(catalog.storage!=="database"){
          const name=asset.image.split("/").pop();
          const response=await untilAborted(fetch("/management/map-assets/billboards/"+encodeURIComponent(name),{cache:"no-store",signal:controller.signal}),controller.signal);
          if(!response.ok)throw new Error("등록 원본을 확인할 수 없습니다.");
          const buffer=await untilAborted(response.arrayBuffer(),controller.signal);
          const digest=await untilAborted(crypto.subtle.digest("SHA-256",buffer),controller.signal);
          const sha256=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
          request={path:"assets/billboards/"+name,sha256,size};
        }
        setPlan({kind,request,before:asset.size});
      }
    }catch(error){if(!controller.signal.aborted || timedOut)setMessage(timedOut ? "검토 대상 조회 시간이 초과됐습니다. 다시 확인하세요." : error.message);}
    finally{clearTimeout(timeout);if(previewRequest.current===controller)previewRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function confirm(){
    setBusy(true);setMessage("");
    try{
      const retiring=plan.kind==="retire";
      const result=await managementCommand("map-assets",retiring?"asset-retire":"resize",plan.request);
      if(retiring && (result.retired!==true || result.texture!==texture))throw new Error("폐기 결과를 확인할 수 없습니다.");
      if(!retiring && !validResizeResult(result,plan,texture))throw new Error("축소 결과를 확인할 수 없습니다.");
      onComplete(texture+(retiring?" 폐기 완료":" 원본 축소 완료"),{retired:retiring});
    }catch(error){setMessage(error.message+" · 처리 결과가 불확실할 수 있습니다. 다시 요청하기 전에 에셋 상태를 확인하세요.");}
    finally{setBusy(false);setPlan(null);}
  }
  return <details><summary>원본 해상도와 에셋 폐기</summary><fieldset disabled={busy}>
    <label>원본 긴 변 (px)<select value={size} onChange={e=>{setSize(Number(e.target.value));setPlan(null);}}>
      {[128,256,384,512].map(v=><option key={v}>{v}</option>)}</select></label>
    <button type="button" onClick={()=>prepare("resize")}>축소 내용 확인</button><button type="button" onClick={()=>prepare("retire")}>폐기 영향 조회</button>
    {plan && <section><h3>{texture}</h3>{plan.kind==="retire"?<>
      <ResultTable table={{title:"제거될 맵 배치",summary:plan.maps.reduce((n,m)=>n+m.removed,0)+"개 배치",
        columns:["맵","제거 수"],rows:plan.maps.map(m=>[m.map,m.removed])}}/>
      <p>{plan.storage==="database"?"원본 파일을 보존하고 DB에서 폐기합니다.":"원본과 생성 이력을 폐기 경로에 보존합니다."}</p></>:
      <p>{plan.before.join(" × ")} px → 긴 변 {plan.request.size}px</p>}
      <button type="button" onClick={confirm}>{plan.kind==="retire"?"확인한 에셋 폐기":"원본 축소 저장"}</button>
      <button type="button" onClick={()=>setPlan(null)}>취소</button></section>}
    {message && <p role="status">{message}</p>}
  </fieldset></details>;
}
