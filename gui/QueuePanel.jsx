import WorkflowResults from "./WorkflowResults.jsx";
import ResultTable from "./ResultTable.jsx";
import QueuePriority from "./QueuePriority.jsx";
import React, {useEffect, useState} from "react";

const categories = {translation:"번역", image:"이미지", audio:"오디오", motion:"모션"};
const states = {
  ready:"접수 준비", waiting:"선행 단계 대기", awaiting_choice:"결과 선택 대기",
  submitting:"접수 중", queued:"실행 대기", running:"실행 중", paused:"일시 중지",
  completed:"완료", failed:"실패", cancelled:"취소", blocked:"차단", unknown:"확인 중"
};
const initial = {category:"", state:"", generator:"", run_id:"", job_id:"", created_from:"", created_through:""};

export default function QueuePanel({session, call, initialRun=""}) {
  const [selectedRun,setSelectedRun] = useState(initialRun);
  const [draft, setDraft] = useState({...initial,run_id:initialRun});
  const [filters, setFilters] = useState({...initial,run_id:initialRun});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const {category, state, ...search_filters} = filters;
    setResult(null);
    setError("");
    call("workflow-list", {session_id:session, category, state, search_filters})
      .then(data => { if (active) setResult(data); })
      .catch(problem => { if (active) setError(problem.message); });
    return () => { active = false; };
  }, [session, filters, call]);

  function field(name) {
    return {value:draft[name], onChange:event => setDraft({...draft, [name]:event.target.value})};
  }
  return <section className="panel session-queue" aria-label="세션 대기열">
    <form onSubmit={event => {event.preventDefault(); setSelectedRun(""); setFilters({...draft});}} style={{display:"block"}}>
      <label>카테고리 <select {...field("category")}><option value="">전체</option>
        {Object.entries(categories).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>상태 <select {...field("state")}><option value="">전체</option>
        {Object.entries(states).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <details><summary>상세 필터</summary>{Object.entries({generator:"생성기",run_id:"워크플로우 실행 ID",job_id:"단계 또는 작업 ID",created_from:"시작일",created_through:"종료일"}).map(([key,label]) =>
        <label key={key}>{label} <input type={key.startsWith("created_")?"date":"text"} {...field(key)}/></label>)}</details>
      <button>대기열 조회</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {!result && !error && <p role="status">조회 중…</p>}
    {result && <ResultTable table={{
      title:"워크플로우 대기열",
      summary:(result.truncated?"최근 100개 단계 표시":result.steps.length+"개 단계")+" · 조회 "+result.queried_at,
      columns:["생성기","단계","원본 작업 ID","상태","원본 관측 시각","실행 ID","우선순위"],
      rowKeys:result.steps.map(step=>step.request_id),
      rows:result.steps.map(step=>[
        step.generator,step.step_id,step.source_job_id || "—",
        (states[step.state] || step.state)+(step.source_state?" · "+(states[step.source_state] || step.source_state):""),
        step.observed_at || "관측 전",
        <button aria-label={step.run_id+" 결과 조회"} onClick={()=>setSelectedRun(step.run_id)}>{step.run_id}</button>,
        <QueuePriority step={step} call={call}/>
      ])
    }}/>}
    {selectedRun && <WorkflowResults key={selectedRun} session={session} run={selectedRun} openRun={setSelectedRun} call={call} close={()=>setSelectedRun("")}/>}
  </section>;
}
