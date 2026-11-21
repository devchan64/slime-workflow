import React,{useState} from "react";
import WriterActions from "./WriterActions.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import WriterResult from "./WriterResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ResultTable from "./ResultTable.jsx";
import {managementCommand} from "./managementCommand.js";

export default function WriterPage({embedded=false}={}){
  const params=new URLSearchParams(location.search);
  const [query,setQuery]=useState(embedded ? "" : params.get("job") || "");
  const [selected,select]=useState("");
  const [recent,setRecent]=useState([]);
  const [matches,setMatches]=useState(null);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  async function search(){
    setBusy(true);select("");
    try {
      const result=await managementCommand("writer-agent","writer-history",{query});
      if(!Array.isArray(result.jobs) || result.count!==result.jobs.length)throw new Error("이력 건수를 확인할 수 없습니다.");
      setMatches(result.jobs);setNotice("");
      if(result.jobs.filter(job=>job.id===query).length===1)select(query);
    }catch(problem){setNotice(problem.message);setMatches([]);}
    finally{setBusy(false);}
  }
  const jobs=matches ?? recent;
  return <main><article><a href={"/management/frame/hermes-agent/"+(params.has("session")?"?"+new URLSearchParams({session:params.get("session")}):"")}>헤르메스 대화로 돌아가기</a>
    <h1>작가 AI 에이전트</h1><GeneratorChangelog generator="writer-agent"/>
    <ModelReadiness service="writer-agent"/><DownloadProgress service="writer-agent"/>
    <WriterActions onWorkspace={setRecent} onAccepted={id=>{select(id);setMatches(null);setNotice(id+" 작업을 접수했습니다.");}}/>
    <form onSubmit={event=>{event.preventDefault();search();}}><label>이력 검색<input maxLength={200} value={query} disabled={busy} onChange={event=>setQuery(event.target.value)}/></label>
      <button disabled={busy}>전체 이력 검색</button></form>
    <ResultTable table={{title:"작가 실행 기록",summary:(matches?"검색 결과 ":"최근 기록 ")+jobs.length+"건",columns:["작업 ID","작업","상태","요약"],
      rows:jobs.map(job=>[<><JobIdentifier id={job.id} compact/><button type="button" disabled={busy} onClick={()=>select(job.id)}>작업 보기</button></>,job.mode,job.stage,job.summary || job.error])}}/>
    {notice && <p role="status">{notice}</p>}
    {selected && <WriterResult key={selected} id={selected} onDeleted={id=>{select("");setRecent(rows=>rows.filter(row=>row.id!==id));setMatches(rows=>rows?.filter(row=>row.id!==id) ?? null);setNotice(id+" 기록을 휴지통으로 이동했습니다.");}}/>}
  </article></main>;
}
