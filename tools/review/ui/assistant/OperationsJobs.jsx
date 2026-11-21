import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function MapDatabaseReceipt(){
  const [id,setId]=useState(""),[hash,setHash]=useState("");
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  async function lookup(){
    setBusy(true);setNotice("");
    try{
      const receipt=await managementCommand("hermes-agent","hermes-map-database-receipt",{database_request_id:id,request_sha256:hash});
      if(receipt.request_sha256!==hash)throw new Error();
      const messages=new Map([
        ["matched","DB 접수의 요청 해시가 일치합니다. 파일 동기화 상태는 별도로 확인하세요."],
        ["mismatch","보관한 요청 해시와 DB 접수 기록이 다릅니다. 원래 요청을 확인하세요."],
        ["not_found","조회 시점에 DB 접수 기록이 없습니다. 진행 중인 작업의 상태를 확인하세요."],
      ]);
      if(!messages.has(receipt.state))throw new Error();
      setNotice(messages.get(receipt.state));
    }catch{setNotice("DB 접수를 확인할 수 없습니다. 요청 ID·해시와 에셋 서비스 연결을 확인하세요.");}
    finally{setBusy(false);}
  }
  return <details><summary>맵 DB 변경 접수 확인</summary><fieldset disabled={busy}>
    <label>DB 요청 ID <input value={id} onChange={e=>{setId(e.target.value);setNotice("");}}/></label>
    <label>원본 요청 SHA-256 <input value={hash} onChange={e=>{setHash(e.target.value);setNotice("");}}/></label>
    <button disabled={!id.trim() || !/^[a-f0-9]{64}$/.test(hash)} onClick={lookup}>DB 접수 확인</button>
    {notice && <p role="status">{notice}</p>}
  </fieldset></details>;
}

export default function OperationsJobs(){
  const [query,setQuery]=useState(""),[status,setStatus]=useState("전체");
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [gpu,setGpu]=useState(null),[gpuError,setGpuError]=useState("");
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
      return [...row,target ? <><button onClick={()=>inspectReservation(target)}>예약 신원 확인</button><button onClick={()=>reviewRecovery(target)}>예약 정리 검토</button></> : "조회 대상 미확인"];
    })};
    if(table.title!=="GPU 대기열")return table;
    return {...table,columns:[...table.columns,"우선순위"],rows:table.rows.map(row=>{
      const source=row[3];
      const cells=[...row];
      if(row[1]==="review-capture" && source==="review-capture" && row[4]!=="미확인"){
        cells[4]=<button onClick={()=>inspectCapture(row)}>{row[4]} · 상태 조회</button>;
      }
      return [...cells,source==="미확인" ? "원 서비스 미확인" :
        <button onClick={()=>reviewPriority(source,row[2])}>우선 실행 검토</button>];
    })};
  }
  async function loadGpu(){
    setCapture("");
    setRecovery(null);setOutsideChecked(false);
    setInspection("");
    setBusy(true);setGpuError("");setPriority(null);
    try{
      const response=await fetch("/management/assistant/operations-gpu",{cache:"no-store"});
      if(!response.ok)throw new Error("GPU 관측 기록을 불러올 수 없습니다.");
      setGpu(await response.json());
    }catch(problem){setGpu(null);setGpuError(problem.message);}
    finally{setBusy(false);}
  }
  const [detail,setDetail]=useState(null);
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
    setDiffPage(null);
    setBusy(true);setError("");setDetail(null);
    try{
      const record=await managementCommand("hermes-agent","hermes-detail",{id});
      if(record.id!==id || typeof record.status?.status!=="string")throw new Error("선택한 작업의 상세를 확인할 수 없습니다.");
      setDetail(record);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function load(direction){
    setDetail(null);
    setBusy(true);setError("");
    try{
      const response=await fetch("/management/assistant/operations-jobs",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({query,status,direction,page:result?.page})});
      if(!response.ok)throw new Error("운영 작업 목록을 불러올 수 없습니다.");
      setResult(await response.json());
    }catch(problem){setError(problem.message);setResult(null);}
    finally{setBusy(false);}
  }
  const page=result?.page;
  const same=page && page.query===query.trim().toLowerCase() && page.status===status;
  return <fieldset disabled={busy}><legend>운영 작업 이력</legend>
    <MapDatabaseReceipt/>
    <label>작업 ID 또는 지시문 <input value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <label>작업 상태 <select value={status} onChange={e=>setStatus(e.target.value)}><option>전체</option>
      {Object.entries(result?.statuses || {}).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
    <button onClick={()=>load("first")}>작업 조회</button>
    {error && <p role="alert">{error}</p>}
    {result && <><ResultTable table={{title:"운영 작업",summary:result.summary,columns:["작업 ID","상태","GPU 대기","지시문","GPU 예약"],rows:result.rows.map(([id,...cells])=>[<button onClick={()=>inspectJob(id)}>{id}</button>,...cells])}}/>
      <button disabled={!same || !page.offset} onClick={()=>load("newer")}>이전 페이지</button>
      <button disabled={!same || page.next_offset==null} onClick={()=>load("older")}>다음 페이지</button></>}
    {detail && <section aria-label="운영 작업 상세"><h3>{detail.id}</h3>
      <p>{detail.status.status}{detail.status.queue_position ? " · 대기 순서 "+detail.status.queue_position : ""} {detail.status.message} {detail.status.error}</p>
      <h4>작업 지시</h4><pre>{detail.request?.prompt || "기록된 지시가 없습니다."}</pre>
      <h4>최종 응답</h4><pre>{detail.final_response || "기록된 최종 응답이 없습니다."}</pre>
      {detail.final_response_truncated && <p>응답 일부만 표시했습니다.</p>}
      {detail.result?.verification && <p>독립 검증 · {detail.result.verification.status}</p>}
      <details><summary>변경 내역</summary>{detail.diff_truncated && <p>변경 내역 일부만 표시했습니다.</p>}<pre>{diffPage?.text ?? (detail.diff || "기록된 변경이 없습니다.")}</pre>
        {detail.diff_truncated && <><button onClick={()=>readDiff(null)}>처음 부분부터 조회</button>
          {diffPage && <p>{diffPage.notice}</p>}
          {diffPage?.cursor.next_offset!=null && <button onClick={()=>readDiff(diffPage.cursor)}>다음 부분 조회</button>}</>}
      </details>
      <details><summary>작업 로그</summary><pre>{detail.log || "기록된 로그가 없습니다."}</pre></details>
      {detail.result && <details><summary>결과 기록</summary><pre>{JSON.stringify(detail.result,null,2)}</pre></details>}
      <button onClick={()=>inspectJob(detail.id)}>상세 새로고침</button>
    </section>}
    <button onClick={loadGpu}>GPU 대기열·예약 조회</button>
    {gpuError && <p role="alert">{gpuError}</p>}
    {gpu?.map(table=>table.available ? <ResultTable key={table.title} table={gpuTable(table)}/> :
      <p role="status" key={table.title}>{table.summary}</p>)}
    {capture && <p role="status">{capture}</p>}
    {inspection && <p role="status">{inspection}</p>}
    {priority && <section><p role="status">{priority.notice}</p>{priority.identifier && <code>{priority.identifier}</code>}
      {priority.request && <><button onClick={()=>setPriority(null)}>취소</button>
        <button onClick={prioritize}>확인 후 우선순위 변경</button></>}</section>}
    {recovery && <section><p role="status">{recovery.notice}</p>
      {recovery.request && <><label><input type="checkbox" checked={outsideChecked} onChange={e=>setOutsideChecked(e.target.checked)}/>별도 그룹의 GPU 프로세스를 확인했습니다</label>
        <button onClick={()=>setRecovery(null)}>취소</button><button disabled={!outsideChecked} onClick={recover}>확인 후 예약 정리</button></>}</section>}
    <label>우선순위 변경·예약 정리 접수 ID <input value={receiptId} onChange={e=>{setReceiptId(e.target.value);setReceiptNotice("");}}/></label>
    <button disabled={!/^(priority|recovery)_[a-f0-9]{64}$/.test(receiptId.trim())} onClick={readReceipt}>접수 결과 조회</button>
    {receiptNotice && <p role="status">{receiptNotice}</p>}
  </fieldset>;
}
