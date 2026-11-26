import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ModelInventory from "./ModelInventory.jsx";
import {startModelReadinessPoller} from "./modelReadinessPoller.mjs";

export function modelPrepareReason(status,error,sending,checking=false) {
  return sending ? "다운로드 요청을 접수하고 있습니다." : checking ? "모델 준비 상태를 확인하고 있습니다." : error ? "모델 준비 상태를 다시 확인하세요." : !status ? "모델 준비 상태를 확인하고 있습니다." : ["queued","running"].includes(status.preparation_status) ? "모델 준비가 진행 중입니다." : status.ready ? "모델 파일이 이미 준비되어 있습니다." : status.can_prepare===false || !status.prepare_request ? (status.prepare_blocked_reason || "현재 상태에서는 다운로드 요청을 사용할 수 없습니다.") : "";
}

export function modelReadinessPollDelay(status,manage) {
  return ["queued","running"].includes(status.preparation_status) ? 5000 : manage ? 30000 : null;
}

export function validModelReadiness(status) {
  if(!status || typeof status!=="object" || Array.isArray(status) || typeof status.ready!=="boolean" || typeof status.message!=="string" ||
     (status.generation_ready!=null && typeof status.generation_ready!=="boolean") ||
     (status.can_prepare!=null && typeof status.can_prepare!=="boolean") ||
     (status.preparation_status!=null && typeof status.preparation_status!=="string") ||
     (status.prepare_blocked_reason!=null && typeof status.prepare_blocked_reason!=="string") ||
     (status.missing!=null && (!Array.isArray(status.missing) || status.missing.some(item=>typeof item!=="string"))))return false;
  const request=status.prepare_request;
  return request==null || Boolean(typeof request==="object" && !Array.isArray(request) &&
    typeof request.service==="string" && request.service.length>0 && ["prepare","download-model"].includes(request.command) &&
    request.payload && typeof request.payload==="object" && !Array.isArray(request.payload));
}

export function ModelDownloadButton({sending,reason,reasonId,onPrepare}) {
  return <><button type="button" disabled={Boolean(reason)} aria-describedby={reason ? reasonId : undefined} onClick={onPrepare}>
    {sending?"접수 중…":"모델 다운로드 · 이어받기"}
  </button>{reason && <p id={reasonId}>{reason}</p>}</>;
}

export function ModelReadinessMessage({service,status,error,hasStatusSummary=false,id}) {
  let text="모델 상태 확인 중…";
  if(error) text="모델 상태 조회 실패 · "+error;
  else if(status) {
    const ready=["wan21-t2v-assets","wan21-i2v-assets","wan21-i2v-attack-lora"].includes(service) ? status.ready : (status.generation_ready ?? status.ready);
    if(hasStatusSummary) {
      text=status.message.replace(/^(?:모델 파일 준비 완료 · |모델 준비 필요: )/,"");
      if(!ready && status.missing?.length) text="준비가 필요한 파일 · "+status.missing.join(", ");
    } else if(service==="wan22-animate2") text=ready && status.message.startsWith("모델 파일 준비 완료") ? status.message : (ready ? "모델 파일 준비 완료" : "모델 파일 준비 필요")+" · "+status.message;
    else text=(["animationgpt","wan22-fighting-lora","wan22-vace-lightning","wan22-animate2-lightx2v","wan22-vace-q8","wan22-i2v-assets","wan21-t2v-assets","wan21-i2v-assets","wan21-i2v-attack-lora","writer-agent"].includes(service) ? (ready?"모델 파일 준비 완료":"모델 파일 준비 필요") : (ready?"생성 준비 완료":"모델 준비 필요"))+" · "+status.message;
  }
  return <p id={id} role={error ? "alert" : "status"}>{text}</p>;
}

export default function ModelReadiness(props) {
  return <ModelReadinessForService key={props.service} {...props}/>;
}

function ModelReadinessForService({service, modelManagementService=service, manage=false, hasStatusSummary=false, onStatus, onError, session:sessionOverride}) {
  const session=sessionOverride ?? new URLSearchParams(location.search).get("session");
  const modelQuery=new URLSearchParams({model:modelManagementService,...(session?{session}:{})});
  const [revision,setRevision]=useState(0);
  const [status,setStatus]=useState(null);
  const [checkedAt,setCheckedAt]=useState(null);
  const [error,setError]=useState("");
  const [sending,setSending]=useState(false);
  const [checking,setChecking]=useState(true);
  const [notice,setNotice]=useState(""),[noticeError,setNoticeError]=useState(false);
  const preparing=useRef(false),readiness=useRef({status:null,error:"",checking:true}),poller=useRef(null);
  const sectionRef=useRef(null);
  const reasonId=useId(),pendingId=useId();
  useEffect(()=>{
    if(preparing.current)return;
    readiness.current={status:null,error:"",checking:true};setError("");onError?.("");
    const stop=startModelReadinessPoller({
      initialRetryDelay:manage ? 30000 : null,
      validate:validModelReadiness,
      delayForStatus:next=>modelReadinessPollDelay(next,manage),
      onStart:()=>{readiness.current.checking=true;readiness.current.status=null;setChecking(true);onStatus?.(null);},
      read:async signal=>{
        if (manage) {
          const response=await fetch("/management/assistant/model-readiness/"+encodeURIComponent(service), {cache:"no-store",signal});
          if (!response.ok) throw new Error("모델 준비 상태를 조회할 수 없습니다.");
          try{return await response.json();}
          catch(problem){signal.throwIfAborted();throw new Error("모델 준비 상태 응답을 확인할 수 없습니다. 다시 확인하세요.");}
        }
        return managementCommand(service,"model-status",{},{signal});
      },
      onSuccess:next=>{
        readiness.current.status=next;readiness.current.error="";setStatus(next);setCheckedAt(new Date());setError("");onStatus?.(next);onError?.("");
      },
      onFailure:(problem,timedOut)=>{const message=timedOut ? "모델 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem);readiness.current.status=null;readiness.current.error=message;onStatus?.(null);setError(message);onError?.(message);},
      onFinish:()=>{readiness.current.checking=false;setChecking(false);},
    });
    poller.current=stop;
    return ()=>{stop();if(poller.current===stop)poller.current=null;};
  },[service,revision,manage,onStatus,onError]);
  async function prepare() {
    const current=readiness.current;
    if(preparing.current || modelPrepareReason(current.status,current.error,false,current.checking))return;
    const restoreFocus=sectionRef.current?.contains(document.activeElement);
    preparing.current=true;setSending(true);
    poller.current?.();poller.current=null;
    setNotice("");setNoticeError(false);
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try {
      const target=current.status.prepare_request;
      await untilAborted(managementCommand(target.service,target.command,target.payload,{signal:controller.signal}),controller.signal);
      setNotice("모델 준비 요청을 보냈습니다. 현재 준비 상태를 확인하세요.");
    } catch(problem) {
      setNoticeError(true);
      setNotice("모델 준비 요청의 접수 결과를 확인하지 못했습니다. 다시 요청하기 전에 준비 상태와 다운로드 이력을 확인하세요. · "+(timedOut ? "응답 시간이 초과됐습니다." : requestErrorMessage(problem)));
    } finally {
      clearTimeout(timeout);
      readiness.current.status=null;readiness.current.checking=true;setStatus(null);setChecking(true);
      preparing.current=false;setSending(false);
      setRevision(value=>value+1);
      if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body)sectionRef.current?.focus({preventScroll:true});});
    }
  }
  function refreshReadiness(){
    if(readiness.current.checking || preparing.current)return;
    readiness.current.checking=true;setChecking(true);setRevision(value=>value+1);
  }
  const prepareReason=modelPrepareReason(status,error,sending,checking);
  return <section ref={sectionRef} className="model-readiness" tabIndex={-1} aria-label="모델 준비 상태">
    <ModelReadinessMessage service={service} status={status} error={error} hasStatusSummary={hasStatusSummary} id={checking && !status && !sending ? pendingId : undefined}/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && status && <><p>아래는 마지막 조회 결과입니다. 준비 상태를 다시 확인하기 전에는 작업에 사용할 수 없습니다.</p><ModelReadinessMessage service={service} status={status} hasStatusSummary={hasStatusSummary}/></>}
    {sending ? <p id={pendingId} role="status">모델 준비 요청을 접수하고 있습니다.</p> : checking && status && <p id={pendingId} role="status">모델 준비 상태를 다시 확인하고 있습니다. 위 상태는 마지막 조회 결과입니다.</p>}
    <button type="button" aria-disabled={checking || sending} aria-describedby={checking || sending ? pendingId : undefined} onClick={refreshReadiness}>{sending ? "준비 요청 접수 중…" : checking ? "모델 준비 상태 확인 중…" : "모델 준비 상태 확인"}</button>
    {manage && <>
      <ModelDownloadButton sending={sending} reason={prepareReason} reasonId={reasonId} onPrepare={prepare}/>
      {notice && <p role={noticeError ? "alert" : "status"}>{notice}</p>}
    </>}
    <ModelInventory service={modelManagementService}/>
    {!manage && <a href={"/management/frame/model-management/?"+modelQuery}>모델 관리로 이동</a>}
  </section>;
}
