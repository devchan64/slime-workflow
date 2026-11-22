import HistoryCleanup from "./HistoryCleanup.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import JobStatus from "./JobStatus.jsx";
import KimodoFrames from "./KimodoFrames.jsx";
import WriterActions from "./WriterActions.jsx";
import WriterResult from "./WriterResult.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import React, {useEffect, useRef, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {latestRequest} from "./latestRequest.mjs";
import {validSourceHistoryPage} from "./sourceHistoryPage.mjs";
import {orderHistorySources} from "./historySourceOrder.mjs";

export function HistoryPage({source, choose, session, initialJob=""}) {
  const [selectedJob,selectJob]=useState(initialJob);
  const [query,setQuery]=useState("");
  const [filter,setFilter]=useState("");
  const [page,setPage]=useState(null);
  const [receivedAt,setReceivedAt]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const request=useRef(null);
  const resultRef=useRef(null),resultTrigger=useRef(null);
  const listRef=useRef(null),focusList=useRef(false),failedPageTrigger=useRef(null),searchRef=useRef(null);
  if(!request.current)request.current=latestRequest();
  useEffect(()=>()=>request.current.invalidate(),[]);
  const mediaKind=source.result_kind;
  const writer=source.service==="writer-agent";
  const kimodo=source.service==="kimodo";
  const hasResult=source.result_path || mediaKind || writer || kimodo;
  function focusResult(){resultRef.current?.focus({preventScroll:true});resultRef.current?.scrollIntoView({block:"start",inline:"nearest"});}
  useEffect(()=>{if(selectedJob && (mediaKind || writer || kimodo) && resultTrigger.current)focusResult();},[selectedJob,mediaKind,writer,kimodo]);
  useEffect(()=>{if(focusList.current && page && listRef.current){focusList.current=false;listRef.current.focus({preventScroll:true});listRef.current.scrollIntoView({block:"start",inline:"nearest"});}},[page]);
  useEffect(()=>{if(!busy && error && failedPageTrigger.current){const target=failedPageTrigger.current;failedPageTrigger.current=null;if(document.activeElement===document.body && target.isConnected)target.focus();}},[busy,error]);
  function closeResult(){selectJob("");requestAnimationFrame(()=>resultTrigger.current?.isConnected && resultTrigger.current.focus());}
  function openResult(id,event){resultTrigger.current=event.currentTarget;if(selectedJob===id)focusResult();else selectJob(id);}
  async function load(offset,snapshot,navigate=false,trigger=null,search=query.trim()) {
    const token=request.current.start();
    setBusy(true);
    setError("");
    try {
      const payload={service:source.service,query:search,offset,limit:10};
      if(snapshot) payload.snapshot=snapshot;
      const result=await managementCommand("hermes-agent",source.command,payload);
      if(!validSourceHistoryPage(result,source.service,offset,snapshot))throw new Error("이력 페이지를 확인할 수 없습니다. 다시 조회하세요.");
      if(request.current.isCurrent(token)){focusList.current=navigate;setPage(result);setReceivedAt(new Date());setFilter(payload.query);selectJob("");}
    } catch(problem) {if(request.current.isCurrent(token)){failedPageTrigger.current=navigate ? trigger : null;setError((problem instanceof TypeError ? "이력 서버에 연결하지 못했습니다. 연결 상태를 확인한 후 다시 조회하세요." : problem.message)+(page ? " · 이전 조회 결과를 유지합니다." : ""));}}
    finally {if(request.current.isCurrent(token))setBusy(false);}
  }
  function cleaned(message){setNotice(message);selectJob("");load(0,undefined,false,null,filter);}
  return <fieldset disabled={busy}>
    {writer && <WriterActions onAccepted={id=>{resultTrigger.current=null;selectJob(id);setNotice(id+" 작가 작업을 접수했습니다.");}}/>}
      {selectedJob && writer && <div ref={resultRef} tabIndex={-1} aria-label="선택한 이력 결과"><button type="button" onClick={closeResult}>결과 닫기</button><WriterResult key={selectedJob} id={selectedJob} onDeleted={id=>{setNotice(id+" 실행 기록을 휴지통으로 옮겼습니다.");selectJob("");load(0,undefined,false,null,filter);}}/></div>}
    <label>작업 ID 검색 <input ref={searchRef} maxLength={80} value={query} onChange={event=>{request.current.invalidate();setBusy(false);setQuery(event.target.value);setError("");}} onKeyDown={event=>{if(event.key==="Enter" && !event.nativeEvent.isComposing && event.nativeEvent.keyCode!==229){event.preventDefault();load(0,undefined,true,event.currentTarget);}}}/></label>
    <button onClick={event=>load(0,undefined,true,event.currentTarget)}>{busy?"조회 중…":"이력 조회"}</button>
    {query && <button type="button" onClick={()=>{request.current.invalidate();setQuery("");setError("");searchRef.current?.focus();}}>검색어 지우기</button>}
    {error && <p role="alert">{error}</p>}
    {page && query.trim()!==filter && <p role="status">검색어가 변경되었습니다. 아래는 이전 검색 결과입니다. 이력 조회를 눌러 적용하세요.</p>}
    {notice && <p role="status">{notice}</p>}
    {page && <>
      <section ref={listRef} tabIndex={-1} aria-label={source.service+" 생성 이력"}><strong>{source.service} 생성 이력</strong>
        <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>
        <p>{filter ? <>검색어 · <strong>{filter}</strong></> : "검색 조건 · 전체 이력"}</p>
        <p>전체 {page.total}건 · 조회 {page.records.length}건 · 확인 불가 {page.unavailable_count}건</p>
        <button type="button" onClick={()=>{searchRef.current?.focus({preventScroll:true});searchRef.current?.scrollIntoView({block:"center",inline:"nearest"});}}>검색 조건으로 이동</button>
        {page.records.length===0 && <div><p>{filter ? "검색 조건에 맞는 이력이 없습니다." : "조회된 이력이 없습니다."}</p>{filter && <button type="button" onClick={event=>{setQuery("");load(0,undefined,true,event.currentTarget,"");}}>전체 이력 보기</button>}</div>}
        <div className="session-job-list source-history-list">{page.records.map(record=><article className="session-job" key={record.id}>
          <div className="session-job-heading"><JobIdentifier id={record.id} compact/><div className="source-history-recorded-status"><small>기록 상태</small><JobStatus state={record.recorded_status}/></div></div>
          <div className="session-job-actions"><button type="button" aria-label={record.id+" 작업을 대화에 추가"} onClick={()=>choose(source.service+" 작업",record.id)}>대화에 추가</button>
            {hasResult && <>
              {kimodo && <a href={"/management/assistant/kimodo/?"+new URLSearchParams({restore:record.id,...(session?{session}:{})})}>입력 재사용</a>}
              {kimodo && <button aria-label={record.id+(record.recorded_status==="completed"?" 원본 프레임 보기":" 작업 상태 보기")} aria-expanded={selectedJob===record.id} onClick={event=>openResult(record.id,event)}>{record.recorded_status==="completed"?"원본 프레임 보기":"작업 상태 보기"}</button>}
              {(mediaKind || writer) && <button aria-label={record.id+" 결과 보기"} aria-expanded={selectedJob===record.id} onClick={event=>openResult(record.id,event)}>결과 보기</button>}
              {source.result_path && <a aria-label={record.id+" 작업 열기"} href={source.result_path+"?"+new URLSearchParams({job:record.id,...(session?{session}:{})})}>작업 열기</a>}
            </>}
          </div>
        </article>)}</div>
      </section>

      {selectedJob && mediaKind && <div ref={resultRef} tabIndex={-1} aria-label="선택한 이력 결과"><button type="button" onClick={closeResult}>결과 닫기</button><MediaJobResult kind={mediaKind} key={selectedJob} service={source.service} id={selectedJob}>
        {job=>mediaKind!=="character" && job?.status==="completed" && job.result_status==="available" && job.file_observation!=="unavailable" &&
          <button onClick={()=>choose(source.service+" 생성 결과",selectedJob)}>이 결과를 대화 입력에 추가</button>}
      </MediaJobResult></div>}
      <p>{page.note}</p>
      {page.offset>0 && <button disabled={query.trim()!==filter} onClick={event=>load(Math.max(0,page.offset-10),page.snapshot,true,event.currentTarget)}>이전 이력</button>}
      {page.next_offset!=null && <button disabled={query.trim()!==filter} onClick={event=>load(page.next_offset,page.snapshot,true,event.currentTarget)}>다음 이력</button>}
    </>}
    {kimodo && (selectedJob ? <div ref={resultRef} tabIndex={-1} aria-label="선택한 이력 결과"><button type="button" onClick={closeResult}>결과 닫기</button><KimodoFrames key={selectedJob} id={selectedJob} choose={choose} onDeleted={cleaned}/></div> :
      <HistoryCleanup service="kimodo" onDeleted={cleaned}/>)}
  </fieldset>;
}

export default function SourceHistory({choose, session}) {
  const [sources,setSources]=useState([]);
  const [selected,select]=useState("");
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[attempt,setAttempt]=useState(0);
  const serviceRef=useRef(null),retryRef=useRef(null),sectionRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);setError("");
    fetch("/management/assistant/history-services",{signal:controller.signal})
      .then(response=>{if(!response.ok)throw new Error("생성기 목록을 조회할 수 없습니다.");return response.json();})
      .then(rows=>{if(!Array.isArray(rows) || rows.some(row=>!row || typeof row.service!=="string" || typeof row.command!=="string"))throw new Error("생성기 목록 형식을 확인할 수 없습니다.");if(!controller.signal.aborted){const ordered=orderHistorySources(rows);setSources(ordered);select(ordered[0]?.service || "");}})
      .catch(problem=>{if(!controller.signal.aborted)setError(problem.message);})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[attempt]);
  useEffect(()=>{
    if(loading || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)(error ? retryRef : sources.length ? serviceRef : sectionRef).current?.focus();
  },[loading,error,sources]);
  const source=sources.find(row=>row.service===selected);
  return <section ref={sectionRef} tabIndex={-1} aria-label="생성 이력">
    {loading && <p role="status">이력 서비스를 조회하고 있습니다.</p>}
    {error && <div role="alert"><p>{error}</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=true;setAttempt(value=>value+1);}}>다시 시도</button></div>}
    {!loading && !error && sources.length===0 && <p>조회할 수 있는 이력 서비스가 없습니다.</p>}
    {sources.length>0 && <label>이력 서비스 <select ref={serviceRef} value={selected} onChange={event=>select(event.target.value)}>
      {sources.map(row=><option key={row.service} value={row.service}>{row.service}{row.archived === true ? " · 이전 이력" : ""}</option>)}
    </select></label>}
    {source && <HistoryPage key={selected} source={source} session={session} choose={choose}/>}
  </section>;
}
