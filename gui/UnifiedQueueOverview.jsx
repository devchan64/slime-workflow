import React,{useEffect,useState} from "react";
import JobIdentifier from "./JobIdentifier.jsx";
import {untilAborted} from "./managementCommand.js";

function validSnapshot(value,session){
  return value?.session_id===session && Array.isArray(value.entries) && typeof value.note==="string" && value.entries.every(row=>
    row && ["chat","task"].includes(row.kind) && typeof row.id==="string" && /^[A-Za-z0-9_-]{1,120}$/.test(row.id) &&
    typeof row.order_ns==="string" && /^[0-9]{1,20}$/.test(row.order_ns) && Number.isSafeInteger(row.priority) &&
    (row.wait_reason===undefined || typeof row.wait_reason==="string") &&
    ["queued","dispatching","gpu_queued"].includes(row.state) &&
    (row.kind!=="chat" || (typeof row.own_session==="boolean" && typeof row.indexed==="boolean")) &&
    (row.kind!=="task" || typeof row.service==="string"));
}

export default function UnifiedQueueOverview({session,call}){
  const [snapshot,setSnapshot]=useState(null),[error,setError]=useState(""),[filter,setFilter]=useState("all"),[revision,refresh]=useState(0);
  useEffect(()=>{
    let active=true,timer,controller;
    async function load(){
      controller=new AbortController();
      const deadline=setTimeout(()=>controller.abort(),15000);
      try{
        const value=await untilAborted(call("unified-queue-observe",{session_id:session},{signal:controller.signal}),controller.signal);
        if(!validSnapshot(value,session))throw new Error("공용 대기열 응답 형식 오류");
        if(active){setSnapshot(value);setError("");}
      }catch(problem){if(active)setError(problem.message || "공용 대기열을 조회하지 못했습니다.");}
      finally{clearTimeout(deadline);if(active)timer=setTimeout(load,5000);}
    }
    setSnapshot(null);setError("");load();
    return()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[session,call,revision]);
  const entries=(snapshot?.entries || []).filter(row=>filter==="all" || row.kind===filter);
  return <section className="panel unified-queue-overview" aria-label="공용 대기열 목록">
    <h2>공용 대기열</h2><p>{snapshot?.note || "대화 요청과 GPU 대기 작업을 조회합니다."}</p>
    <label>분류 <select aria-label="대기열 분류" value={filter} onChange={event=>setFilter(event.target.value)}><option value="all">전체</option><option value="chat">대화</option><option value="task">작업</option></select></label>
    <button type="button" onClick={()=>refresh(n=>n+1)}>공용 대기열 새로고침</button>
    {error && <p role="alert">공용 대기열을 확인하지 못했습니다. {snapshot && "표시된 목록은 이전 조회 결과입니다."}</p>}
    {!snapshot && !error && <p role="status">대기열 조회 중</p>}
    {snapshot && !entries.length && <p>해당 분류에 대기 중인 요청이 없습니다.</p>}
    {entries.length>0 && <ol>{entries.map((row,index)=><li key={row.kind+":"+row.id+":"+row.order_ns}>
      <strong>{row.kind==="chat" ? "대화" : "작업 · "+row.service}</strong>{" · "}
      <span>{row.state==="gpu_queued" ? "GPU 대기" : row.state==="dispatching" ? "실행 준비" : "대기"}</span>
      {row.wait_reason && <span> · {row.wait_reason}</span>}
      {row.kind==="chat" && <span>{row.own_session ? " · 이 대화" : " · 다른 대화"}</span>}
      {row.kind==="chat" && !row.indexed && <span> · 공용 접수 확인 중</span>}
      {row.priority<0 && <span> · 우선순위 적용</span>}
      <JobIdentifier id={row.id} label={row.kind==="chat" ? "대화 요청 ID" : "작업 ID"} compact/>
    </li>)}</ol>}
  </section>;
}
