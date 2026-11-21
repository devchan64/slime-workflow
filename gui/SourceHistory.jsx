import HistoryCleanup from "./HistoryCleanup.jsx";
import KimodoFrames from "./KimodoFrames.jsx";
import WriterActions from "./WriterActions.jsx";
import WriterResult from "./WriterResult.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export function HistoryPage({source, choose, session, initialJob=""}) {
  const [selectedJob,selectJob]=useState(initialJob);
  const [query,setQuery]=useState("");
  const [page,setPage]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const mediaKind=source.result_kind;
  const writer=source.service==="writer-agent";
  const kimodo=source.service==="kimodo";
  const hasResult=source.result_path || mediaKind || writer || kimodo;
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
  function cleaned(message){setNotice(message);load(0);}
  return <fieldset disabled={busy}>
    {writer && <WriterActions onAccepted={id=>{selectJob(id);setNotice(id+" 작가 작업을 접수했습니다.");}}/>}
      {selectedJob && writer && <WriterResult key={selectedJob} id={selectedJob} onDeleted={id=>{setNotice(id+" 실행 기록을 휴지통으로 옮겼습니다.");load(0);}}/>}
    <label>작업 ID 검색 <input maxLength={80} value={query} onChange={event=>{selectJob("");setQuery(event.target.value);setPage(null);setError("");}}/></label>
    <button onClick={()=>load(0)}>{busy?"조회 중…":"이력 조회"}</button>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {page && <>
      <ResultTable table={{
        title:source.service+" 생성 이력",
        summary:"전체 "+page.total+"건 · 조회 "+page.records.length+"건 · 확인 불가 "+page.unavailable_count+"건",
        columns:["작업 ID","기록 상태",...(hasResult?["결과"]:[])],
        rows:page.records.map(record=>[
          <button title="작업을 대화 입력에 추가" onClick={()=>choose(source.service+" 작업",record.id)}>{record.id}</button>,
          record.recorded_status,
          ...(hasResult ? [<>
            {kimodo && <a href={"/management/assistant/kimodo/?"+new URLSearchParams({restore:record.id,...(session?{session}:{})})}>입력 재사용</a>}
            {kimodo && <button onClick={()=>selectJob(record.id)}>{record.recorded_status==="completed"?"원본 프레임 보기":"작업 상태 보기"}</button>}
            {(mediaKind || writer) && <button onClick={()=>selectJob(record.id)}>결과 보기</button>}
            {source.result_path && <a href={source.result_path+"?"+new URLSearchParams({job:record.id,...(session?{session}:{})})}>작업 열기</a>}
          </>] : []),
        ]),
      }}/>

      {selectedJob && mediaKind && <MediaJobResult kind={mediaKind} key={selectedJob} service={source.service} id={selectedJob}>
        {job=>job?.status==="completed" && job.result_status==="available" && job.file_observation!=="unavailable" &&
          <button onClick={()=>choose(source.service+" 생성 결과",selectedJob)}>이 결과를 대화 입력에 추가</button>}
      </MediaJobResult>}
      <p>{page.note}</p>
      {page.offset>0 && <button onClick={()=>load(Math.max(0,page.offset-10),page.snapshot)}>이전 이력</button>}
      {page.next_offset!=null && <button onClick={()=>load(page.next_offset,page.snapshot)}>다음 이력</button>}
    </>}
    {kimodo && (selectedJob ? <KimodoFrames key={selectedJob} id={selectedJob} choose={choose} onDeleted={cleaned}/> :
      <HistoryCleanup service="kimodo" onDeleted={cleaned}/>)}
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
