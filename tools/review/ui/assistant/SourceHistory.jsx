import MediaJobResult from "./MediaJobResult.jsx";
import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function HistoryPage({source, choose, session}) {
  const [selectedJob,selectJob]=useState("");
  const [query,setQuery]=useState("");
  const [page,setPage]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const mediaKind=source.result_kind;
  async function load(offset,snapshot) {
    setBusy(true);selectJob("");
    setError("");
    try {
      const payload={service:source.service,query:query.trim(),offset,limit:10};
      if(snapshot) payload.snapshot=snapshot;
      setPage(await managementCommand("hermes-agent",source.command,payload));
    } catch(problem) {setError(problem.message);setPage(null);}
    finally {setBusy(false);}
  }
  return <fieldset disabled={busy}>
    <label>작업 ID 검색 <input maxLength={80} value={query} onChange={event=>{selectJob("");setQuery(event.target.value);setPage(null);setError("");}}/></label>
    <button onClick={()=>load(0)}>{busy?"조회 중…":"이력 조회"}</button>
    {error && <p role="alert">{error}</p>}
    {page && <>
      <ResultTable table={{
        title:source.service+" 생성 이력",
        summary:"전체 "+page.total+"건 · 조회 "+page.records.length+"건 · 확인 불가 "+page.unavailable_count+"건",
        columns:["작업 ID","기록 상태",...(source.result_path || mediaKind?["결과"]:[])],
        rows:page.records.map(record=>[
          <button title="작업을 대화 입력에 추가" onClick={()=>choose(source.service+" 작업",record.id)}>{record.id}</button>,
          record.recorded_status,
          ...(source.result_path ? [
            <a href={source.result_path+"?"+new URLSearchParams({job:record.id,...(session?{session}:{})})}>작업 열기</a>,
          ] : mediaKind ? [<button onClick={()=>selectJob(record.id)}>결과 보기</button>] : []),
        ]),
      }}/>
      {selectedJob && <MediaJobResult kind={mediaKind} key={selectedJob} service={source.service} id={selectedJob}>
        {job=>job?.status==="completed" && job.result_status==="available" && job.file_observation!=="unavailable" &&
          <button onClick={()=>choose(source.service+" 생성 결과",selectedJob)}>이 결과를 대화 입력에 추가</button>}
      </MediaJobResult>}
      <p>{page.note}</p>
      {page.offset>0 && <button onClick={()=>load(Math.max(0,page.offset-10),page.snapshot)}>이전 이력</button>}
      {page.next_offset!=null && <button onClick={()=>load(page.next_offset,page.snapshot)}>다음 이력</button>}
    </>}
  </fieldset>;
}

export default function SourceHistory({choose, session}) {
  const [sources,setSources]=useState([]);
  const [selected,select]=useState("");
  const [error,setError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    fetch("/management/assistant/history-services",{signal:controller.signal})
      .then(response=>{if(!response.ok)throw new Error("생성기 목록을 조회할 수 없습니다.");return response.json();})
      .then(rows=>{setSources(rows);select(rows[0]?.service || "");})
      .catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});
    return ()=>controller.abort();
  },[]);
  const source=sources.find(row=>row.service===selected);
  return <section aria-label="생성 이력">
    <label>이력 서비스 <select value={selected} onChange={event=>select(event.target.value)}>
      {sources.map(row=><option key={row.service}>{row.service}</option>)}
    </select></label>
    {error && <p role="alert">{error}</p>}
    {source && <HistoryPage key={selected} source={source} session={session} choose={choose}/>}
  </section>;
}
