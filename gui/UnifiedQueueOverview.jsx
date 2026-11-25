import React,{useEffect,useState} from "react";
import QueuePagination from "./QueuePagination.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {untilAborted} from "./managementCommand.js";

export function validSnapshot(value,session){
  return value?.session_id===session && Array.isArray(value.entries) && typeof value.note==="string" && value.entries.every(row=>
    row && ["chat","task"].includes(row.kind) && typeof row.id==="string" && /^[A-Za-z0-9_-]{1,120}$/.test(row.id) &&
    typeof row.order_ns==="string" && /^[0-9]{1,20}$/.test(row.order_ns) && Number.isSafeInteger(row.priority) &&
    (row.wait_reason===undefined || typeof row.wait_reason==="string") &&
    ["queued","dispatching","gpu_queued"].includes(row.state) &&
    (row.kind!=="chat" || (typeof row.own_session==="boolean" && typeof row.indexed==="boolean")) &&
    (row.kind!=="task" || typeof row.service==="string"));
}

export default function UnifiedQueueOverview(props){
  return <QueueForSession key={props.session} {...props}/>;
}

function QueueForSession({session,call,running,completed,ready,failures=[]}){
  const [page,setPage]=useState(0),[size,setSize]=useState(5);
  const [snapshot,setSnapshot]=useState(null),[error,setError]=useState(""),[filter,setFilter]=useState("all"),[revision,refresh]=useState(0);
  const [checkedAt,setCheckedAt]=useState(null),[checking,setChecking]=useState(true);
  useEffect(()=>{
    let active=true,timer,controller;
    async function load(){
      controller=new AbortController();let timedOut=false;
      const deadline=setTimeout(()=>{timedOut=true;controller.abort();},15000);
      if(active)setChecking(true);
      try{
        const value=await untilAborted(call("unified-queue-observe",{session_id:session},{signal:controller.signal}),controller.signal);
        if(!validSnapshot(value,session))throw new Error("공용 대기열 응답 형식 오류");
        if(active){setSnapshot(value);setCheckedAt(new Date());setError("");}
      }catch(problem){if(active)setError(timedOut ? "조회 시간이 초과됐습니다." : problem.message || "공용 대기열을 조회하지 못했습니다.");}
      finally{clearTimeout(deadline);if(active){setChecking(false);timer=setTimeout(load,5000);}}
    }
    load();
    return()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[session,call,revision]);
  const current=snapshot?.session_id===session ? snapshot : null;
  const rows=current?.entries || [];
  const pending=rows.map((row,index)=>{
    const position=index+1;
    return (
      <details key={row.kind+":"+row.id} className="queue-record">
      <summary><strong>{row.kind==="task" ? "GPU 작업 · "+row.service : row.own_session ? "이 대화 요청" : "다른 대화 요청"}</strong> · <code>{row.id}</code></summary>
      <small>공용 대기 순서 {position}번째</small>
      <div>{row.state==="gpu_queued" ? "GPU 대기" : row.state==="dispatching" ? "실행 준비" : "실행 대기"}{row.priority<0 && " · 우선순위 적용"}</div>
      {row.wait_reason && <p>{row.wait_reason}</p>}
      {row.kind==="chat" && !row.indexed && <p>공용 접수 확인 중</p>}
      <JobIdentifier id={row.id} label={row.kind==="chat" ? "요청 ID" : "작업 ID"} compact/>
      </details>
    );
  });
  const groups=[["running","진행 중",running],["pending","다음 후보",pending],["completed","완료",completed]];
  const entries=groups.filter(([key])=>filter==="all" || filter===key)
    .flatMap(([key,label,items])=>items.map(item=>({key:key+":"+item.key,label,item})));
  const failedSources=[...failures,["공용 대기열",error,Boolean(current)]].filter(([,reason])=>reason);
  const currentPage=Math.min(page,Math.max(0,Math.ceil(entries.length/size)-1));
  return <section className="panel unified-queue-overview" aria-label="작업 일정 목록">
    <label className="queue-state-filter">작업 상태
      <select value={filter} onChange={event=>{setFilter(event.target.value);setPage(0);}}>
        <option value="all">전체</option>
        {groups.map(([key,label])=><option key={key} value={key}>{label}</option>)}
      </select>
    </label>
    {failedSources.length>0 && <details className="schedule-query-error">
      <summary><span role="status">조회 실패 · {failedSources.map(([label])=>label).join(", ")}</span></summary>
      <ul>{failedSources.map(([label,reason,stale])=><li key={label}><strong>{label}</strong> · {reason} {stale && "마지막 조회 결과를 표시합니다."}</li>)}</ul>
      <p>자동으로 다시 조회합니다. 실패가 계속되면 연결 상태를 확인하세요.</p>
    </details>}
    {!current && checking && <p role="status">공용 대기열 조회 중…</p>}
    {ready && !error && current && !entries.length && <p>표시할 작업이 없습니다.</p>}
    <ul className="queue-entries">{entries.slice(currentPage*size,(currentPage+1)*size).map(({key,label,item})=>
      <li key={key}><small>{label}</small>{item}</li>)}</ul>
    {entries.length>5 && <QueuePagination page={currentPage} size={size} total={entries.length} label="작업 일정 페이지" onPage={setPage} onSize={value=>{setSize(value);setPage(0);}}/>}
    <footer><small>5초마다 갱신{checkedAt && <> · 최근 조회 <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleTimeString("ko-KR")}</time></>}</small>
      <button type="button" disabled={checking} onClick={()=>refresh(n=>n+1)}>새로고침</button></footer>
    {current && rows.length>0 && <small>{current.note}</small>}
  </section>;
}
