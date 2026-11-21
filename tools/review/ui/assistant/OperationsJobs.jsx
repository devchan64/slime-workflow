import React,{useState} from "react";
import ResultTable from "./ResultTable.jsx";

export default function OperationsJobs(){
  const [query,setQuery]=useState(""),[status,setStatus]=useState("전체");
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
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
  </fieldset>;
}
