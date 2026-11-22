import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {requestErrorMessage} from "./requestError.mjs";

import MapDatabaseReceipt from "./MapDatabaseReceipt.jsx";
import BuildingSessionReceipts from "./BuildingSessionReceipts.jsx";

function validGpuTables(tables){
  return Array.isArray(tables) && tables.length===2 && ["GPU 대기열","GPU 예약"].every(title=>tables.filter(table=>table?.title===title).length===1) && tables.every(table=>table && typeof table.title==="string" && typeof table.available==="boolean" && typeof table.summary==="string" &&
    (!table.available || (Array.isArray(table.columns) && table.columns.every(column=>typeof column==="string") && Array.isArray(table.rows) &&
      table.rows.every(row=>Array.isArray(row) && row.length===table.columns.length && row.every(cell=>typeof cell==="string" || typeof cell==="number")) &&
      (table.title!=="GPU 대기열" || table.columns.length>=5) &&
      (table.inspection_targets===undefined || Array.isArray(table.inspection_targets) && table.inspection_targets.length===table.rows.length))));
}
function validOperationsPage(value,query,status,direction,previous){
  const page=value?.page;
  const expectedOffset=direction==="older" ? previous?.next_offset : direction==="newer" ? Math.max(0,(previous?.offset ?? 0)-30) : 0;
  return Boolean(value && typeof value.summary==="string" && Array.isArray(value.rows) &&
    value.rows.every(row=>Array.isArray(row) && row.length===5 && row.every(cell=>typeof cell==="string")) &&
    page && typeof page.query==="string" && (/^[\x00-\x7f]*$/.test(query.trim()) ? page.query===query.trim().toLowerCase() : direction==="first" || page.query===previous?.query) && page.status===status && Number.isInteger(page.offset) && page.offset>=0 && page.offset===expectedOffset &&
    (page.next_offset===null || Number.isInteger(page.next_offset) && page.next_offset>page.offset) &&
    typeof page.snapshot==="string" && /^[a-f0-9]{64}$/.test(page.snapshot) && (direction==="first" || previous && page.snapshot===previous.snapshot) &&
    (!value.statuses || typeof value.statuses==="object" && !Array.isArray(value.statuses) && Object.values(value.statuses).every(item=>typeof item==="string")));
}

export default function OperationsJobs({session,linkedJob,linkedStatus}){
  const storageKey="hermes-operations-search-"+(session || "");
  const [query,setQuery]=useState(()=>sessionStorage.getItem(storageKey) || "");
  const [status,setStatus]=useState(()=>sessionStorage.getItem(storageKey+"-status") || "전체");
  useEffect(()=>{sessionStorage.setItem(storageKey,query);sessionStorage.setItem(storageKey+"-status",status);},[storageKey,query,status]);
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [resultQuery,setResultQuery]=useState("");
  const [listError,setListError]=useState("");
  const listRequest=useRef(null),gpuRequest=useRef(null);
  useEffect(()=>()=>{listRequest.current?.abort();gpuRequest.current?.abort();},[]);
  const resultHeadingRef=useRef(null);
  useEffect(()=>{if(result)resultHeadingRef.current?.focus();},[result]);
  const [gpu,setGpu]=useState(null),[gpuError,setGpuError]=useState(""),[gpuCheckedAt,setGpuCheckedAt]=useState(null),[gpuStale,setGpuStale]=useState(false);
  const [priority,setPriority]=useState(null);
  const [receiptId,setReceiptId]=useState(""),[receiptNotice,setReceiptNotice]=useState("");
  async function readReceipt(){
    setBusy(true);setReceiptNotice("");
    try{
      const response=await fetch("/management/assistant/operations-"+(receiptId.trim().startsWith("recovery_")?"recovery":"priority")+"-receipt/"+encodeURIComponent(receiptId.trim()),{cache:"no-store"});
      if(!response.ok)throw new Error("접수 기록을 조회할 수 없습니다.");
      setReceiptNotice((await response.json()).notice);
    }catch(problem){setReceiptNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function reviewPriority(service,id){
    setBusy(true);setPriority(null);setGpuError("");
    try{
      const response=await fetch("/management/assistant/operations-priority-review",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({service,id})});
      if(!response.ok)throw new Error("대기 작업을 다시 조회하세요.");
      const review=await response.json();
      setPriority(review);setReceiptId(review.identifier || "");setReceiptNotice("");
    }catch(problem){setGpuError(problem.message);}
    finally{setBusy(false);}
  }
  async function prioritize(){
    const request=priority?.request;
    if(!request || busy)return;
    setBusy(true);setPriority({...priority,request:null});
    try{
      const receipt=await managementCommand("hermes-agent","hermes-priority-submit",request);
      if(receipt.state!=="completed" || receipt.request_id!==request.request_id || receipt.job_id!==request.id ||
         receipt.service!==request.service || receipt.ticket_revision!==request.ticket_revision)throw new Error();
      setPriority({notice:"우선순위 변경이 접수되었습니다. 대기열을 다시 조회하세요.",identifier:request.request_id});
    }catch{
      setPriority({notice:"접수 결과를 확인할 수 없습니다. 접수 ID로 운영 이력을 확인하세요.",identifier:request.request_id});
    }finally{setBusy(false);}
  }
  const [inspection,setInspection]=useState("");
  const [recovery,setRecovery]=useState(null),[outsideChecked,setOutsideChecked]=useState(false);
  async function reviewRecovery(target){
    setBusy(true);setRecovery(null);setOutsideChecked(false);setInspection("");setReceiptNotice("");
    try{
      const response=await fetch("/management/assistant/operations-recovery-review",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(target)});
      if(!response.ok)throw new Error("예약 정리 대상을 확인할 수 없습니다.");
      const review=await response.json();
      setRecovery(review);setReceiptId(review.identifier || "");
    }catch(problem){setInspection(problem.message);}
    finally{setBusy(false);}
  }
  async function recover(){
    const request=recovery?.request;
    if(busy || !outsideChecked || !request)return;
    setBusy(true);setRecovery(null);setOutsideChecked(false);
    try{
      const receipt=await managementCommand("hermes-agent","hermes-generator-reservation-recover",{...request,outside_processes_checked:true});
      if(receipt.state!=="completed" || receipt.request_id!==request.request_id || receipt.service!==request.service ||
         receipt.job_id!==request.job_id)throw new Error();
      setInspection("정리 완료 · "+request.service+" · "+request.job_id);
    }catch{setInspection("정리 결과를 확인하려면 접수 ID로 조회하세요.");}
    finally{setBusy(false);setReceiptId(request.request_id);}
  }
  async function inspectReservation(target){
    setRecovery(null);setOutsideChecked(false);
    setBusy(true);setInspection("");
    try{
      const response=await fetch("/management/assistant/operations-reservation-inspect",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(target)});
      if(!response.ok)throw new Error("예약 신원을 조회할 수 없습니다.");
      setInspection((await response.json()).notice);
    }catch(problem){setInspection(problem.message);}
    finally{setBusy(false);}
  }
  const [capture,setCapture]=useState("");
  async function inspectCapture(row){
    setBusy(true);setCapture("");
    try{
      const response=await fetch("/management/assistant/operations-capture-status",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({row})});
      if(!response.ok)throw new Error("캡처 접수 상태를 조회할 수 없습니다.");
      setCapture((await response.json()).notice);
    }catch(problem){setCapture(problem.message);}
    finally{setBusy(false);}
  }
  function gpuTable(table){
    if(table.inspection_targets)return {...table,columns:[...table.columns,"예약 조회"],rows:table.rows.map((row,index)=>{
      const target=table.inspection_targets[index];
      return [...row,target ? <><button disabled={gpuStale} onClick={()=>inspectReservation(target)}>예약 신원 확인</button><button disabled={gpuStale} onClick={()=>reviewRecovery(target)}>예약 정리 검토</button></> : "조회 대상 미확인"];
    })};
    if(table.title!=="GPU 대기열")return table;
    return {...table,columns:[...table.columns,"우선순위"],rows:table.rows.map(row=>{
      const source=row[3];
      const cells=[...row];
      if(row[1]==="review-capture" && source==="review-capture" && row[4]!=="미확인"){
        cells[4]=<button disabled={gpuStale} onClick={()=>inspectCapture(row)}>{row[4]} · 상태 조회</button>;
      }
      return [...cells,source==="미확인" ? "원 서비스 미확인" :
        <button disabled={gpuStale} onClick={()=>reviewPriority(source,row[2])}>우선 실행 검토</button>];
    })};
  }
  async function loadGpu(){
    const controller=new AbortController();gpuRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setCapture("");
    setRecovery(null);setOutsideChecked(false);
    setInspection("");
    setBusy(true);setGpuError("");setPriority(null);
    try{
      const response=await fetch("/management/assistant/operations-gpu",{cache:"no-store",signal:controller.signal});
      if(!response.ok)throw new Error("GPU 관측 기록을 불러올 수 없습니다.");
      const tables=await response.json();
      if(!validGpuTables(tables))throw new Error("GPU 관측 응답을 확인할 수 없습니다.");
      if(!controller.signal.aborted){setGpu(tables);setGpuCheckedAt(new Date());setGpuStale(false);}
    }catch(problem){if(!controller.signal.aborted || timedOut){setGpuStale(true);setGpuError((timedOut ? "GPU 관측 조회 시간이 초과됐습니다." : requestErrorMessage(problem))+(gpu ? " 이전 관측 결과를 표시합니다. 다시 조회한 뒤 작업을 선택하세요." : timedOut ? " 다시 조회하세요." : ""));}}
    finally{clearTimeout(timer);if(gpuRequest.current===controller){gpuRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  const [detail,setDetail]=useState(null),[detailCheckedAt,setDetailCheckedAt]=useState(null),[detailError,setDetailError]=useState("");
  const detailRef=useRef(null),detailTriggerRef=useRef(null),searchRef=useRef(null);
  useEffect(()=>{if(detail)detailRef.current?.focus();},[detail]);
  const [diffPage,setDiffPage]=useState(null);
  async function readDiff(cursor){
    setBusy(true);setError("");
    try{
      const response=await fetch("/management/assistant/operations-diff",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({id:detail.id,cursor})});
      const page=await response.json();
      if(!response.ok || page.cursor?.job_id!==detail.id)throw new Error(page.detail || "변경 내역을 확인할 수 없습니다.");
      setDiffPage(page);
    }catch(problem){setError(problem.message);setDiffPage(null);}
    finally{setBusy(false);}
  }
  async function inspectJob(id){
    const refreshing=detail?.id===id;
    if(!refreshing){setDiffPage(null);setDetail(null);}
    setBusy(true);setError("");setDetailError("");
    try{
      const record=await managementCommand("hermes-agent","hermes-detail",{id});
      if(record.id!==id || typeof record.status?.status!=="string")throw new Error("선택한 작업의 상세를 확인할 수 없습니다.");
      setDetail(record);setDetailCheckedAt(new Date());setDiffPage(null);
    }catch(problem){if(refreshing)setDetailError(requestErrorMessage(problem)+" 이전 조회 내용을 표시합니다.");else setError(requestErrorMessage(problem));}
    finally{setBusy(false);}
  }
  useEffect(()=>{
    if(linkedJob && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(linkedJob))inspectJob(linkedJob);
  },[linkedJob]);
  useEffect(()=>{
    if(linkedJob && linkedStatus && detail?.id===linkedJob && detail.status.status!==linkedStatus && !busy)inspectJob(linkedJob);
  },[linkedJob,linkedStatus]);
  async function load(direction){
    const controller=new AbortController();listRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");setListError("");
    try{
      const response=await fetch("/management/assistant/operations-jobs",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,
        body:JSON.stringify({query,status,direction,page:result?.page})});
      if(!response.ok)throw new Error("운영 작업 목록을 불러올 수 없습니다.");
      const data=await response.json();
      if(!validOperationsPage(data,query,status,direction,result?.page))throw new Error("운영 작업 목록 응답을 확인할 수 없습니다.");
      if(!controller.signal.aborted){setResult(data);setResultQuery(query.trim());setDetail(null);}
    }catch(problem){if(!controller.signal.aborted || timedOut)setListError((timedOut ? "운영 작업 목록 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem))+(result ? " 이전 조회 결과를 유지합니다." : ""));}
    finally{clearTimeout(timer);if(listRequest.current===controller){listRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  const page=result?.page;
  const same=page && resultQuery===query.trim() && page.status===status;
  const statusLabels={queued:"대기 중",pending:"대기 중",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",canceled:"취소"};
  const verificationLabels={...statusLabels,not_requested:"요청하지 않음",unknown:"확인 불가"};
  const filterStatuses=result?.statuses || {queued:"대기",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",paused:"일시정지",unknown:"확인 불가"};
  const pagination=()=> <nav aria-label="운영 작업 페이지 이동"><button type="button" disabled={!!listError || !same || !page.offset} onClick={()=>load("newer")}>이전 페이지</button>{" "}
    <button type="button" disabled={!!listError || !same || page.next_offset==null} onClick={()=>load("older")}>다음 페이지</button></nav>;
  return <fieldset className="operations-jobs" disabled={busy}><legend>운영 작업 이력</legend>
    {busy && <p role="status">요청을 처리하고 있습니다.</p>}
    <MapDatabaseReceipt/>
    <BuildingSessionReceipts key={session} session={session}/>
    <label>작업 ID 또는 지시문 <input ref={searchRef} value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter" && !e.nativeEvent.isComposing && !busy){e.preventDefault();load("first");}}}/></label>
    <label>작업 상태 <select value={status} onChange={e=>setStatus(e.target.value)}><option>전체</option>
      {status!=="전체" && !Object.hasOwn(filterStatuses,status) && <option value={status}>{status}</option>}
      {Object.entries(filterStatuses).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
    <button onClick={()=>load("first")}>작업 조회</button>
    {listError && <p role="alert">{listError}</p>}
    {error && <p role="alert">{error}</p>}
    {result && <><section className="operations-job-results" aria-label="운영 작업 목록"><h3 ref={resultHeadingRef} tabIndex={-1}>운영 작업</h3>
      {!same && <p className="operations-job-stale" role="status">검색 조건이 변경되었습니다. 아래는 이전 조회 결과입니다. 변경한 조건을 적용하려면 작업 조회를 누르세요.</p>}
      <p>{result.summary}</p>
      {pagination()}
      {result.rows.length ? <div className="operations-job-list">{result.rows.map(([id,state,gpuWait,prompt,reservation])=><article className="operations-job-card" key={id}>
        <div className="operations-job-heading"><strong>작업</strong><span className="operations-job-status">{state}</span></div>
        <JobIdentifier id={id} compact/><p className="operations-job-prompt">{prompt || "기록된 지시가 없습니다."}</p>
        <p className="operations-job-meta">GPU 대기 · {gpuWait}　 GPU 예약 · {reservation}</p>
        <button type="button" onClick={e=>{detailTriggerRef.current=e.currentTarget;inspectJob(id);}}>상세 보기</button>
      </article>)}</div> : <p>조회된 작업이 없습니다.</p>}</section>
      {pagination()}</>}
    {detail && <section ref={detailRef} tabIndex={-1} className="operations-job-detail" aria-label="운영 작업 상세"><div className="operations-job-heading"><h3>작업 상세</h3><span className="operations-job-status">{statusLabels[detail.status.status] || detail.status.status}</span></div>
      <JobIdentifier id={detail.id} compact/>
      {detailError && <p role="alert">{detailError}</p>}
      {detail.status.queue_position && <p>대기 순서 · {detail.status.queue_position}</p>}
      {detail.status.message && <p>{detail.status.message}</p>}
      {detail.status.error && <p role="alert">{detail.status.error}</p>}
      {detailCheckedAt && <p>조회 시각 · {detailCheckedAt.toLocaleString("ko-KR")}</p>}
      {detail.result?.verification && <section aria-label="독립 검증 결과"><h4>독립 검증</h4><p>{verificationLabels[detail.result.verification.status] || detail.result.verification.status || "상태 확인 불가"}{Number.isInteger(detail.result.verification.exit_code) && " · 종료 코드 "+detail.result.verification.exit_code}</p>{Array.isArray(detail.result.verification.modules) && detail.result.verification.modules.length>0 && <p>검증 대상 · {detail.result.verification.modules.join(", ")}</p>}{detail.result.partial && <p>작업 결과가 부분 완료로 기록됐습니다. 최종 응답과 검증 결과를 함께 확인하세요.</p>}</section>}
      <details><summary>작업 로그</summary><pre tabIndex={0} aria-label="작업 로그 내용">{detail.log || "기록된 로그가 없습니다."}</pre></details>
      <h4>작업 지시</h4><pre tabIndex={0} aria-label="작업 지시 내용">{detail.request?.prompt || "기록된 지시가 없습니다."}</pre>
      <h4>최종 응답</h4><pre tabIndex={0} aria-label="최종 응답 내용">{detail.final_response || "기록된 최종 응답이 없습니다."}</pre>
      {detail.final_response_truncated && <p>응답 일부만 표시했습니다.</p>}
      <details><summary>변경 내역</summary>{detail.diff_truncated && <p>변경 내역 일부만 표시했습니다.</p>}<pre tabIndex={0} aria-label="변경 내역 내용">{diffPage?.text ?? (detail.diff || "기록된 변경이 없습니다.")}</pre>
        {detail.diff_truncated && <><button onClick={()=>readDiff(null)}>처음 부분부터 조회</button>
          {diffPage && <p>{diffPage.notice}</p>}
          {diffPage?.cursor.next_offset!=null && <button onClick={()=>readDiff(diffPage.cursor)}>다음 부분 조회</button>}</>}
      </details>
      {detail.result && <details><summary>결과 기록</summary><pre tabIndex={0} aria-label="결과 기록 내용">{JSON.stringify(detail.result,null,2)}</pre></details>}
      <button onClick={()=>inspectJob(detail.id)}>상세 새로고침</button>
      <button type="button" onClick={()=>{setDetail(null);(detailTriggerRef.current?.isConnected ? detailTriggerRef.current : searchRef.current)?.focus();}}>상세 닫기</button>
    </section>}
    <button onClick={loadGpu}>GPU 대기열·예약 조회</button>
    {gpuError && <p role="alert">{gpuError}</p>}
    {gpuCheckedAt && <p>GPU 관측 시각 · {gpuCheckedAt.toLocaleString("ko-KR")}{gpuStale && " · 이전 결과"}</p>}
    {gpu?.map(table=>table.available ? <div className="operations-gpu-table" role="region" aria-label={table.title+" 표"} tabIndex={0} key={table.title}><ResultTable table={gpuTable(table)}/></div> :
      <p role="status" key={table.title}>{table.summary}</p>)}
    {capture && <p role="status">{capture}</p>}
    {inspection && <p role="status">{inspection}</p>}
    {priority && <section><p role="status">{priority.notice}</p>{priority.identifier && <JobIdentifier id={priority.identifier} compact/>}
      {priority.request && <><button onClick={()=>setPriority(null)}>취소</button>
        <button onClick={prioritize}>확인 후 우선순위 변경</button></>}</section>}
    {recovery && <section><p role="status">{recovery.notice}</p>
      {recovery.request && <><label><input type="checkbox" checked={outsideChecked} onChange={e=>setOutsideChecked(e.target.checked)}/>별도 그룹의 GPU 프로세스를 확인했습니다</label>
        <button onClick={()=>setRecovery(null)}>취소</button><button disabled={!outsideChecked} onClick={recover}>확인 후 예약 정리</button></>}</section>}
    <label>우선순위 변경·예약 정리 접수 ID <input value={receiptId} aria-describedby="operations-receipt-hint" placeholder="priority_… 또는 recovery_…" onChange={e=>{setReceiptId(e.target.value);setReceiptNotice("");}}/></label>
    <p id="operations-receipt-hint">접수 시 표시된 ID 전체를 입력하세요. priority_ 또는 recovery_ 뒤에 숫자와 a–f로 된 64자리가 이어집니다.</p>
    <button disabled={!/^(priority|recovery)_[a-f0-9]{64}$/.test(receiptId.trim())} onClick={readReceipt}>접수 결과 조회</button>
    {receiptNotice && <p role="status">{receiptNotice}</p>}
  </fieldset>;
}
