import React,{useEffect,useRef,useState} from "react";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {readHandoffHistoryResult} from "./handoffHistoryResult.mjs";

export function GpuHandoffDisclosure({session}){
  const [opened,setOpened]=useState(false);
  return <details onToggle={event=>{
    if(event.target===event.currentTarget && event.currentTarget.open)setOpened(true);
  }}>
    <summary>이 대화의 GPU 양도 이력</summary>
    {opened && <GpuHandoffHistory session={session}/>}
  </details>;
}

export default function GpuHandoffHistory({session}){
  return <HandoffHistoryForSession key={session} session={session}/>;
}

function HandoffHistoryForSession({session}){
  const [rows,setRows]=useState(null),[busy,setBusy]=useState(true),[error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const activeRequest=useRef(null),rowRevision=useRef(0);
  async function refresh(){
    activeRequest.current?.abort();
    const controller=new AbortController();activeRequest.current=controller;
    const revision=rowRevision.current;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await untilAborted(managementCommand("hermes-agent","hermes-gpu-handoff-list",{session_id:session},{signal:controller.signal}),controller.signal);
      if(activeRequest.current!==controller || controller.signal.aborted)return;
      const validated=readHandoffHistoryResult(result,session,revision,rowRevision.current);
      setRows(validated);setCheckedAt(new Date());
    }catch(problem){if(activeRequest.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut?"GPU 양도 이력 조회 시간이 초과됐습니다. 다시 조회하세요.":problem instanceof TypeError?"GPU 양도 이력에 연결하지 못했습니다. 다시 조회하세요.":problem.message || "GPU 양도 이력을 확인할 수 없습니다.");}
    finally{clearTimeout(timer);if(activeRequest.current===controller){activeRequest.current=null;setBusy(false);}}
  }
  useEffect(()=>{setRows(null);setCheckedAt(null);refresh();return ()=>{activeRequest.current?.abort();activeRequest.current=null;};},[session]);
  return <section className="gpu-handoff-history" aria-label="GPU 양도 이력">
      <p>이 대화의 최근 양도 최대 20건을 최근 변경순으로 표시합니다.</p>
      <button type="button" aria-disabled={busy} onClick={()=>{if(!busy)refresh();}}>{busy?"조회 중":"이력 새로고침"}</button>
      {checkedAt && <p>화면 수신 시각 · {checkedAt.toLocaleString("ko-KR")}</p>}
      {busy && <p role="status">GPU 양도 이력을 불러오는 중입니다.{rows && " 아래는 마지막 조회 결과이며 이력 조작은 잠시 중단됩니다."}</p>}
      {error && <p role="alert">{error}</p>}
      {error && rows && <p>아래에는 마지막으로 조회한 이력이 표시됩니다.</p>}
      {rows && !rows.length && <p>{error || busy ? "마지막 조회에서 이 대화의 양도 기록이 없었습니다." : "이 대화의 양도 기록이 없습니다."}</p>}
      {rows?.length>0 && <fieldset disabled={busy} className="gpu-handoff-history-items"><legend>조회된 양도 이력</legend>{rows.map(row=><GpuHandoffStatus key={row.id} session={session} id={row.id} service={row.service} status={row} onUpdate={value=>{rowRevision.current++;setRows(current=>current?.map(item=>item.id===row.id?{...item,...value}:item) || current);}}><p>대상 · {row.service}</p><p>최근 변경 · {Number.isNaN(Date.parse(row.updated_at)) ? "확인 불가" : new Date(row.updated_at).toLocaleString("ko-KR")}</p></GpuHandoffStatus>)}</fieldset>}
  </section>;
}
