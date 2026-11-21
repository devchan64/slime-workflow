import React, {useEffect, useRef, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {formatCleanupResult} from "./formatCleanupResult.mjs";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import {JobPriority} from "./QueuePriority.jsx";
import {LiveRefreshControl,useLiveRefresh} from "./LiveRefresh.jsx";

const terminalStates=new Set(["completed","failed","cancelled","paused"]);
function statusCommand(service) {
  if (service === "prompt-translation") return null;
  if (service.startsWith("flux-")) return "hermes-flux-source-status";
  if (service === "music-heartmula" || service === "sfx-dasheng-audiogen") return "hermes-audio-source-status";
  return "hermes-video-source-status";
}
async function readState(service,id) {
  const command=statusCommand(service);
  if (!command) {
    const result=await managementCommand(service,"translation-status",{id});
    if (result.id!==id || typeof result.status?.status!=="string") throw new Error("작업 상태가 선택 대상과 일치하지 않습니다.");
    return result.status.status;
  }
  const result=await managementCommand("hermes-agent",command,{service,job_id:id});
  if (result.service!==service || result.job_id!==id || typeof result.job?.status!=="string")
    throw new Error("작업 상태가 선택 대상과 일치하지 않습니다.");
  return result.job.status;
}

export default function SelectedHistoryDeletion({service,id,onDeleted,allowPriority=false}) {
  const mounted=useRef(false);
  const [state,setState]=useState(null),[error,setError]=useState("");
  const [revision,setRevision]=useState(0);
  const [controlActive,setControlActive]=useState(false),[priorityActive,setPriorityActive]=useState(false);
  const [review,setReview]=useState(false),[ack,setAck]=useState(false),[busy,setBusy]=useState(false);
  const live=useLiveRefresh(()=>setRevision(value=>value+1),!busy);
  useEffect(()=>{
    let active=true;
    mounted.current=true;setError("");
    async function read(){
      try {
        const current=await readState(service,id);
        if (!active) return;
        setState(current);setError("");
      } catch(problem) {if(active){setState(null);setError(problem instanceof TypeError ? "작업 상태를 조회할 수 없습니다. 연결을 확인하고 다시 시도하세요." : problem.message);}}
    }
    read();return ()=>{active=false;mounted.current=false;};
  },[service,id,revision]);
  async function remove(){
    if (!review || !ack || !terminalStates.has(state) || busy) return;
    setBusy(true);setError("");
    try {
      const current=await readState(service,id);
      if (!terminalStates.has(current)) throw new Error("작업이 종료 상태가 아닙니다. 상태를 다시 확인하세요.");
      if (!mounted.current) return;
      const result=await managementCommand(service,"history-delete",{id});
      if (result?.status!=="cleared" || result.deleted_jobs!==1 || !Number.isSafeInteger(result.deleted_bytes) || result.deleted_bytes<0)
        throw new Error("삭제 응답을 확인할 수 없습니다.");
      onDeleted(id,formatCleanupResult(result));
    } catch(problem){setState(null);setError(problem.message+" · 삭제 결과가 불확실하면 이력을 다시 조회하세요.");setReview(false);setAck(false);}
    finally{setBusy(false);}
  }
  return <section className="history-selected-actions" aria-label="선택 작업 관리">
    <GeneratorJobControls key={service+"/"+id+"/"+state} service={service} id={id} state={state} showLog={false} showUnavailable resumeEnabled={service!=="wan22-animate2"} disabled={busy || review || priorityActive} onInteractionChange={setControlActive} refresh={()=>setRevision(value=>value+1)}
      renderPriority={allowPriority ? controlsDisabled=>state === "queued" ?
        <JobPriority inline disabled={busy || review || controlActive} onInteractionChange={setPriorityActive} key={service+"/"+id} service={service} id={id} call={(command,payload)=>managementCommand("hermes-agent","hermes-"+command,payload)}/> :
        <button className="history-action-priority" type="button" disabled aria-describedby="priority-help">우선 실행 검토</button> : null}/>
    {allowPriority && <p className="history-action-detail" id="priority-help">{state===null ? "현재 작업 상태를 확인해야 우선 실행을 검토할 수 있습니다." : state==="queued" ? "대기 순서는 검토할 때 다시 확인합니다." : "우선 실행은 대기 중인 작업에서 사용할 수 있습니다."}</p>}
    <button ref={live.ref} className="history-action-delete" type="button" disabled={busy || review || controlActive || priorityActive || !terminalStates.has(state)} aria-describedby="selected-delete-help" onClick={()=>{setReview(true);setAck(false);}}>선택 이력 삭제 검토</button>
    <p className="history-action-detail" id="selected-delete-help">{state===null ? "선택 작업의 상태를 확인할 수 있어야 삭제할 수 있습니다." : terminalStates.has(state) ? "삭제 전에 대상과 범위를 확인합니다." : "종료된 작업만 삭제할 수 있습니다. 종료 후 다시 확인하세요."}</p>
    <div className="history-action-detail"><LiveRefreshControl live={live} label="선택 작업 상태 자동 갱신"/> <button type="button" disabled={busy} onClick={()=>setRevision(value=>value+1)}>작업 상태 다시 확인</button></div>
    {error && <p className="history-action-detail" role="alert">{error}</p>}
    {review && <section className="history-action-detail history-confirmation">
      <p>{service} · 선택 작업 {id}</p>
      <p>작업 폴더의 입력 사본·중간 산출물·결과·모든 실행 시도의 요청·상태·로그와 이력 기록을 삭제하며 복구할 수 없습니다. 외부 원본과 등록된 에셋은 보존합니다.</p>
      <label><input type="checkbox" checked={ack} disabled={busy} onChange={e=>setAck(e.target.checked)}/>삭제 범위와 복구 불가를 확인했습니다.</label>
      <div className="choice-buttons"><button type="button" disabled={busy} onClick={()=>{setReview(false);setAck(false);}}>삭제 취소</button>
      <button type="button" disabled={busy || !ack || !terminalStates.has(state)} onClick={remove}>확인한 이력 삭제</button></div>
    </section>}
  </section>;
}
