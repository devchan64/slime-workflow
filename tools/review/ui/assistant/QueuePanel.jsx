import WorkflowResults from "./WorkflowResults.jsx";
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
  return <section className="panel" aria-label="세션 대기열">
    <form onSubmit={event => {event.preventDefault(); setSelectedRun(""); setFilters({...draft});}} style={{display:"block"}}>
      <label>카테고리 <select {...field("category")}><option value="">전체</option>
        {Object.entries(categories).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>상태 <select {...field("state")}><option value="">전체</option>
        {Object.entries(states).map(([key,label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      {Object.entries({generator:"생성기",run_id:"워크플로우 실행 ID",job_id:"단계 또는 작업 ID",created_from:"시작일",created_through:"종료일"}).map(([key,label]) =>
        <label key={key}>{label} <input type={key.startsWith("created_")?"date":"text"} {...field(key)}/></label>)}
      <button>대기열 조회</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {!result && !error && <p role="status">조회 중…</p>}
    {result && <><p>{result.truncated ? "최근 100개 단계 표시" : result.steps.length + "개 단계"}</p>
      {result.steps.length > 0 && <table><thead><tr><th>생성기</th><th>단계</th><th>상태</th><th>실행 ID</th><th>우선순위</th></tr></thead>
        <tbody>{result.steps.map(step => <tr key={step.request_id}>
          <td>{step.generator}</td><td>{step.step_id}</td>
          <td>{states[step.state] || step.state}{step.source_state && " · " + (states[step.source_state] || step.source_state)}</td>
          <td><button aria-label={step.run_id + " 결과 조회"} onClick={()=>setSelectedRun(step.run_id)}>{step.run_id}</button></td><td><QueuePriority step={step} call={call}/></td></tr>)}</tbody></table>}
    </>}
    {selectedRun && <WorkflowResults key={selectedRun} session={session} run={selectedRun} openRun={setSelectedRun} call={call} close={()=>setSelectedRun("")}/>}
  </section>;
}
