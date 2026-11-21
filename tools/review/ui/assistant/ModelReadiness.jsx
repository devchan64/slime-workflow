import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ModelInventory from "./ModelInventory.jsx";

export default function ModelReadiness({service}) {
  const [revision,setRevision]=useState(0);
  const [status,setStatus]=useState(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    let active=true,timer;
    setError("");setStatus(null);
    async function read() {
      try {
        const next=await managementCommand(service,"model-status",{});
        if(!active)return;
        if(typeof next.ready!=="boolean" || typeof next.message!=="string") throw new Error("모델 상태 응답을 확인하세요.");
        setStatus(next);
        if(next.preparation_status==="running")timer=setTimeout(read,5000);
      } catch(problem) {
        if(active){setStatus(null);setError(problem.message);}
      }
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[service,revision]);
  return <section aria-label="모델 준비 상태">
    <p role="status">{error ? "모델 상태 조회 실패 · "+error : status ?
      ((status.generation_ready ?? status.ready)?"생성 준비 완료":"모델 준비 필요")+" · "+status.message : "모델 상태 확인 중…"}</p>
    <button onClick={()=>setRevision(value=>value+1)}>모델 준비 상태 확인</button>
    <ModelInventory service={service}/>
    {location.pathname.replace(/\/$/,"") !== "/management/assistant/models" && <a href="/management/assistant/models/">모델별 상태 조회</a>}
    <a href="/management/?tool=model-management&category=model-management">모델 관리로 이동</a>
  </section>;
}
