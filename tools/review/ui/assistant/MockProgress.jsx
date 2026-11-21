import React, {useEffect,useState} from "react";
import ResultTable from "./ResultTable.jsx";

const jobsPath="/management/assistant/mock-jobs";
const labels={queued:"대기 중",running:"실행 중",completed:"완료"};

export default function MockProgress() {
  const [jobs,setJobs]=useState([]);
  const [selected,select]=useState("");
  const [revision,refresh]=useState(0);
  const [page,setPage]=useState(0);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [readError,setReadError]=useState("");
  useEffect(()=>{
    let active=true,timer;
    async function read(){
      try {
        const response=await fetch(jobsPath,{cache:"no-store"});
        if(!response.ok)throw new Error("모의 이력 조회 실패");
        const records=await response.json();
        if(active){setJobs(records);setReadError("");}
      }catch(problem){if(active)setReadError(problem.message);}
      finally{if(active)timer=setTimeout(read,2000);}
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[revision]);
  async function start(){
    setBusy(true);setError("");
    try{
      const response=await fetch(jobsPath,{method:"POST"});
      if(!response.ok)throw new Error("모의 작업 등록 실패");
      const job=await response.json();
      select(job.id);setPage(0);refresh(value=>value+1);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  const job=jobs.find(row=>row.id===selected);
  return <article><h1>모의 진행 상태 검증</h1>
    <p>격리된 메모리에서 대기, 실행, 완료 상태를 확인합니다.</p>
    <button disabled={busy} onClick={start}>모의 작업 시작</button>
    {(error || readError) && <p role="alert">{error || readError}</p>}
    {job && <p role="status">{job.id} · {labels[job.status]} · {job.message}</p>}
    <ResultTable table={{title:"모의 작업 이력",summary:"전체 "+jobs.length+"건",columns:["작업 ID","상태"],
      rows:jobs.slice(page*10,page*10+10).map(row=>[<button onClick={()=>select(row.id)}>{row.id}</button>,labels[row.status]])}}/>
    {page>0 && <button onClick={()=>setPage(page-1)}>이전 페이지</button>}
    {(page+1)*10<jobs.length && <button onClick={()=>setPage(page+1)}>다음 페이지</button>}
    <a href="/management/assistant/">헤르메스 대화로 이동</a>
  </article>;
}
