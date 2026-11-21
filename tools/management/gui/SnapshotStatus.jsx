import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function SnapshotStatus(){
  const [message,setMessage]=useState("");
  useEffect(()=>{
    let active=true,timer;
    async function refresh(){
      try{
        const {generation,snapshotGeneration,pending,latestSnapshot}=await managementCommand("map-assets","database-status",{});
        const failed=latestSnapshot?.state==="failed" || latestSnapshot?.leaseExpired;
        const state=pending?(failed?"재시도 필요":"대기"):"완료";
        const parts=[`에셋 원장 동기화 ${state}`,`DB ${generation} / 파일 ${snapshotGeneration}`];
        if(pending && failed)parts.push(latestSnapshot.error || "작업자 응답 기한 만료");
        if(latestSnapshot?.finishedAt)parts.push("최근 처리 "+latestSnapshot.finishedAt);
        if(active)setMessage(parts.join(" · "));
      }catch(error){if(active)setMessage("에셋 원장 상태 조회 실패 · "+error.message);}
      if(active)timer=setTimeout(refresh,5000);
    }
    refresh();
    return ()=>{active=false;clearTimeout(timer);};
  },[]);
  return <p role="status">{message}</p>;
}
