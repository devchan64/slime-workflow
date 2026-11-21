import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ModelInventory from "./ModelInventory.jsx";

export default function ModelReadiness({service, manage=false}) {
  const [revision,setRevision]=useState(0);
  const [status,setStatus]=useState(null);
  const [error,setError]=useState("");
  const [sending,setSending]=useState(false);
  const [notice,setNotice]=useState("");
  useEffect(()=>{
    let active=true,timer;
    setError("");setStatus(null);
    async function read() {
      try {
        let next;
        if (manage) {
          const response=await fetch("/management/assistant/model-readiness/"+encodeURIComponent(service), {cache:"no-store"});
          if (!response.ok) throw new Error("모델 준비 상태를 조회할 수 없습니다.");
          next=await response.json();
        } else next=await managementCommand(service,"model-status",{});
        if(!active)return;
        if(typeof next.ready!=="boolean" || typeof next.message!=="string") throw new Error("모델 상태 응답을 확인하세요.");
        setStatus(next);
        if(manage || ["queued","running"].includes(next.preparation_status))timer=setTimeout(read,["queued","running"].includes(next.preparation_status)?5000:30000);
      } catch(problem) {
        if(active){setStatus(null);setError(problem.message);}
      }
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[service,revision,manage]);
  async function prepare() {
    setSending(true);
    setNotice("");
    try {
      const target=status.prepare_request;
      await managementCommand(target.service,target.command,target.payload);
      setNotice("모델 준비 요청을 접수했습니다.");
    } catch(problem) {
      setNotice("모델 준비 요청 실패 · "+problem.message);
    } finally {
      setStatus(null);
      setRevision(value=>value+1);
      setSending(false);
    }
  }
  return <section aria-label="모델 준비 상태">
    <p role="status">{error ? "모델 상태 조회 실패 · "+error : status ?
      ((status.generation_ready ?? status.ready)?"생성 준비 완료":"모델 준비 필요")+" · "+status.message : "모델 상태 확인 중…"}</p>
    <button onClick={()=>setRevision(value=>value+1)}>모델 준비 상태 확인</button>
    {manage && <>
      <button disabled={sending || !status?.prepare_request || status.ready || status.can_prepare===false || ["queued","running"].includes(status.preparation_status)} onClick={prepare}>
        {sending?"접수 중…":"모델 다운로드 · 이어받기"}
      </button>
      {status?.prepare_blocked_reason && <p>{status.prepare_blocked_reason}</p>}
      {notice && <p role="status">{notice}</p>}
    </>}
    <ModelInventory service={service}/>
    {location.pathname.replace(/\/$/,"") !== "/management/assistant/models" && <a href="/management/assistant/models/">모델별 상태 조회</a>}
    <a href="/management/?tool=model-management&category=model-management">모델 관리로 이동</a>
  </section>;
}
