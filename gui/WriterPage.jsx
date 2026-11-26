import usePageTitle from "./usePageTitle.js";
import React,{useEffect,useId,useRef,useState} from "react";
import WriterActions from "./WriterActions.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import WriterResult from "./WriterResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import GeneratorSectionNavigation,{focusGeneratorRegion} from "./GeneratorSectionNavigation.jsx";
import ResultTable from "./ResultTable.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {writerModeLabel,writerStageLabel} from "./writerLabels.mjs";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";
import {requestErrorMessage} from "./requestError.mjs";

export function writerInputSummary(state,proposalLoading=false){
  if(proposalLoading)return "대화 제안 확인 중";
  const workspace=state?.workspace,active=workspace?.active_job;
  const label=state?.error ? "준비 상태 조회 실패" : state?.checking || !workspace ? "준비 상태 확인 중" : active ? "진행 중 · "+active : !workspace.configured ? "문서 폴더 확인 필요" : !workspace.ready ? "환경 준비 필요" : !workspace.trained ? "색인 준비 필요" : "작업 요청 가능";
  return label+((state?.error || state?.checking) && active ? " · 이전 작업 "+active : "")+(state?.checkedAt ? " · 조회 "+state.checkedAt.toLocaleTimeString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}) : "");
}

export default function WriterPage({embedded=false,session:embeddedSession=""}={}){
  usePageTitle("작가 AI 에이전트",embedded);
  const searchStatusId=useId();
  const params=new URLSearchParams(location.search);
  const session=embeddedSession || params.get("session") || "";
  const [query,setQuery]=useState(embedded ? "" : params.get("job") || "");
  const [selected,setSelected]=useState("");
  const selectionEpoch=useRef(0);
  function select(id){selectionEpoch.current++;setSelected(id);}
  const [recent,setRecent]=useState(null);
  const [matches,setMatches]=useState(null);
  const [searchedQuery,setSearchedQuery]=useState("");
  const [busy,setBusy]=useState(false);
  const [notice,setNoticeState]=useState(""),[noticeError,setNoticeError]=useState(false);
  function setNotice(message,{error=false}={}){setNoticeState(message);setNoticeError(error);}
  const [model,setModel]=useState(null),[modelError,setModelError]=useState("");
  const [workspaceState,setWorkspaceState]=useState(null);
  const [proposalError,setProposalError]=useState("");
  const [proposal,setProposal]=useState(null),[proposalScope,setProposalScope]=useState(null),[proposalLoading,setProposalLoading]=useState(!embedded && params.has('proposal_job'));
  useEffect(()=>{
    if(embedded || !params.has('proposal_job'))return;
    let active=true;const controller=new AbortController();
    async function load(){try{
      const scope=generationProposalScope(location.search,session,'writer');
      const value=await readGenerationProposal(managementCommand,scope,{signal:controller.signal});
      if(!['write','deduplicate','learn','prepare'].includes(value.mode))throw new Error('작가 작업 종류를 확인할 수 없습니다.');
      if(active){setProposal(value);setProposalScope({...scope,proposal:value});setNotice('대화 제안 입력을 불러왔습니다. 작업을 확인한 뒤 요청하세요.');}
    }catch(problem){if(active)setProposalError('대화 제안을 불러오지 못했습니다 · '+requestErrorMessage(problem));}
    finally{if(active)setProposalLoading(false);}}
    load();return()=>{active=false;controller.abort();};
  },[]);
  const resultRef=useRef(null),inputRegion=useRef(null),historyRegion=useRef(null),historyCard=useRef(null),resultTrigger=useRef(null),resultFocusFrame=useRef(null),searchRequest=useRef(null),searchButton=useRef(null),searchInput=useRef(null),restoreSearchFocus=useRef(null);
  useEffect(()=>{if(!busy && restoreSearchFocus.current){const target=restoreSearchFocus.current;restoreSearchFocus.current=null;if(document.activeElement===document.body)target.current?.focus();}},[busy]);
  useEffect(()=>()=>{searchRequest.current?.abort();if(resultFocusFrame.current!==null)cancelAnimationFrame(resultFocusFrame.current);},[]);
  function focusResult(){resultRef.current?.focus({preventScroll:true});resultRef.current?.scrollIntoView({block:"start",inline:"nearest"});}
  useEffect(()=>{if(selected && historyCard.current)historyCard.current.open=true;},[selected]);
  useEffect(()=>{if(selected && resultTrigger.current && (document.activeElement===document.body || document.activeElement===resultTrigger.current))focusResult();},[selected]);
  function closeResult(){
    const focused=document.activeElement,origin=resultTrigger.current,restore=resultRef.current?.contains(focused);
    select("");const epoch=selectionEpoch.current;
    if(resultFocusFrame.current!==null)cancelAnimationFrame(resultFocusFrame.current);
    if(restore)resultFocusFrame.current=requestAnimationFrame(()=>{resultFocusFrame.current=null;const target=origin?.isConnected && !origin.matches(":disabled") ? origin : searchButton.current;if(epoch===selectionEpoch.current && (document.activeElement===document.body || document.activeElement===focused) && target?.isConnected && !target.matches(":disabled"))target.focus();});
  }
  async function search(){
    if(searchRequest.current)return;
    const selectionAtStart=selectionEpoch.current;
    restoreSearchFocus.current=document.activeElement===searchButton.current ? searchButton : document.activeElement===searchInput.current ? searchInput : null;
    const controller=new AbortController();searchRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);
    try {
      const result=await untilAborted(managementCommand("writer-agent","writer-history",{query},{signal:controller.signal}),controller.signal);
      if(selectionEpoch.current!==selectionAtStart)return;
      if(!result || !Array.isArray(result.jobs) || result.count!==result.jobs.length || result.jobs.some(job=>!job || typeof job.id!=="string" || typeof job.mode!=="string" || typeof job.stage!=="string" || [job.summary,job.error].some(value=>value!=null && typeof value!=="string")))throw new Error("이력 응답 형식을 확인할 수 없습니다.");
      setMatches(result.jobs);setSearchedQuery(query);setNotice("");
      if(!selected && result.jobs.filter(job=>job.id===query).length===1){resultTrigger.current=null;select(query);}
    }catch(problem){if(selectionEpoch.current===selectionAtStart && (!controller.signal.aborted || timedOut)){setNotice("이력 검색에 실패했습니다 · "+(timedOut ? "조회 시간이 초과됐습니다. 다시 검색하세요." : requestErrorMessage(problem))+(matches ? (matches.length ? " · 아래에는 마지막으로 확인한 검색 결과가 표시됩니다." : " · 마지막 검색 결과는 0건이었습니다.") : recent ? (recent.length ? " · 아래에는 마지막으로 확인한 최근 기록이 표시됩니다." : " · 마지막으로 확인한 최근 기록은 0건이었습니다.") : " · 최근 기록도 확인되지 않았습니다."),{error:true});}}
    finally{clearTimeout(timeout);if(searchRequest.current===controller)searchRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  const jobs=matches ?? recent ?? [];
  return <main className="writer-page-shell"><article className="writer-page generator-page-common">{!embedded && <nav aria-label="워크플로우 탐색"><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a></nav>}
    <h1 className={embedded ? "embedded-page-title" : undefined}>작가 AI 에이전트</h1><GeneratorChangelog generator="writer-agent" card/>
    <GeneratorSectionCard title="사용설명" summary="사용 방법과 제한 사항" className="vace-usage-card">
      <p>연결된 문서를 바탕으로 작성 제안을 만들거나 중복 내용을 검토합니다.</p>
      <ol><li>모델과 문서 폴더의 준비 상태를 확인하고 필요한 환경을 준비합니다.</li><li>문서를 학습해 검색 색인을 만든 뒤 작성 지시 또는 중복 검토 범위를 입력합니다.</li><li>요청 내용을 검토한 뒤 작업을 접수하고 이력에서 결과를 확인합니다.</li></ol>
      <p>중복 검토 범위를 비우면 전체 색인을 검사합니다. 작성 제안은 문서에 자동 적용되지 않습니다.</p>
    </GeneratorSectionCard>
    <GeneratorSectionNavigation inputRef={inputRegion} historyRef={historyRegion} resultRef={resultRef} inputReady={!proposalLoading} resultReady={Boolean(selected)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : model.ready ? "모델 파일 준비 완료" : "모델 파일 준비 필요"}><ModelReadiness session={session} service="writer-agent" onStatus={setModel} onError={setModelError}/><DownloadProgress service="writer-agent"/></GeneratorSectionCard>
    {proposalError && <p role="alert">{proposalError} · 기본 입력으로 계속할 수 있습니다.</p>}
    <GeneratorSectionCard title="작가 작업 입력" summary={writerInputSummary(workspaceState,proposalLoading)} defaultOpen className="writer-input-card"><div ref={inputRegion} tabIndex={-1} aria-label="작가 작업 입력">{proposalLoading ? <p role="status">대화 제안 확인 중…</p> : <WriterActions hideLegend session={session} proposalScope={proposalScope} initialPrompt={proposal?.prompt || ""} proposedMode={proposal?.mode || ""} onWorkspace={setRecent} onState={setWorkspaceState} onHistory={()=>{if(historyCard.current)historyCard.current.open=true;if(searchInput.current?.isConnected && !searchInput.current.matches(':disabled'))focusGeneratorRegion(searchInput.current);}} onAccepted={id=>{resultTrigger.current=null;select(id);setMatches(null);setNotice(id+" 작업을 접수했습니다.");}}/>}</div></GeneratorSectionCard>
    <GeneratorSectionCard title="작가 작업 이력" summary="검색과 선택 결과" cardRef={historyCard}>
    <div ref={historyRegion} tabIndex={-1} aria-label="작가 작업 이력">
    <form onSubmit={event=>{event.preventDefault();search();}}><label>이력 검색<input ref={searchInput} maxLength={200} value={query} disabled={busy} aria-describedby={busy ? searchStatusId : undefined} onChange={event=>setQuery(event.target.value)}/></label>
      <button ref={searchButton} disabled={busy} aria-describedby={busy ? searchStatusId : undefined}>{busy ? "이력 검색 중…" : query.trim()?"이력 검색":"전체 이력 검색"}</button></form>
    {busy && <p id={searchStatusId} role="status">이력을 검색하고 있습니다.{(matches || recent) && (jobs.length ? " 아래는 이전 조회 결과입니다." : " 이전 조회 결과는 0건이었습니다.")}</p>}
    {!busy && matches && query!==searchedQuery && <p role="status">검색어가 변경되었습니다. {matches.length ? "아래 결과는 이전 검색 조건으로 조회했습니다." : "이전 검색 결과는 0건이었습니다."} {query.trim()?"이력 검색":"전체 이력 검색"}을 눌러 적용하세요.</p>}
    {matches || recent ? <div className="writer-history-table"><ResultTable table={{title:"작가 실행 기록",emptyMessage:busy || noticeError || (matches && query!==searchedQuery) ? "마지막 조회에서 표시할 작업이 없었습니다." : matches ? searchedQuery.trim() ? "조회한 검색어와 일치하는 작업이 없습니다." : "조회한 작업 이력이 없습니다." : "최근 작업 기록이 없습니다.",summary:(matches?"검색 결과 ":"최근 기록 ")+jobs.length+"건",columns:["작업 ID","작업","상태","요약"],
      rows:jobs.map(job=>[<><JobIdentifier id={job.id} compact/><button type="button" disabled={busy} aria-describedby={busy ? searchStatusId : undefined} onClick={event=>{resultTrigger.current=event.currentTarget;if(selected===job.id)focusResult();else select(job.id);}}>작업 보기</button></>,writerModeLabel(job.mode),writerStageLabel(job.stage),job.summary || job.error])}}/></div> : <p>최근 기록을 확인하지 못했습니다. 준비 상태를 다시 확인하거나 전체 이력을 검색하세요.</p>}
    {notice && <p role={noticeError ? "alert" : "status"}>{notice}</p>}</div>
    {selected && <div ref={resultRef} tabIndex={-1} aria-label="선택한 작가 작업"><button type="button" onClick={closeResult}>결과 닫기</button><WriterResult key={selected} id={selected} onDeleted={(id,{restoreFocus}={})=>{select("");setRecent(rows=>rows?.filter(row=>row.id!==id) ?? null);setMatches(rows=>rows?.filter(row=>row.id!==id) ?? null);setNotice(id+" 기록을 휴지통으로 이동했습니다.");if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body)searchButton.current?.focus();});}}/></div>}
    </GeneratorSectionCard>
  </article></main>;
}
