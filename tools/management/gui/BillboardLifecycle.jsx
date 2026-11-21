import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function BillboardLifecycle({texture,onComplete}){
  const [size,setSize]=useState(128),[plan,setPlan]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  async function prepare(kind){
    setBusy(true);setPlan(null);setMessage("");
    try{
      const catalog=await managementCommand("map-assets","asset-list");
      const asset=catalog.assets.find(item=>item.texture===texture);
      if(!asset)throw new Error("등록 목록에서 선택한 에셋을 찾을 수 없습니다.");
      const identity={texture,revision:catalog.revision};
      if(kind==="retire"){
        const result=await managementCommand("map-assets","asset-retire-preview",identity);
        if(result.texture!==texture || !result.token || !Array.isArray(result.maps))throw new Error("폐기 영향을 확인할 수 없습니다.");
        setPlan({kind,request:{...identity,token:result.token},maps:result.maps,storage:result.storage});
      }else{
        if(asset.metadata?.length)throw new Error("프레임 메타데이터가 있는 시트입니다.");
        if(size>=Math.max(...asset.size))throw new Error("현재 "+asset.size.join(" × ")+"px보다 작은 긴 변을 선택하세요.");
        let request={...identity,size};
        if(catalog.storage!=="database"){
          const name=asset.image.split("/").pop();
          const response=await fetch("/management/map-assets/billboards/"+encodeURIComponent(name),{cache:"no-store"});
          if(!response.ok)throw new Error("등록 원본을 확인할 수 없습니다.");
          const digest=await crypto.subtle.digest("SHA-256",await response.arrayBuffer());
          const sha256=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
          request={path:"assets/billboards/"+name,sha256,size};
        }
        setPlan({kind,request,before:asset.size});
      }
    }catch(error){setMessage(error.message);}
    finally{setBusy(false);}
  }
  async function confirm(){
    setBusy(true);setMessage("");
    try{
      const retiring=plan.kind==="retire";
      const result=await managementCommand("map-assets",retiring?"asset-retire":"resize",plan.request);
      if(retiring && (result.retired!==true || result.texture!==texture))throw new Error("폐기 결과를 확인할 수 없습니다.");
      onComplete(texture+(retiring?" 폐기 완료":" 원본 축소 완료"));
    }catch(error){setMessage(error.message);}
    finally{setBusy(false);setPlan(null);}
  }
  return <details><summary>원본 해상도와 에셋 폐기</summary><fieldset disabled={busy}>
    <label>원본 긴 변 (px)<select value={size} onChange={e=>{setSize(Number(e.target.value));setPlan(null);}}>
      {[128,256,384,512].map(v=><option key={v}>{v}</option>)}</select></label>
    <button onClick={()=>prepare("resize")}>축소 내용 확인</button><button onClick={()=>prepare("retire")}>폐기 영향 조회</button>
    {plan && <section><h3>{texture}</h3>{plan.kind==="retire"?<>
      <ResultTable table={{title:"제거될 맵 배치",summary:plan.maps.reduce((n,m)=>n+m.removed,0)+"개 배치",
        columns:["맵","제거 수"],rows:plan.maps.map(m=>[m.map,m.removed])}}/>
      <p>{plan.storage==="database"?"원본 파일을 보존하고 DB에서 폐기합니다.":"원본과 생성 이력을 폐기 경로에 보존합니다."}</p></>:
      <p>{plan.before.join(" × ")} px → 긴 변 {plan.request.size}px</p>}
      <button onClick={confirm}>{plan.kind==="retire"?"확인한 에셋 폐기":"원본 축소 저장"}</button>
      <button onClick={()=>setPlan(null)}>취소</button></section>}
    {message && <p role="status">{message}</p>}
  </fieldset></details>;
}
