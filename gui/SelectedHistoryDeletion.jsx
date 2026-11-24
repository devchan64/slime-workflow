import React, {useCallback, useEffect, useId, useRef, useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {formatCleanupResult,validCleanupResult} from "./formatCleanupResult.mjs";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import {JobPriority} from "./QueuePriority.jsx";
import {useLiveRefresh} from "./LiveRefresh.jsx";
import JobIdentifier from "./JobIdentifier.jsx";

const terminalStates=new Set(["completed","failed","cancelled","paused"]);
function statusCommand(service) {
  if (service === "prompt-translation") return null;
  if (service.startsWith("flux-")) return "hermes-flux-source-status";
  if (service === "music-heartmula" || service === "sfx-dasheng-audiogen") return "hermes-audio-source-status";
  return "hermes-video-source-status";
}
async function readState(service,id,signal) {
  const command=statusCommand(service);
  if (!command) {
    const result=await untilAborted(managementCommand(service,"translation-status",{id},{signal}),signal);
    if (result.id!==id || typeof result.status?.status!=="string") throw new Error("작업 상태가 선택 대상과 일치하지 않습니다.");
    return result.status.status;
  }
  const result=await untilAborted(managementCommand("hermes-agent",command,{service,job_id:id},{signal}),signal);
  if (result.service!==service || result.job_id!==id || typeof result.job?.status!=="string")
    throw new Error("작업 상태가 선택 대상과 일치하지 않습니다.");
  return result.job.status;
}

export default function SelectedHistoryDeletion({service,id,onDeleted,allowPriority=false}) {
  return <SelectedHistoryDeletionForJob key={JSON.stringify([service,id])} service={service} id={id} onDeleted={onDeleted} allowPriority={allowPriority}/>;
}

function SelectedHistoryDeletionForJob({service,id,onDeleted,allowPriority=false}) {
  const mounted=useRef(false),deleteButton=useRef(null),reviewRef=useRef(null);
  const priorityHelp=useId(),deleteHelp=useId();
  const [state,setState]=useState(null),[error,setError]=useState("");
  const [revision,setRevision]=useState(0);
  const [controlActive,setControlActive]=useState(false),[priorityActive,setPriorityActive]=useState(false);
  const [review,setReview]=useState(false),[ack,setAck]=useState(false),[busy,setBusy]=useState(false);
  const live=useLiveRefresh(()=>setRevision(value=>value+1),!busy && ["queued","running"].includes(state));
  const setDeleteButton=useCallback(node=>{deleteButton.current=node;live.ref(node);},[live.ref]);
  useEffect(()=>{
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    mounted.current=true;setError("");
    async function read(){
      try {
        const current=await readState(service,id,controller.signal);
        if (!active) return;
        setState(current);setError("");
      } catch(problem) {if(active){setState(null);setError(timedOut ? "작업 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : problem instanceof TypeError ? "작업 상태를 조회할 수 없습니다. 연결을 확인하고 다시 시도하세요." : problem.message);}}
      finally{clearTimeout(timeout);}
    }
    read();return ()=>{active=false;mounted.current=false;clearTimeout(timeout);controller.abort();};
  },[service,id,revision]);
  async function remove(){
    if (!review || !ack || !terminalStates.has(state) || busy) return;
    setBusy(true);setError("");
    let deleteStarted=false;
    try {
      const controller=new AbortController();let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      let current;
      try{current=await readState(service,id,controller.signal);}
      catch(problem){if(timedOut)throw new Error("삭제 전 상태 조회 시간이 초과됐습니다. 다시 확인하세요.");throw problem;}
      finally{clearTimeout(timeout);}
      if (!terminalStates.has(current)) throw new Error("작업이 종료 상태가 아닙니다. 상태를 다시 확인하세요.");
      if (!mounted.current) return;
      deleteStarted=true;
      const result=await managementCommand(service,"history-delete",{id});
      if (!validCleanupResult(result,true))
        throw new Error("삭제 응답을 확인할 수 없습니다.");
      onDeleted(id,formatCleanupResult(result));
    } catch(problem){setState(null);setError(problem.message+(deleteStarted ? " · 삭제 결과가 불확실하면 이력을 다시 조회하세요." : " · 삭제 요청은 전송하지 않았습니다."));setReview(false);setAck(false);}
    finally{setBusy(false);}
  }
  return <section className="history-selected-actions" aria-label="선택 작업 관리">
    <GeneratorJobControls key={service+"/"+id+"/"+state} service={service} id={id} state={state} showLog={false} showUnavailable resumeEnabled={!['wan22-animate2','wan21-i2v','wan21-t2v'].includes(service)} disabled={busy || review || priorityActive} onInteractionChange={setControlActive} refresh={()=>setRevision(value=>value+1)}
      renderPriority={allowPriority ? controlsDisabled=>state === "queued" ?
        <JobPriority inline disabled={busy || review || controlActive} onInteractionChange={setPriorityActive} key={service+"/"+id} service={service} id={id} call={(command,payload)=>managementCommand("hermes-agent","hermes-"+command,payload)}/> :
        <button className="history-action-priority" type="button" disabled aria-describedby={priorityHelp}>우선 실행 검토</button> : null}/>
    {allowPriority && <p className="history-action-detail" id={priorityHelp}>{state===null ? "현재 작업 상태를 확인해야 우선 실행을 검토할 수 있습니다." : state==="queued" ? "대기 순서는 검토할 때 다시 확인합니다." : "우선 실행은 대기 중인 작업에서 사용할 수 있습니다."}</p>}
    <button ref={setDeleteButton} className="history-action-delete" type="button" disabled={busy || review || controlActive || priorityActive || !terminalStates.has(state)} aria-describedby={deleteHelp} onClick={()=>{setReview(true);setAck(false);requestAnimationFrame(()=>reviewRef.current?.focus());}}>선택 이력 삭제 검토</button>
    <p className="history-action-detail" id={deleteHelp}>{state===null ? "선택 작업의 상태를 확인할 수 있어야 삭제할 수 있습니다." : terminalStates.has(state) ? "삭제 전에 대상과 범위를 확인합니다." : "종료된 작업만 삭제할 수 있습니다. 종료 후 다시 확인하세요."}</p>
    {error && <div className="history-action-detail"><p role="alert">{error}</p>
      <button type="button" disabled={busy} onClick={event=>{event.currentTarget.closest(".generator-history-item")?.querySelector(".generator-history-select")?.focus();setRevision(value=>value+1);}}>작업 상태 다시 확인</button></div>}
    {review && <section ref={reviewRef} tabIndex={-1} aria-label="선택 이력 삭제 확인" className="history-action-detail history-confirmation">
      <p>{service} · 선택 작업</p><JobIdentifier id={id} compact/>
      <p>작업 폴더의 입력 사본·중간 산출물·결과·모든 실행 시도의 요청·상태·로그와 이력 기록을 삭제하며 복구할 수 없습니다. 외부 원본과 등록된 에셋은 보존합니다.</p>
      <label><input type="checkbox" checked={ack} disabled={busy} onChange={e=>setAck(e.target.checked)}/>삭제 범위와 복구 불가를 확인했습니다.</label>
      <div className="choice-buttons"><button type="button" disabled={busy} onClick={()=>{setReview(false);setAck(false);requestAnimationFrame(()=>deleteButton.current?.focus());}}>삭제 취소</button>
      <button type="button" disabled={busy || !ack || !terminalStates.has(state)} onClick={remove}>확인한 이력 삭제</button></div>
    </section>}
  </section>;
}
