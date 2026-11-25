import React,{useEffect,useId,useRef,useState} from "react";
import QueuePagination from "./QueuePagination.jsx";
import StatusTag from "./StatusTag.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
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
  const loadingId=useId();
  const [rows,setRows]=useState(null),[busy,setBusy]=useState(true),[error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null),[page,setPage]=useState(0),[size,setSize]=useState(5),[total,setTotal]=useState(0);
  const activeRequest=useRef(null),rowRevision=useRef(0);
  async function refresh(){
    activeRequest.current?.abort();
    const controller=new AbortController();activeRequest.current=controller;
    const revision=rowRevision.current;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await untilAborted(managementCommand("hermes-agent","hermes-gpu-handoff-list",{session_id:session,offset:page*size,limit:size},{signal:controller.signal}),controller.signal);
      if(activeRequest.current!==controller || controller.signal.aborted)return;
      const validated=readHandoffHistoryResult(result,session,revision,rowRevision.current);
      if(!Number.isSafeInteger(result.total) || result.total<0 || result.offset!==page*size || result.limit!==size)throw new Error("페이지 정보가 일치하지 않습니다.");
      if(page>0 && page*size>=result.total){setPage(Math.max(0,Math.ceil(result.total/size)-1));return;}
      setRows(validated);setTotal(result.total);setCheckedAt(new Date());
    }catch(problem){if(activeRequest.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut?"GPU 양도 이력 조회 시간이 초과됐습니다. 다시 조회하세요.":problem instanceof TypeError?"GPU 양도 이력에 연결하지 못했습니다. 다시 조회하세요.":problem?.message || "GPU 양도 이력을 확인할 수 없습니다. 다시 조회하세요.");}
    finally{clearTimeout(timer);if(activeRequest.current===controller){activeRequest.current=null;setBusy(false);}}
  }
  useEffect(()=>{setRows(null);setCheckedAt(null);refresh();return ()=>{activeRequest.current?.abort();activeRequest.current=null;};},[session,page,size]);
  return <section className="gpu-handoff-history" aria-label="GPU 양도 이력">
      <p>이 대화의 양도 기록을 최근 변경순으로 표시합니다.</p>
      <button type="button" aria-disabled={busy} aria-describedby={busy?loadingId:undefined} onClick={()=>{if(!busy)refresh();}}>{busy?"조회 중":"이력 새로고침"}</button>
      {checkedAt && <p>화면 수신 시각 · {checkedAt.toLocaleString("ko-KR")}</p>}
      {busy && <p id={loadingId} role="status">GPU 양도 이력을 불러오는 중입니다.{rows && " 아래는 마지막 조회 결과이며 이력 조작은 잠시 중단됩니다."}</p>}
      {error && <p role="alert">{error}</p>}
      {error && rows && <p>아래에는 마지막으로 조회한 이력이 표시됩니다.</p>}
      {rows && !rows.length && <p>{error || busy ? "마지막 조회에서 이 대화의 양도 기록이 없었습니다." : "이 대화의 양도 기록이 없습니다."}</p>}
      {rows?.length>0 && <table className="handoff-history-table"><thead><tr><th scope="col">상태</th><th scope="col">대상·작업</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td><StatusTag tone={row.state==='ready'?'completed':row.state==='needs_attention'?'failed':'pending'}>{({approved:'예약됨',waiting_release:'해제 대기',submitting:'접수 중',running:'생성 중',reload_queued:'재적재 대기',reloading:'재적재 중',ready:'재적재 완료',cancelled:'취소',rejected:'실패',needs_attention:'확인 필요'})[row.state] || row.state}</StatusTag></td><td><strong>{row.service}</strong>{row.job_id && <JobIdentifier id={row.job_id} compact/>}<small>변경 · {Number.isNaN(Date.parse(row.updated_at))?'확인 불가':new Date(row.updated_at).toLocaleString('ko-KR')}</small><details><summary>접수 ID와 상세</summary><JobIdentifier id={row.id} label="접수 ID" compact/>{row.reason && <p>{row.reason}</p>}</details></td></tr>)}</tbody></table>}
      {rows && <QueuePagination page={page} size={size} total={total} label="GPU 양도 이력 페이지" sizes={[5,10,20]} onPage={setPage} onSize={value=>{setSize(value);setPage(0);}}/>}
  </section>;
}
