import JobStatus from "./JobStatus.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import RecordFolder from "./RecordFolder.jsx";
import GenerationProgress from "./GenerationProgress.jsx";
import {validGenerationEstimate} from "./generationEstimate.mjs";
import {useLiveRefresh} from "./LiveRefresh.jsx";
import KimodoMedia from "./KimodoMedia.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import KimodoKeyframeSave from "./KimodoKeyframeSave.jsx";
import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";

export default function KimodoFrames({id,choose,onDeleted,selectionControls=false}) {
  return <KimodoFramesForJob key={id} id={id} choose={choose} onDeleted={onDeleted} selectionControls={selectionControls}/>;
}

function KimodoFramesForJob({id,choose,onDeleted,selectionControls=false}) {
  const [source,setSource]=useState(null);
  const [revision,refresh]=useState(0);
  const [frame,setFrame]=useState("1");
  const [preview,setPreview]=useState(null);
  const [error,setError]=useState("");
  const [statusError,setStatusError]=useState("");
  const [statusLoading,setStatusLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const retryRef=useRef(null),refreshRef=useRef(null),frameButtonRef=useRef(null);
  const frameRequest=useRef(0),frameController=useRef(null);
  const live=useLiveRefresh(()=>refresh(value=>value+1),!source || ["queued","running"].includes(source.status));
  useEffect(()=>{frameRequest.current++;setPreview(null);setSource(null);setError("");setStatusError("");setBusy(false);return ()=>{frameRequest.current++;frameController.current?.abort();};},[id]);
  useEffect(()=>{frameRequest.current++;frameController.current?.abort();setPreview(null);setError("");setBusy(false);},[source?.attempt]);
  useEffect(()=>{
    let active=true,timedOut=false;
    setStatusLoading(true);
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    untilAborted(managementCommand("kimodo","status",{id},{signal:controller.signal}),controller.signal).then(job=>{
      if(!job.status || (job.status==="completed" && (job.image!=="/kimodo/jobs/"+id+"/attempts/"+job.attempt+"/output-000.png" || !job.attempt || !Number.isInteger(job.source_frame_count) || job.source_frame_count<1)))
        throw new Error("완료된 모션의 원본 프레임을 확인할 수 없습니다.");
      if(active){
        const restoreFocus=document.activeElement===retryRef.current;
        setSource({...job,queried_at:new Date().toISOString()});setStatusError("");
        if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body)refreshRef.current?.focus();});
      }
    }).catch(problem=>{if(active)setStatusError(timedOut ? "작업 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}).finally(()=>{clearTimeout(timeout);if(active)setStatusLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[id,revision]);
  async function inspect(event){
    event.preventDefault();const restoreFocus=event.currentTarget.contains(document.activeElement),requestId=++frameRequest.current,controller=new AbortController();frameController.current=controller;let timedOut=false;const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);setBusy(true);setError("");setPreview(null);
    try{
      const request={job_id:id,attempt_id:source.attempt,frame:Number(frame)};
      const result=await untilAborted(managementCommand("hermes-agent","hermes-kimodo-source-frame",request,{signal:controller.signal}),controller.signal);
      const path="/kimodo/jobs/"+id+"/attempts/"+source.attempt+"/output-"+String(request.frame-1).padStart(3,"0")+".png";
      if(result.image!==path || result.frame!==request.frame || result.attempt_id!==source.attempt || result.job_id!==id)
        throw new Error("선택한 원본 프레임과 조회 결과가 일치하지 않습니다.");
      if(frameRequest.current===requestId)setPreview(result);
    }catch(problem){if(frameRequest.current===requestId)setError(timedOut ? "프레임 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(frameRequest.current===requestId){frameController.current=null;setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body)frameButtonRef.current?.focus();});}}
  }
  return <section ref={!source ? live.ref : undefined} aria-label="Kimodo 원본 프레임">
    <JobIdentifier id={id}/>
    <RecordFolder key={id} service="kimodo" id={id}/>
    {statusLoading && <p role="status">작업 상태를 조회하고 있습니다.{source && " 아래는 마지막으로 조회한 상태입니다."}</p>}
    {statusError && <p role="alert">{statusError}{source && " · 아래 내용은 마지막으로 조회한 상태입니다."}</p>}
    {statusError && !source && <button ref={retryRef} type="button" onClick={()=>refresh(value=>value+1)}>작업 상태 다시 조회</button>}
    {source && <><p><JobStatus state={source.status}/> {source.error}</p>
      {source.status==="missing" && <p role="status">현재 작업 데이터를 찾을 수 없습니다. 이력 색인에는 과거 상태가 남아 있을 수 있으므로 결과와 실제 작업 상태를 확인할 수 없습니다.</p>}
      <GenerationProgress job={{...source,estimate:validGenerationEstimate(source.estimate) ? source.estimate : null}} live={live} supportsProgress={false}/>
      <div className="kimodo-result-actions"><button ref={refreshRef} type="button" onClick={()=>refresh(value=>value+1)}>작업 상태 갱신</button>
      {statusError && <p role="status">작업 상태를 다시 조회할 때까지 이 작업의 제어와 삭제를 사용할 수 없습니다.</p>}
      <GeneratorJobControls showActions={!selectionControls} service="kimodo" id={id} state={source.status} disabled={Boolean(statusError)} refresh={()=>refresh(value=>value+1)}/></div></>}
    {onDeleted && !selectionControls && <HistoryCleanup key={id+"/"+(source?.status || "")} service="kimodo" job={id} state={statusError ? null : source?.status} onDeleted={onDeleted}/>}
    {source?.status==="completed" && <KimodoMedia key={source.attempt} id={id} job={source}/>}
    {source?.status==="completed" && <form onSubmit={inspect}><fieldset disabled={busy}><legend>원본 SOMA 관절 · {source.source_frame_count}프레임</legend>
      <label>원본 프레임 번호 <input type="number" min="1" max={source.source_frame_count} required value={frame}
        onChange={event=>{setFrame(event.target.value);setPreview(null);setError("");}}/></label>
      <button ref={frameButtonRef}>프레임 조회</button>
    </fieldset></form>}
    {error && <p role="alert">{error}</p>}
    {preview && <figure><img src={preview.image} alt={id+" 원본 "+preview.frame+"프레임"} style={{maxWidth:"100%"}}/>
      <figcaption>{preview.frame} / {preview.frame_count} · {preview.fps} fps</figcaption>
      {choose && <button type="button" onClick={()=>choose("Kimodo 원본 프레임",JSON.stringify({job_id:id,attempt_id:source.attempt,frame:preview.frame}))}>이 프레임을 대화 입력에 추가</button>}
      {choose && <KimodoKeyframeSave preview={preview} choose={choose}/>}
    </figure>}
  </section>;
}
