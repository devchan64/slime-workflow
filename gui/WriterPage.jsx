import usePageTitle from "./usePageTitle.js";
import React,{useEffect,useRef,useState} from "react";
import WriterActions from "./WriterActions.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import WriterResult from "./WriterResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import ResultTable from "./ResultTable.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {writerModeLabel,writerStageLabel} from "./writerLabels.mjs";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";
import {requestErrorMessage} from "./requestError.mjs";

export default function WriterPage({embedded=false,session:embeddedSession=""}={}){
  usePageTitle("작가 AI 에이전트",embedded);
  const params=new URLSearchParams(location.search);
  const session=embeddedSession || params.get("session") || "";
  const [query,setQuery]=useState(embedded ? "" : params.get("job") || "");
  const [selected,select]=useState("");
  const [recent,setRecent]=useState(null);
  const [matches,setMatches]=useState(null);
  const [searchedQuery,setSearchedQuery]=useState("");
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [model,setModel]=useState(null),[modelError,setModelError]=useState("");
  const [proposalError,setProposalError]=useState("");
  const [proposal,setProposal]=useState(null),[proposalScope,setProposalScope]=useState(null),[proposalLoading,setProposalLoading]=useState(!embedded && params.has('proposal_job'));
  useEffect(()=>{
    if(embedded || !params.has('proposal_job'))return;
    let active=true;
    async function load(){try{
      const scope=generationProposalScope(location.search,session,'writer');
      const value=await readGenerationProposal(managementCommand,scope);
      if(!['write','deduplicate','learn','prepare'].includes(value.mode))throw new Error('작가 작업 종류를 확인할 수 없습니다.');
      if(active){setProposal(value);setProposalScope({...scope,proposal:value});setNotice('대화 제안 입력을 불러왔습니다. 작업을 확인한 뒤 요청하세요.');}
    }catch(problem){if(active)setProposalError('대화 제안을 불러오지 못했습니다 · '+requestErrorMessage(problem));}
    finally{if(active)setProposalLoading(false);}}
    load();return()=>{active=false;};
  },[]);
  const resultRef=useRef(null),resultTrigger=useRef(null),searchRequest=useRef(null),searchButton=useRef(null),searchInput=useRef(null),restoreSearchFocus=useRef(null);
  useEffect(()=>{if(!busy && restoreSearchFocus.current){const target=restoreSearchFocus.current;restoreSearchFocus.current=null;if(document.activeElement===document.body)target.current?.focus();}},[busy]);
  useEffect(()=>()=>{searchRequest.current?.abort();},[]);
  function focusResult(){resultRef.current?.focus({preventScroll:true});resultRef.current?.scrollIntoView({block:"start",inline:"nearest"});}
  useEffect(()=>{if(selected && resultTrigger.current)focusResult();},[selected]);
  function closeResult(){const focused=document.activeElement;select("");requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===focused) && resultTrigger.current?.isConnected)resultTrigger.current.focus();});}
  async function search(){
    if(searchRequest.current)return;
    restoreSearchFocus.current=document.activeElement===searchButton.current ? searchButton : document.activeElement===searchInput.current ? searchInput : null;
    const controller=new AbortController();searchRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);select("");resultTrigger.current=null;
    try {
      const result=await untilAborted(managementCommand("writer-agent","writer-history",{query},{signal:controller.signal}),controller.signal);
      if(!result || !Array.isArray(result.jobs) || result.count!==result.jobs.length || result.jobs.some(job=>!job || typeof job.id!=="string" || typeof job.mode!=="string" || typeof job.stage!=="string" || [job.summary,job.error].some(value=>value!=null && typeof value!=="string")))throw new Error("이력 응답 형식을 확인할 수 없습니다.");
      setMatches(result.jobs);setSearchedQuery(query);setNotice("");
      if(result.jobs.filter(job=>job.id===query).length===1)select(query);
    }catch(problem){if(!controller.signal.aborted || timedOut){setNotice("이력 검색에 실패했습니다 · "+(timedOut ? "조회 시간이 초과됐습니다. 다시 검색하세요." : requestErrorMessage(problem))+(matches ? " · 아래에는 마지막으로 확인한 검색 결과가 표시됩니다." : recent ? " · 아래에는 마지막으로 확인한 최근 기록이 표시됩니다." : " · 최근 기록도 확인되지 않았습니다."));}}
    finally{clearTimeout(timeout);if(searchRequest.current===controller)searchRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  const jobs=matches ?? recent ?? [];
  return <main className="writer-page-shell"><article className="writer-page">{!embedded && <nav aria-label="워크플로우 탐색"><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a></nav>}
    <h1 className={embedded ? "embedded-page-title" : undefined}>작가 AI 에이전트</h1><GeneratorChangelog generator="writer-agent"/>
    {embedded ? <GeneratorSectionCard title="모델 준비 및 다운로드" summary={modelError ? "조회 실패" : !model ? "확인 중" : model.ready ? "준비됨" : "준비 필요"}><ModelReadiness service="writer-agent" onStatus={setModel} onError={setModelError}/><DownloadProgress service="writer-agent"/></GeneratorSectionCard> : <><ModelReadiness service="writer-agent"/><DownloadProgress service="writer-agent"/></>}
    {proposalError && <p role="alert">{proposalError} · 기본 입력으로 계속할 수 있습니다.</p>}
    {proposalLoading ? <p role="status">대화 제안 확인 중…</p> : <WriterActions session={session} proposalScope={proposalScope} initialPrompt={proposal?.prompt || ""} proposedMode={proposal?.mode || ""} onWorkspace={setRecent} onAccepted={id=>{resultTrigger.current=null;select(id);setMatches(null);setNotice(id+" 작업을 접수했습니다.");}}/>}
    <form onSubmit={event=>{event.preventDefault();search();}}><label>이력 검색<input ref={searchInput} maxLength={200} value={query} disabled={busy} onChange={event=>setQuery(event.target.value)}/></label>
      <button ref={searchButton} disabled={busy}>{query.trim()?"이력 검색":"전체 이력 검색"}</button></form>
    {matches && query!==searchedQuery && <p role="status">검색어가 변경되었습니다. 아래 결과는 이전 검색 조건으로 조회했습니다. {query.trim()?"이력 검색":"전체 이력 검색"}을 눌러 적용하세요.</p>}
    {matches || recent ? <div className="writer-history-table"><ResultTable table={{title:"작가 실행 기록",summary:(matches?"검색 결과 ":"최근 기록 ")+jobs.length+"건",columns:["작업 ID","작업","상태","요약"],
      rows:jobs.map(job=>[<><JobIdentifier id={job.id} compact/><button type="button" disabled={busy} onClick={event=>{resultTrigger.current=event.currentTarget;if(selected===job.id)focusResult();else select(job.id);}}>작업 보기</button></>,writerModeLabel(job.mode),writerStageLabel(job.stage),job.summary || job.error])}}/></div> : <p>최근 기록을 확인하지 못했습니다. 준비 상태를 다시 확인하거나 전체 이력을 검색하세요.</p>}
    {notice && <p role="status">{notice}</p>}
    {selected && <div ref={resultRef} tabIndex={-1} aria-label="선택한 작가 작업"><button type="button" onClick={closeResult}>결과 닫기</button><WriterResult key={selected} id={selected} onDeleted={id=>{select("");setRecent(rows=>rows?.filter(row=>row.id!==id) ?? null);setMatches(rows=>rows?.filter(row=>row.id!==id) ?? null);setNotice(id+" 기록을 휴지통으로 이동했습니다.");}}/></div>}
  </article></main>;
}
