import React,{useEffect,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";

export default function SnapshotStatus(){
  const [message,setMessage]=useState("에셋 원장 동기화 상태 조회 중…");
  useEffect(()=>{
    let active=true,timer,controller;
    async function refresh(){
      controller=new AbortController();
      const current=controller;
      const timeout=setTimeout(()=>current.abort(),30000);
      try{
        const result=await untilAborted(managementCommand("map-assets","database-status",{},{signal:current.signal}),current.signal);
        if(!result || !Number.isSafeInteger(result.generation) || result.generation<0 || !Number.isSafeInteger(result.snapshotGeneration) || result.snapshotGeneration<0 || result.snapshotGeneration>result.generation || typeof result.pending!=="boolean" || result.pending!==(result.generation>result.snapshotGeneration))throw new Error("상태 응답을 확인할 수 없습니다.");
        const {generation,snapshotGeneration,pending,latestSnapshot}=result;
        if(latestSnapshot!=null && (typeof latestSnapshot!=="object" || Array.isArray(latestSnapshot) || !["pending","running","completed","failed"].includes(latestSnapshot.state) || !Number.isSafeInteger(latestSnapshot.generation) || latestSnapshot.generation<0 || typeof latestSnapshot.leaseExpired!=="boolean"))throw new Error("원장 처리 상태 응답을 확인할 수 없습니다.");
        const failed=latestSnapshot?.state==="failed" || latestSnapshot?.leaseExpired;
        const state=pending?(failed?"재시도 필요":"대기"):"완료";
        const parts=[`에셋 원장 동기화 ${state}`,`DB ${generation} / 원장 반영 ${snapshotGeneration}`];
        if(pending && failed)parts.push(latestSnapshot.error || "작업자 응답 기한 만료");
        if(latestSnapshot?.finishedAt)parts.push("최근 처리 "+latestSnapshot.finishedAt);
        if(active)setMessage(parts.join(" · "));
      }catch(error){if(active)setMessage(error?.name==="AbortError" ? "에셋 원장 상태 조회 시간이 초과됐습니다. 다시 확인합니다." : "에셋 원장 상태 조회 실패 · "+(error instanceof TypeError ? "서버 연결을 확인하세요." : error.message));}
      finally{clearTimeout(timeout);}
      if(active)timer=setTimeout(refresh,5000);
    }
    refresh();
    return ()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[]);
  return <p role="status">{message}</p>;
}
