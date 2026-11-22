import React, {useEffect,useId,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ModelInventory from "./ModelInventory.jsx";

export function modelPrepareReason(status,error,sending,checking=false) {
  return sending ? "다운로드 요청을 접수하고 있습니다." : checking ? "모델 준비 상태를 확인하고 있습니다." : error ? "모델 준비 상태를 다시 확인하세요." : !status ? "모델 준비 상태를 확인하고 있습니다." : ["queued","running"].includes(status.preparation_status) ? "모델 준비가 진행 중입니다." : status.ready ? "모델 파일이 이미 준비되어 있습니다." : status.can_prepare===false || !status.prepare_request ? (status.prepare_blocked_reason || "현재 상태에서는 다운로드 요청을 사용할 수 없습니다.") : "";
}

export function modelReadinessPollDelay(status,manage) {
  return ["queued","running"].includes(status.preparation_status) ? 5000 : manage ? 30000 : null;
}

export function ModelDownloadButton({sending,reason,reasonId,onPrepare}) {
  return <><button disabled={Boolean(reason)} aria-describedby={reason ? reasonId : undefined} onClick={onPrepare}>
    {sending?"접수 중…":"모델 다운로드 · 이어받기"}
  </button>{reason && <p id={reasonId}>{reason}</p>}</>;
}

export function ModelReadinessMessage({service,status,error,hasStatusSummary=false}) {
  let text="모델 상태 확인 중…";
  if(error) text="모델 상태 조회 실패 · "+error;
  else if(status) {
    const ready=status.generation_ready ?? status.ready;
    if(hasStatusSummary) {
      text=status.message.replace(/^(?:모델 파일 준비 완료 · |모델 준비 필요: )/,"");
      if(!ready && status.missing?.length) text="준비가 필요한 파일 · "+status.missing.join(", ");
    } else if(service==="wan22-animate2") text=ready && status.message.startsWith("모델 파일 준비 완료") ? status.message : (ready ? "모델 파일 준비 완료" : "모델 파일 준비 필요")+" · "+status.message;
    else text=(["animationgpt","wan22-fighting-lora","wan22-vace-lightning","writer-agent"].includes(service) ? (ready?"모델 파일 준비 완료":"모델 파일 준비 필요") : (ready?"생성 준비 완료":"모델 준비 필요"))+" · "+status.message;
  }
  return <p role="status">{text}</p>;
}

export default function ModelReadiness({service, manage=false, hasStatusSummary=false, onStatus, onError}) {
  const session=new URLSearchParams(location.search).get("session");
  const modelQuery=new URLSearchParams({model:service,...(session?{session}:{})});
  const [revision,setRevision]=useState(0);
  const [status,setStatus]=useState(null);
  const [checkedAt,setCheckedAt]=useState(null);
  const [error,setError]=useState("");
  const [sending,setSending]=useState(false);
  const [checking,setChecking]=useState(true);
  const [notice,setNotice]=useState("");
  const reasonId=useId();
  useEffect(()=>{setCheckedAt(null);},[service]);
  useEffect(()=>{
    let active=true,timer,controller;
    setError("");onError?.("");setStatus(null);onStatus?.(null);
    async function read() {
      if(active)setChecking(true);
      controller=new AbortController();let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        let next;
        if (manage) {
          const response=await fetch("/management/assistant/model-readiness/"+encodeURIComponent(service), {cache:"no-store",signal:controller.signal});
          if (!response.ok) throw new Error("모델 준비 상태를 조회할 수 없습니다.");
          next=await response.json();
        } else next=await managementCommand(service,"model-status",{},{signal:controller.signal});
        if(!active)return;
        if(typeof next.ready!=="boolean" || typeof next.message!=="string") throw new Error("모델 상태 응답을 확인하세요.");
        setStatus(next);setCheckedAt(new Date());onStatus?.(next);onError?.("");
        const delay=modelReadinessPollDelay(next,manage);
        if(delay!==null)timer=setTimeout(read,delay);
      } catch(problem) {
        if(active){const message=timedOut ? "모델 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem);setStatus(null);onStatus?.(null);setError(message);onError?.(message);}
      } finally {
        clearTimeout(timeout);
        if(active)setChecking(false);
      }
    }
    read();
    return ()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[service,revision,manage,onStatus,onError]);
  async function prepare() {
    setSending(true);
    setNotice("");
    try {
      const target=status.prepare_request;
      await managementCommand(target.service,target.command,target.payload);
      setNotice("모델 준비 요청을 접수했습니다.");
    } catch(problem) {
      setNotice("모델 준비 요청의 접수 결과를 확인하지 못했습니다. 다시 요청하기 전에 준비 상태와 다운로드 이력을 확인하세요. · "+problem.message);
    } finally {
      setStatus(null);
      setRevision(value=>value+1);
      setSending(false);
    }
  }
  const prepareReason=modelPrepareReason(status,error,sending,checking);
  return <section aria-label="모델 준비 상태">
    <ModelReadinessMessage service={service} status={status} error={error} hasStatusSummary={hasStatusSummary}/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    <button disabled={checking} onClick={()=>setRevision(value=>value+1)}>{checking ? "모델 준비 상태 확인 중…" : "모델 준비 상태 확인"}</button>
    {manage && <>
      <ModelDownloadButton sending={sending} reason={prepareReason} reasonId={reasonId} onPrepare={prepare}/>
      {notice && <p role="status">{notice}</p>}
    </>}
    <ModelInventory service={service}/>
    {!manage && <a href={"/management/frame/model-management/?"+modelQuery}>모델 관리로 이동</a>}
  </section>;
}
