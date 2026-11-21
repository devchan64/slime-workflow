import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function OperationsJobs(){
  const [query,setQuery]=useState(""),[status,setStatus]=useState("전체");
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [gpu,setGpu]=useState(null),[gpuError,setGpuError]=useState("");
  const [priority,setPriority]=useState(null);
  async function reviewPriority(service,id){
    setBusy(true);setPriority(null);setGpuError("");
    try{
      const response=await fetch("/management/assistant/operations-priority-review",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({service,id})});
      if(!response.ok)throw new Error("대기 작업을 다시 조회하세요.");
      setPriority(await response.json());
    }catch(problem){setGpuError(problem.message);}
    finally{setBusy(false);}
  }
  async function prioritize(){
    const request=priority?.request;
    if(!request || busy)return;
    setBusy(true);setPriority({...priority,request:null});
    try{
      const receipt=await managementCommand("hermes-agent","hermes-priority-submit",request);
      if(receipt.state!=="completed" || receipt.request_id!==request.request_id || receipt.job_id!==request.id ||
         receipt.service!==request.service || receipt.ticket_revision!==request.ticket_revision)throw new Error();
      setPriority({notice:"우선순위 변경이 접수되었습니다. 대기열을 다시 조회하세요.",identifier:request.request_id});
    }catch{
      setPriority({notice:"접수 결과를 확인할 수 없습니다. 접수 ID로 운영 이력을 확인하세요.",identifier:request.request_id});
    }finally{setBusy(false);}
  }
  function gpuTable(table){
    if(table.title!=="GPU 대기열")return table;
    return {...table,columns:[...table.columns,"우선순위"],rows:table.rows.map(row=>{
      const source=row[3];
      return [...row,source==="미확인" ? "원 서비스 미확인" :
        <button onClick={()=>reviewPriority(source,row[2])}>우선 실행 검토</button>];
    })};
  }
  async function loadGpu(){
    setBusy(true);setGpuError("");setPriority(null);
    try{
      const response=await fetch("/management/assistant/operations-gpu",{cache:"no-store"});
      if(!response.ok)throw new Error("GPU 관측 기록을 불러올 수 없습니다.");
      setGpu(await response.json());
    }catch(problem){setGpu(null);setGpuError(problem.message);}
    finally{setBusy(false);}
  }
  async function load(direction){
    setBusy(true);setError("");
    try{
      const response=await fetch("/management/assistant/operations-jobs",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({query,status,direction,page:result?.page})});
      if(!response.ok)throw new Error("운영 작업 목록을 불러올 수 없습니다.");
      setResult(await response.json());
    }catch(problem){setError(problem.message);setResult(null);}
    finally{setBusy(false);}
  }
  const page=result?.page;
  const same=page && page.query===query.trim().toLowerCase() && page.status===status;
  return <fieldset disabled={busy}><legend>운영 작업 이력</legend>
    <label>작업 ID 또는 지시문 <input value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <label>작업 상태 <select value={status} onChange={e=>setStatus(e.target.value)}><option>전체</option>
      {Object.entries(result?.statuses || {}).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
    <button onClick={()=>load("first")}>작업 조회</button>
    {error && <p role="alert">{error}</p>}
    {result && <><ResultTable table={{title:"운영 작업",summary:result.summary,columns:["작업 ID","상태","GPU 대기","지시문","GPU 예약"],rows:result.rows}}/>
      <button disabled={!same || !page.offset} onClick={()=>load("newer")}>이전 페이지</button>
      <button disabled={!same || page.next_offset==null} onClick={()=>load("older")}>다음 페이지</button></>}
    <button onClick={loadGpu}>GPU 대기열·예약 조회</button>
    {gpuError && <p role="alert">{gpuError}</p>}
    {gpu?.map(table=>table.available ? <ResultTable key={table.title} table={gpuTable(table)}/> :
      <p role="status" key={table.title}>{table.summary}</p>)}
    {priority && <section><p role="status">{priority.notice}</p>{priority.identifier && <code>{priority.identifier}</code>}
      {priority.request && <><button onClick={()=>setPriority(null)}>취소</button>
        <button onClick={prioritize}>확인 후 우선순위 변경</button></>}</section>}
  </fieldset>;
}
