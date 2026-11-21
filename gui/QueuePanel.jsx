import WorkflowResults from "./WorkflowResults.jsx";
import QueuePriority from "./QueuePriority.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import React, {useEffect, useRef, useState} from "react";
import JobIdentifier from "./JobIdentifier.jsx";
import RecentGeneratorJobs from "./RecentGeneratorJobs.jsx";
import QueuePagination from "./QueuePagination.jsx";

const categories = {translation:"번역", image:"이미지", audio:"오디오", motion:"모션"};
const states = {
  ready:"접수 준비", waiting:"선행 단계 대기", awaiting_choice:"결과 선택 대기",
  submitting:"접수 중", queued:"실행 대기", running:"실행 중", paused:"일시 중지",
  completed:"완료", failed:"실패", cancelled:"취소", blocked:"차단", unknown:"확인 중"
};
const initial = {category:"", state:"", generator:"", run_id:"", job_id:"", created_from:"", created_through:""};
function displayTime(value){const date=new Date(value);return value && !Number.isNaN(date.getTime())?date.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}):"확인 불가";}

export default function QueuePanel({session, call, editNextStep, openMessage, initialRun=""}) {
  const [selectedRun,setSelectedRun] = useState(initialRun);
  const [selectedDirect,setSelectedDirect]=useState("");
  const detail=useRef(null);
  useEffect(()=>{if(selectedRun || selectedDirect)detail.current?.scrollIntoView({block:"nearest"});},[selectedRun,selectedDirect]);
  const [draft, setDraft] = useState({...initial,run_id:initialRun});
  const [filters, setFilters] = useState({...initial,run_id:initialRun});
  const [result, setResult] = useState(null);
  const [page,setPage]=useState(0),[pageSize,setPageSize]=useState(5);
  const [error, setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [revision,refresh] = useState(0);
  useEffect(() => {
    let active = true;
    const {category, state, ...search_filters} = filters;
    setError("");
    setLoading(true);
    call("workflow-list", {session_id:session, category, state, search_filters})
      .then(data => { if (!Array.isArray(data?.steps) || (data.direct_jobs != null && !Array.isArray(data.direct_jobs))) throw new Error("작업 목록 응답을 읽을 수 없습니다."); if (active) setResult(data); })
      .catch(problem => { if (active) setError(problem.message || "조회에 실패했습니다."); })
      .finally(()=>{if(active)setLoading(false);});
    return () => { active = false; };
  }, [session, filters, call, revision]);

  useEffect(()=>setPage(0),[filters,session]);
  const jobs=result ? [...result.steps.map(step=>({kind:"workflow",step})),...(result.direct_jobs || []).map(step=>({kind:"direct",step}))].sort((a,b)=>(b.step.source_job_id || "").localeCompare(a.step.source_job_id || "")) : [];
  const currentPage=Math.min(page,Math.max(0,Math.ceil(jobs.length/pageSize)-1));
  const visibleJobs=jobs.slice(currentPage*pageSize,(currentPage+1)*pageSize);
  function field(name) {
    return {value:draft[name], onChange:event => setDraft({...draft, [name]:event.target.value})};
  }
  return <section className="panel session-queue" aria-label="세션 대기열">
    <form onSubmit={event => {event.preventDefault(); setSelectedRun("");setSelectedDirect(""); setFilters({...draft});}} style={{display:"block"}}>
      <label>카테고리 <select {...field("category")}><option value="">전체</option>
        {Object.entries(categories).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>상태 <select {...field("state")}><option value="">전체</option>
        {Object.entries(states).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <details><summary>상세 필터</summary>{Object.entries({generator:"생성기",run_id:"워크플로우 실행 ID",job_id:"단계 또는 작업 ID",created_from:"시작일",created_through:"종료일"}).map(([key,label]) =>
        <label key={key}>{label} <input type={key.startsWith("created_")?"date":"text"} {...field(key)}/></label>)}</details>
      <button>작업 조회</button>
      <button type="button" onClick={()=>refresh(n=>n+1)}>작업 목록 새로고침</button>
    </form>
    {error && <div role="alert"><p>작업 목록을 불러오지 못했습니다. 연결 상태를 확인해 주세요.</p>{result && <p>아래 목록은 마지막으로 조회한 정보입니다.</p>}<button type="button" onClick={()=>refresh(n=>n+1)}>다시 시도</button></div>}
    {loading && <p role="status">작업 목록 조회 중…{result && " 아래에는 이전 조회 결과가 표시됩니다."}</p>}
    {result && <section aria-label="세션 작업 목록"><h3>이 세션의 작업</h3><p>{result.steps.length+(result.direct_jobs || []).length}개 작업{(result.truncated || result.direct_truncated) && " · 일부 이전 항목 제외"} · 조회 {displayTime(result.queried_at)}</p>
      <div className="session-job-list">
        {visibleJobs.filter(item=>item.kind==="workflow").map(({step})=><article className="session-job" key={"workflow:"+step.request_id}>
          <div className="session-job-heading"><strong>{step.generator}</strong><span>{states[step.source_state] || states[step.state] || step.state}</span></div>
          <p>{step.step_id}</p>{step.source_job_id ? <JobIdentifier id={step.source_job_id} compact/> : <p>작업 ID 확인 중</p>}<small>관측 · {step.observed_at ? displayTime(step.observed_at) : "관측 전"}</small>
          <div className="session-job-actions"><button type="button" aria-label={step.run_id+" 결과 조회"} onClick={()=>{setSelectedDirect("");setSelectedRun(step.run_id);}}>상태·결과 보기</button>{step.state==="submitting" && step.source_state==="queued" && <QueuePriority step={step} call={call}/>}</div>
        </article>)}
        {visibleJobs.filter(item=>item.kind==="direct").map(({step})=><article className="session-job" key={"form:"+step.form_id}>
          <div className="session-job-heading"><strong>{step.generator} · 직접 접수</strong><span>{states[step.state] || step.state}</span></div>
          {step.source_job_id ? <JobIdentifier id={step.source_job_id} compact/> : <p>접수 확인 필요</p>}<small>관측 · {displayTime(step.observed_at)}</small>
          {step.source_job_id && <div className="session-job-actions"><button type="button" aria-label={step.source_job_id+" 결과 조회"} onClick={()=>{setSelectedRun("");setSelectedDirect(step.source_job_id);}}>상태·결과 보기</button>{openMessage && Number.isInteger(step.message_offset) && step.message_snapshot && <button type="button" onClick={()=>openMessage(step)}>관련 대화 보기</button>}</div>}
        </article>)}
      </div>
      {!jobs.length && <p>조건에 맞는 작업이 없습니다.</p>}
      {jobs.length>0 && <QueuePagination label="세션 작업 페이지" page={currentPage} size={pageSize} total={jobs.length} onPage={setPage} onSize={value=>{setPageSize(value);setPage(0);}}/>}
    </section>}
    <RecentGeneratorJobs session={session} filters={filters} revision={revision}/>
    {(selectedRun || selectedDirect) && <div ref={detail}>
      {selectedRun && <WorkflowResults editNextStep={editNextStep} key={selectedRun} session={session} run={selectedRun} openRun={setSelectedRun} call={call} close={()=>setSelectedRun("")}/>}
      {selectedDirect && <section aria-label="직접 접수 결과"><button type="button" onClick={()=>setSelectedDirect("")}>결과 닫기</button><MediaJobResult key={selectedDirect} service="wan22-fun-control" id={selectedDirect} folderLink/></section>}
    </div>}
  </section>;
}
