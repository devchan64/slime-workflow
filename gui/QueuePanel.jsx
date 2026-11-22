import WorkflowResults from "./WorkflowResults.jsx";
import QueuePriority from "./QueuePriority.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import WriterResult from "./WriterResult.jsx";
import React, {useEffect, useId, useRef, useState} from "react";
import JobIdentifier from "./JobIdentifier.jsx";
import RecentGeneratorJobs from "./RecentGeneratorJobs.jsx";
import QueuePagination from "./QueuePagination.jsx";
import {newestSessionJobs,parseSessionTime} from "./sessionJobOrder.mjs";

const categories = {translation:"번역", image:"이미지", audio:"오디오", motion:"모션"};
const states = {
  ready:"접수 준비", waiting:"선행 단계 대기", awaiting_choice:"결과 선택 대기",
  submitting:"접수 중", queued:"실행 대기", running:"실행 중", paused:"일시 중지",
  completed:"완료", failed:"실패", cancelled:"취소", blocked:"차단", unknown:"확인 중"
};
const initial = {category:"", state:"", generator:"", run_id:"", job_id:"", created_from:"", created_through:""};
function displayTime(value){const time=parseSessionTime(value);return Number.isFinite(time)?new Date(time).toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}):"확인 불가";}
function pendingFluxLabel(step){
  if(!["flux_proposal","writer_proposal"].includes(step.source_kind))return "접수 확인 필요";
  if(["approved","waiting_release","submitting"].includes(step.handoff_state))return "GPU 양도 진행 중 · 작업 ID 생성 전";
  if(["cancel_waiting_release","cancel_reload_queued","cancel_reloading"].includes(step.handoff_state))return "양도 중지 및 모델 복구 중 · 작업 ID 생성 전";
  if(step.handoff_state==="cancelled")return "양도 취소됨 · 생성 작업 없음";
  if(step.handoff_state==="withdrawn")return "미접수 양도 요청 철회됨 · 생성 작업 없음";
  if(["rejected_reload_queued","rejected_reloading"].includes(step.handoff_state))return "생성 요청 검증 실패 · 모델 복구 중";
  if(step.handoff_state==="rejected")return "생성 요청 검증 실패 · 생성 작업 없음";
  if(step.receipt_state==="rejected")return "생성 요청 거절 · 모델 복구 상태 확인 필요";
  return "접수 확인 필요";
}

export default function QueuePanel({session, call, editNextStep, openMessage, choose, initialRun="", filterCache}) {
  const dateErrorId=useId();
  const [selectedRun,setSelectedRun] = useState(initialRun);
  const [selectedDirect,setSelectedDirect]=useState("");
  const detail=useRef(null),resultTrigger=useRef(null),listHeading=useRef(null);
  useEffect(()=>{
    if(!(selectedRun || selectedDirect) || !detail.current)return;
    detail.current.focus({preventScroll:true});
    if(resultTrigger.current)detail.current.scrollIntoView({block:"start",inline:"nearest"});
  },[selectedRun,selectedDirect]);
  function closeResult(){
    setSelectedRun("");setSelectedDirect("");
    requestAnimationFrame(()=>resultTrigger.current?.isConnected && resultTrigger.current.focus());
  }
  const [draft, setDraft] = useState(()=>!initialRun && filterCache?.current[session]?.draft || {...initial,run_id:initialRun});
  const [filters, setFilters] = useState(()=>!initialRun && filterCache?.current[session]?.filters || {...initial,run_id:initialRun});
  const [result, setResult] = useState(null),[resultFilters,setResultFilters]=useState(null);
  const [page,setPage]=useState(0),[pageSize,setPageSize]=useState(()=>filterCache?.current[session]?.pageSize || 5);
  useEffect(()=>{if(filterCache)filterCache.current[session]={draft,filters,pageSize};},[filterCache,session,draft,filters,pageSize]);
  const [error, setError] = useState("");
  const [navigationError,setNavigationError]=useState("");
  const [loading,setLoading] = useState(true);
  const [revision,refresh] = useState(0);
  useEffect(() => {
    let active = true;
    const {category, state, ...search_filters} = filters;
    setError("");
    setNavigationError("");
    setLoading(true);
    call("workflow-list", {session_id:session, category, state, search_filters})
      .then(data => { if (!Array.isArray(data?.steps) || (data.direct_jobs != null && !Array.isArray(data.direct_jobs))) throw new Error("작업 목록 응답을 읽을 수 없습니다."); if (active) {setResult(data);setResultFilters(filters);} })
      .catch(problem => { if (active) setError(problem.message || "조회에 실패했습니다."); })
      .finally(()=>{if(active)setLoading(false);});
    return () => { active = false; };
  }, [session, filters, call, revision]);

  useEffect(()=>setPage(0),[filters,session]);
  const jobs=result ? newestSessionJobs([...result.steps.map(step=>({kind:"workflow",step})),...(result.direct_jobs || []).map(step=>({kind:"direct",step}))]) : [];
  const currentPage=Math.min(page,Math.max(0,Math.ceil(jobs.length/pageSize)-1));
  const visibleJobs=jobs.slice(currentPage*pageSize,(currentPage+1)*pageSize);
  const filtersChanged=Object.keys(initial).some(key=>draft[key]!==filters[key]);
  function describeFilters(value){return [value.category && "카테고리: "+(categories[value.category] || value.category),value.state && "상태: "+(states[value.state] || value.state),value.generator && "생성기: "+value.generator,value.run_id && "워크플로우 ID: "+value.run_id,value.job_id && "작업 ID: "+value.job_id,value.created_from && "시작일: "+value.created_from,value.created_through && "종료일: "+value.created_through].filter(Boolean).join(" · ") || "전체";}
  const filterSummary=describeFilters(filters),resultFilterSummary=describeFilters(resultFilters || filters);
  const invalidDateRange=Boolean(draft.created_from && draft.created_through && draft.created_from>draft.created_through);
  function field(name) {
    return {value:draft[name], onChange:event => setDraft({...draft, [name]:event.target.value})};
  }
  return <section className="panel session-queue" aria-label="세션 대기열">
    <form onSubmit={event => {event.preventDefault(); if(invalidDateRange)return; const normalized=Object.fromEntries(Object.entries(draft).map(([key,value])=>[key,value.trim()])); setDraft(normalized);setSelectedRun("");setSelectedDirect(""); setFilters(normalized);}} style={{display:"block"}}>
      <label>카테고리 <select {...field("category")}><option value="">전체</option>
        {Object.entries(categories).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>상태 <select {...field("state")}><option value="">전체</option>
        {Object.entries(states).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <details><summary>상세 필터</summary>{Object.entries({generator:"생성기",run_id:"워크플로우 실행 ID",job_id:"단계 또는 작업 ID",created_from:"시작일",created_through:"종료일"}).map(([key,label]) =>
        <label key={key}>{label} <input type={key.startsWith("created_")?"date":"text"} aria-invalid={key.startsWith("created_") && invalidDateRange || undefined} aria-describedby={key.startsWith("created_") && invalidDateRange ? dateErrorId : undefined} {...field(key)}/></label>)}<small>날짜 기준 · 한국 시간. 생성기와 작업 ID는 일부 값으로 검색할 수 있습니다. 워크플로우 실행 ID는 전체 값을 입력하세요.</small></details>
      {invalidDateRange && <p id={dateErrorId} role="alert">상세 필터의 시작일은 종료일보다 늦을 수 없습니다.</p>}
      <button disabled={invalidDateRange}>작업 조회</button>
      <button type="button" onClick={()=>{setDraft({...initial});setFilters({...initial});setSelectedRun("");setSelectedDirect("");}}>필터 초기화</button>
      <button type="button" onClick={()=>refresh(n=>n+1)}>작업 목록 새로고침</button>
    </form>
    {filtersChanged && <p className="queue-filter-notice" role="status">필터가 변경되었습니다. 아래 목록은 이전 조건의 결과입니다. {invalidDateRange ? "날짜 범위를 수정한 뒤 조회하세요." : "두 목록에 적용하려면 작업 조회를 누르세요."}</p>}
    {error && <div role="alert"><p>{error.includes("세션 이력이") ? "대화 이력이 조회 중 변경되었습니다. 작업 목록을 다시 조회하세요." : "작업 목록을 불러오지 못했습니다. 연결 상태를 확인해 주세요."}</p>{result && <p>아래 목록은 마지막으로 조회한 정보입니다.</p>}<button type="button" onClick={()=>refresh(n=>n+1)}>다시 시도</button></div>}
    {navigationError && <p role="alert">{navigationError}</p>}
    {loading && <p role="status">작업 목록 조회 중…{result && " 아래에는 이전 조회 결과가 표시됩니다."}</p>}
    {result && <section aria-label="세션 작업 목록"><h3 ref={listHeading} tabIndex={-1}>이 세션의 작업</h3><p className="queue-filter-summary">적용된 조건 · {resultFilterSummary}</p><p>{result.steps.length+(result.direct_jobs || []).length}개 작업{(result.truncated || result.direct_truncated) && " · 일부 이전 항목 제외"} · 조회 {displayTime(result.queried_at)}</p>{result.flux_proposal_unreadable_count>0 && <p role="status">대화 작업 {result.flux_proposal_unreadable_count}건의 제안을 확인하지 못했습니다. 이 작업들의 FLUX 접수 여부는 목록에서 확인할 수 없습니다.</p>}{result.writer_proposal_unreadable_count>0 && <p role="status">대화 작업 {result.writer_proposal_unreadable_count}건의 작가 제안 접수 여부를 확인하지 못했습니다.</p>}
      <div className="session-job-list">
        {visibleJobs.map(({kind,step})=>kind==="workflow" ? <article className="session-job" key={"workflow:"+step.request_id}>
          <div className="session-job-heading"><strong>{step.generator}</strong><span>{states[step.source_state] || states[step.state] || step.state}</span></div>
          <p>{step.step_id}</p>{step.source_job_id ? <JobIdentifier id={step.source_job_id} compact/> : <p>작업 ID 확인 중</p>}<div className="queue-job-times"><small>생성 · {displayTime(step.created_at)}</small><small>관측 · {step.observed_at ? displayTime(step.observed_at) : "관측 전"}</small></div>
          <div className="session-job-actions"><button type="button" aria-label={step.run_id+(selectedRun===step.run_id?" 결과 닫기":" 결과 조회")} aria-expanded={selectedRun===step.run_id} onClick={event=>{if(selectedRun===step.run_id)closeResult();else{resultTrigger.current=event.currentTarget;setSelectedDirect("");setSelectedRun(step.run_id);}}}>{selectedRun===step.run_id?"결과 닫기":"상태·결과 보기"}</button>{step.state==="submitting" && step.source_state==="queued" && <QueuePriority step={step} call={call}/>}</div>
        </article> : <article className="session-job" key={"direct:"+step.request_id}>
          <div className="session-job-heading"><strong>{step.generator}</strong><span>{states[step.state] || step.state}</span></div>
          <small>{["flux_proposal","writer_proposal"].includes(step.source_kind) ? "대화 제안" : "직접 접수"}</small>
          {step.source_job_id ? <JobIdentifier id={step.source_job_id} compact/> : <p>{pendingFluxLabel(step)}</p>}<div className="queue-job-times"><small>생성 · {displayTime(step.created_at)}</small><small>관측 · {displayTime(step.observed_at)}</small></div>
          {(step.source_job_id || step.proposal_job_id) && <div className="session-job-actions">{step.source_job_id && <button type="button" aria-label={step.source_job_id+(selectedDirect?.id===step.source_job_id && selectedDirect?.service===step.generator?" 결과 닫기":" 결과 조회")} aria-expanded={selectedDirect?.id===step.source_job_id && selectedDirect?.service===step.generator} onClick={event=>{if(selectedDirect?.id===step.source_job_id && selectedDirect?.service===step.generator)closeResult();else{resultTrigger.current=event.currentTarget;setSelectedRun("");setSelectedDirect({id:step.source_job_id,service:step.generator,kind:step.source_kind==="writer_proposal"?"writer":step.source_kind==="flux_proposal"?"flux":"video"});}}}>{selectedDirect?.id===step.source_job_id && selectedDirect?.service===step.generator?"결과 닫기":"상태·결과 보기"}</button>}{openMessage && (step.form_id || step.proposal_job_id) && Number.isInteger(step.message_offset) && step.message_snapshot && <button type="button" onClick={()=>{if(openMessage(step)===false)setNavigationError("대화 이력이 변경되었거나 연결 정보가 올바르지 않습니다. 작업 목록을 새로고침하세요.");}}>관련 대화 보기</button>}</div>}
        </article>)}
      </div>
      {!jobs.length && <p>조건에 맞는 작업이 없습니다.</p>}
      {jobs.length>0 && <QueuePagination label="세션 작업 페이지" page={currentPage} size={pageSize} total={jobs.length} onPage={value=>{setSelectedRun("");setSelectedDirect("");setPage(value);}} onPageFocus={()=>listHeading.current?.focus()} onSize={value=>{setSelectedRun("");setSelectedDirect("");setPageSize(value);setPage(0);}}/>}
    </section>}
    {(selectedRun || selectedDirect) && <div ref={detail} tabIndex={-1} aria-label="선택한 작업 결과">
      {selectedRun && <WorkflowResults editNextStep={editNextStep} key={selectedRun} session={session} run={selectedRun} openRun={setSelectedRun} call={call} close={closeResult}/>}
      {selectedDirect && <section aria-label="직접 접수 결과"><button type="button" onClick={closeResult}>결과 닫기</button>{selectedDirect.kind==='writer' ? <WriterResult key={selectedDirect.id} id={selectedDirect.id} onDeleted={()=>{setSelectedDirect("");refresh(value=>value+1);}}/> : <MediaJobResult key={selectedDirect.service+selectedDirect.id} service={selectedDirect.service} id={selectedDirect.id} kind={selectedDirect.kind} folderLink/>}</section>}
    </div>}
    <RecentGeneratorJobs session={session} filters={filters} filterSummary={filterSummary} revision={revision} choose={choose}/>
  </section>;
}
