import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

import MapDatabaseReceipt from "./MapDatabaseReceipt.jsx";
import BuildingSessionReceipts from "./BuildingSessionReceipts.jsx";

export function OperationsRefreshStatus({loading,hasPrevious,label}){
  return loading && hasPrevious ? <p role="status">{label}을 다시 조회하는 중입니다. 아래는 마지막 조회 결과입니다.</p> : null;
}
export function OperationsPagination({position,canPrevious,canNext,onPage}){
  return <nav className="ui-action-row" aria-label={"운영 작업 페이지 이동 · 목록 "+position}>
    <button type="button" disabled={!canPrevious} onClick={event=>onPage("newer",event)}>이전 페이지</button>
    <button type="button" disabled={!canNext} onClick={event=>onPage("older",event)}>다음 페이지</button>
  </nav>;
}

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

export function FinalResponse({text,truncated}){
  if(text!=null && typeof text!=="string")return <><h4>최종 응답</h4><p role="alert">최종 응답의 형식을 확인할 수 없습니다. 상세를 다시 조회하세요.</p></>;
  const answer=text?.trimEnd();
  if(!answer)return <><h4>최종 응답</h4><p>기록된 최종 응답이 없습니다.</p></>;
  const lines=answer.split(/\r?\n/);
  const ending=Array.from(lines.slice(-2).join(" ").trim());
  const preview=(lines.length>2 || ending.length>100 ? "… " : "")+ending.slice(-100).join("");
  return <details className="job-final-response">
    <summary>최종 응답 <span className="response-preview">{preview}</span></summary>
    <pre tabIndex={0} aria-label="최종 응답 내용">{text}</pre>
    {truncated && <p>응답 일부만 표시했습니다.</p>}
  </details>;
}

export function operationStatusLabel(labels,value){
  return typeof value!=="string" || !value ? "상태 확인 불가" : Object.hasOwn(labels,value) ? labels[value] : value;
}

export function OperationsDetailData({detail,verificationLabels}){
  return <>
    {Number.isInteger(detail.status.queue_position) && detail.status.queue_position>0 && <p>대기 순서 · {detail.status.queue_position}</p>}
    {typeof detail.status.message==="string" && detail.status.message && <p>{detail.status.message}</p>}
    {typeof detail.status.error==="string" && detail.status.error && <p role="alert">{detail.status.error}</p>}
    {([detail.status.message,detail.status.error].some(value=>value!=null && typeof value!=="string") || detail.status.queue_position!=null && (!Number.isInteger(detail.status.queue_position) || detail.status.queue_position<0)) && <p role="alert">작업 상태의 일부 형식을 확인할 수 없습니다. 상세를 다시 조회하세요.</p>}
    <h4>작업 지시</h4><pre tabIndex={0} aria-label="작업 지시 내용">{typeof detail.request?.prompt==="string" ? detail.request.prompt || "기록된 지시가 없습니다." : detail.request?.prompt == null ? "기록된 지시가 없습니다." : "작업 지시 형식을 확인할 수 없습니다."}</pre>
    <FinalResponse key={detail.id} text={detail.final_response} truncated={detail.final_response_truncated}/>
    {detail.result?.verification && <section aria-label="독립 검증 결과"><h4>독립 검증</h4><p>{operationStatusLabel(verificationLabels,detail.result.verification.status)}{Number.isInteger(detail.result.verification.exit_code) && " · 종료 코드 "+detail.result.verification.exit_code}</p>{Array.isArray(detail.result.verification.modules) && detail.result.verification.modules.length>0 && <p>검증 대상 · {detail.result.verification.modules.filter(item=>typeof item==="string").join(", ") || "확인 불가"}</p>}{detail.result.partial && <p>작업 결과가 부분 완료로 기록됐습니다. 최종 응답과 검증 결과를 함께 확인하세요.</p>}</section>}
    <details><summary>작업 로그</summary><pre tabIndex={0} aria-label="작업 로그 내용">{typeof detail.log==="string" ? detail.log || "기록된 로그가 없습니다." : detail.log == null ? "기록된 로그가 없습니다." : "작업 로그 형식을 확인할 수 없습니다."}</pre></details>
  </>;
}

export default function OperationsJobs({session,linkedJob,linkedStatus,detailOnly=false}){
  const storageKey="hermes-operations-search-"+(session || "");
  const [query,setQuery]=useState(()=>sessionStorage.getItem(storageKey) || "");
  const [status,setStatus]=useState(()=>sessionStorage.getItem(storageKey+"-status") || "전체");
  useEffect(()=>{sessionStorage.setItem(storageKey,query);sessionStorage.setItem(storageKey+"-status",status);},[storageKey,query,status]);
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [resultQuery,setResultQuery]=useState("");
  const [listError,setListError]=useState("");
  const listRequest=useRef(null),gpuRequest=useRef(null),priorityRequest=useRef(null),priorityPending=useRef(false),detailRequest=useRef(null),diffRequest=useRef(null);
  useEffect(()=>()=>{listRequest.current?.abort();gpuRequest.current?.abort();priorityRequest.current?.abort();detailRequest.current?.abort();diffRequest.current?.abort();},[]);
  const resultHeadingRef=useRef(null),resultFocus=useRef(null);
  useEffect(()=>{if(busy || !resultFocus.current)return;const pending=resultFocus.current;resultFocus.current=null;restoreLostFocus(document,pending.success ? resultHeadingRef.current : pending.trigger);},[busy,result,listError]);
  const [gpu,setGpu]=useState(null),[gpuError,setGpuError]=useState(""),[gpuCheckedAt,setGpuCheckedAt]=useState(null),[gpuStale,setGpuStale]=useState(false);
  const [priority,setPriority]=useState(null);
  const [receiptId,setReceiptId]=useState(""),[receiptNotice,setReceiptNotice]=useState("");
  const priorityFocus=useRef(null),prioritySection=useRef(null),priorityError=useRef(null),receiptResult=useRef(null),priorityOrigin=useRef(null),recoveryOrigin=useRef(null),cancelFocus=useRef(null),gpuReload=useRef(null);
  useEffect(()=>{if(busy || !priorityFocus.current)return;const target=priorityFocus.current;priorityFocus.current=null;restoreLostFocus(document,(target==="receipt" ? receiptResult : target==="review" && !priority ? priorityError : prioritySection).current);},[busy,priority,receiptNotice,gpuError]);
  function cancelOperation(event,origin,clear){if(document.activeElement===event.currentTarget)cancelFocus.current=origin.current || gpuReload.current;clear(null);}
  async function readReceipt(event){
    if(priorityPending.current)return;priorityPending.current=true;
    priorityFocus.current=document.activeElement===event?.currentTarget ? "receipt" : null;
    const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setReceiptNotice("");
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-"+(receiptId.trim().startsWith("recovery_")?"recovery":"priority")+"-receipt/"+encodeURIComponent(receiptId.trim()),{cache:"no-store",signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error("접수 기록을 조회할 수 없습니다.");
      const data=await untilAborted(response.json(),controller.signal);
      if(typeof data?.notice!=="string" || !data.notice.trim())throw new Error("접수 기록 응답을 확인할 수 없습니다.");
      setReceiptNotice(data.notice);
    }catch(problem){if(!controller.signal.aborted || timedOut)setReceiptNotice(timedOut ? "접수 기록 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  async function reviewPriority(service,id,event){
    if(priorityPending.current)return;priorityPending.current=true;
    priorityOrigin.current=event?.currentTarget || null;
    priorityFocus.current=document.activeElement===event?.currentTarget ? "review" : null;
    const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setPriority(null);setGpuError("");
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-priority-review",{method:"POST",signal:controller.signal,
        headers:{"Content-Type":"application/json"},body:JSON.stringify({service,id})}),controller.signal);
      if(!response.ok)throw new Error("대기 작업을 다시 조회하세요.");
      const review=await untilAborted(response.json(),controller.signal);
      if(typeof review?.notice!=="string" || typeof review?.identifier!=="string")throw new Error("우선 실행 검토 응답을 확인할 수 없습니다.");
      if(review.request && (review.request.service!==service || review.request.id!==id || review.request.request_id!==review.identifier || !/^priority_[a-f0-9]{64}$/.test(review.identifier) || !/^[a-f0-9]{64}$/.test(review.request.ticket_revision)))throw new Error("우선 실행 검토 대상을 확인할 수 없습니다.");
      setPriority(review);setReceiptId(review.identifier || "");setReceiptNotice("");
    }catch(problem){if(!controller.signal.aborted || timedOut)setGpuError(timedOut ? "우선 실행 검토 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  async function prioritize(event){
    const request=priority?.request;
    if(!request || busy || priorityPending.current)return;
    priorityFocus.current=document.activeElement===event?.currentTarget ? "submit" : null;
    priorityPending.current=true;const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setPriority({...priority,request:null});
    try{
      const receipt=await untilAborted(managementCommand("hermes-agent","hermes-priority-submit",request,{signal:controller.signal}),controller.signal);
      if(receipt.state!=="completed" || receipt.request_id!==request.request_id || receipt.job_id!==request.id ||
         receipt.service!==request.service || receipt.ticket_revision!==request.ticket_revision)throw new Error();
      setPriority({notice:"우선순위 변경이 접수되었습니다. 대기열을 다시 조회하세요.",identifier:request.request_id});
    }catch{
      if(!controller.signal.aborted || timedOut)setPriority({notice:"접수 결과를 확인할 수 없습니다. 재접수하지 말고 접수 ID로 조회하세요.",identifier:request.request_id});
    }finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  const [inspection,setInspection]=useState("");
  const [recovery,setRecovery]=useState(null),[outsideChecked,setOutsideChecked]=useState(false);
  useEffect(()=>{if(busy || !cancelFocus.current)return;const origin=cancelFocus.current;cancelFocus.current=null;restoreLostFocus(document,origin.isConnected && !origin.disabled ? origin : gpuReload.current);},[busy,priority,recovery]);
  const [capture,setCapture]=useState("");
  const auxFocus=useRef(null),inspectionResult=useRef(null),captureResult=useRef(null),recoveryResult=useRef(null);
  useEffect(()=>{if(busy || !auxFocus.current)return;const target=auxFocus.current;auxFocus.current=null;restoreLostFocus(document,(target==="capture" ? captureResult : target==="recovery" && recovery ? recoveryResult : inspectionResult).current);},[busy,inspection,capture,recovery]);
  function rememberAuxFocus(event,target){auxFocus.current=event?.currentTarget===document.activeElement ? target : null;}
  async function reviewRecovery(target,event){
    if(priorityPending.current)return;priorityPending.current=true;
    recoveryOrigin.current=event?.currentTarget || null;
    rememberAuxFocus(event,"recovery");
    const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setRecovery(null);setOutsideChecked(false);setInspection("");setReceiptNotice("");
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-recovery-review",{method:"POST",signal:controller.signal,
        headers:{"Content-Type":"application/json"},body:JSON.stringify(target)}),controller.signal);
      if(!response.ok)throw new Error("예약 정리 대상을 확인할 수 없습니다.");
      const review=await untilAborted(response.json(),controller.signal);
      if(typeof review?.notice!=="string" || typeof review?.identifier!=="string")throw new Error("예약 정리 검토 응답을 확인할 수 없습니다.");
      if(review.request && (review.request.service!==target.service || review.request.job_id!==target.job_id || review.request.request_id!==review.identifier || !/^recovery_[a-f0-9]{64}$/.test(review.identifier) || !/^[a-f0-9]{64}$/.test(review.request.review_sha256)))throw new Error("예약 정리 검토 대상을 확인할 수 없습니다.");
      setRecovery(review);setReceiptId(review.identifier || "");
    }catch(problem){if(!controller.signal.aborted || timedOut)setInspection(timedOut ? "예약 정리 검토 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  async function recover(event){
    const request=recovery?.request;
    if(busy || !outsideChecked || !request || priorityPending.current)return;
    rememberAuxFocus(event,"inspection");
    priorityPending.current=true;const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setRecovery(null);setOutsideChecked(false);
    try{
      const receipt=await untilAborted(managementCommand("hermes-agent","hermes-generator-reservation-recover",{...request,outside_processes_checked:true},{signal:controller.signal}),controller.signal);
      if(receipt.state!=="completed" || receipt.request_id!==request.request_id || receipt.service!==request.service ||
         receipt.job_id!==request.job_id)throw new Error();
      setInspection("정리 완료 · "+request.service+" · "+request.job_id);
    }catch{if(!controller.signal.aborted || timedOut)setInspection("정리 결과를 확인할 수 없습니다. 재실행하지 말고 접수 ID로 조회하세요.");}
    finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut){setBusy(false);setReceiptId(request.request_id);}}}
  }
  async function inspectReservation(target,event){
    if(priorityPending.current)return;
    rememberAuxFocus(event,"inspection");
    setRecovery(null);setOutsideChecked(false);
    await inspectStatus("operations-reservation-inspect",target,setInspection,"예약 신원");
  }
  async function inspectCapture(row,event){
    if(priorityPending.current)return;
    rememberAuxFocus(event,"capture");
    await inspectStatus("operations-capture-status",{row},setCapture,"캡처 접수 상태");
  }
  async function inspectStatus(endpoint,payload,setNotice,label){
    if(priorityPending.current)return;priorityPending.current=true;
    const controller=new AbortController();priorityRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice("");
    try{
      const response=await untilAborted(fetch("/management/assistant/"+endpoint,{method:"POST",signal:controller.signal,
        headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),controller.signal);
      if(!response.ok)throw new Error(label+" 조회에 실패했습니다.");
      const data=await untilAborted(response.json(),controller.signal);
      if(typeof data?.notice!=="string" || !data.notice.trim())throw new Error(label+" 응답을 확인할 수 없습니다.");
      setNotice(data.notice);
    }catch(problem){if(!controller.signal.aborted || timedOut)setNotice(timedOut ? label+" 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timer);if(priorityRequest.current===controller){priorityRequest.current=null;priorityPending.current=false;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  function gpuTable(table){
    if(table.inspection_targets)return {...table,columns:[...table.columns,"예약 조회"],rows:table.rows.map((row,index)=>{
      const target=table.inspection_targets[index];
      return [...row,target ? <><button disabled={gpuStale} onClick={event=>inspectReservation(target,event)}>예약 신원 확인</button><button disabled={gpuStale} onClick={event=>reviewRecovery(target,event)}>예약 정리 검토</button></> : "조회 대상 미확인"];
    })};
    if(table.title!=="GPU 대기열")return table;
    return {...table,columns:[...table.columns,"우선순위"],rows:table.rows.map(row=>{
      const source=row[3];
      const cells=[...row];
      if(row[1]==="review-capture" && source==="review-capture" && row[4]!=="미확인"){
        cells[4]=<button disabled={gpuStale} onClick={event=>inspectCapture(row,event)}>{row[4]} · 상태 조회</button>;
      }
      return [...cells,source==="미확인" ? "원 서비스 미확인" :
        <button disabled={gpuStale} onClick={event=>reviewPriority(source,row[2],event)}>우선 실행 검토</button>];
    })};
  }
  async function loadGpu(){
    if(gpuRequest.current)return;
    const controller=new AbortController();gpuRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setCapture("");
    setRecovery(null);setOutsideChecked(false);
    setInspection("");
    setBusy(true);setGpuError("");setPriority(null);
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-gpu",{cache:"no-store",signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error("GPU 관측 기록을 불러올 수 없습니다.");
      const tables=await untilAborted(response.json(),controller.signal);
      if(!validGpuTables(tables))throw new Error("GPU 관측 응답을 확인할 수 없습니다.");
      if(!controller.signal.aborted){setGpu(tables);setGpuCheckedAt(new Date());setGpuStale(false);}
    }catch(problem){if(!controller.signal.aborted || timedOut){setGpuStale(true);setGpuError((timedOut ? "GPU 관측 조회 시간이 초과됐습니다." : requestErrorMessage(problem))+(gpu ? " 이전 관측 결과를 표시합니다. 다시 조회한 뒤 작업을 선택하세요." : timedOut ? " 다시 조회하세요." : ""));}}
    finally{clearTimeout(timer);if(gpuRequest.current===controller){gpuRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  const [detail,setDetail]=useState(null),[detailCheckedAt,setDetailCheckedAt]=useState(null),[detailError,setDetailError]=useState("");
  const detailRef=useRef(null),detailTriggerRef=useRef(null),detailFocus=useRef(null),searchRef=useRef(null);
  useEffect(()=>{if(busy || !detailFocus.current)return;const pending=detailFocus.current;detailFocus.current=null;restoreLostFocus(document,pending.success ? detailRef.current : pending.trigger);},[busy,detail,error,detailError]);
  const [diffPage,setDiffPage]=useState(null),[diffError,setDiffError]=useState("");
  const diffText=useRef(null),diffFocus=useRef(null);
  useEffect(()=>{if(busy || !diffFocus.current)return;const pending=diffFocus.current;diffFocus.current=null;restoreLostFocus(document,pending.success ? diffText.current : pending.trigger);},[busy,diffPage,diffError]);
  async function readDiff(cursor,event){
    if(diffRequest.current || !detail)return;
    diffFocus.current=event?.currentTarget===document.activeElement ? {trigger:event.currentTarget,success:false} : null;
    const controller=new AbortController();diffRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setDiffError("");
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-diff",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,
        body:JSON.stringify({id:detail.id,cursor})}),controller.signal);
      const page=await untilAborted(response.json(),controller.signal);
      const next=page.cursor?.next_offset,size=page.cursor?.size_bytes,offset=cursor?.next_offset ?? 0;
      if(!response.ok || page.cursor?.job_id!==detail.id || typeof page.text!=="string" || typeof page.notice!=="string" || !Number.isSafeInteger(size) || size<offset || (cursor && size!==cursor.size_bytes) || !(next===null || Number.isSafeInteger(next) && next>offset && next<size))throw new Error("변경 내역을 확인할 수 없습니다.");
      if(diffFocus.current)diffFocus.current.success=true;
      setDiffPage(page);
    }catch(problem){if(!controller.signal.aborted || timedOut)setDiffError((timedOut ? "변경 내역 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem))+(diffPage ? " 이전 조회 내용을 표시합니다." : ""));}
    finally{clearTimeout(timer);if(diffRequest.current===controller){diffRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  async function inspectJob(id,event){
    detailRequest.current?.abort();diffRequest.current?.abort();diffFocus.current=null;setDiffError("");
    const controller=new AbortController();detailRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    detailFocus.current=event?.currentTarget===document.activeElement ? {trigger:event.currentTarget,success:false} : null;
    const refreshing=detail?.id===id;
    if(!refreshing){setDiffPage(null);setDetail(null);}
    setBusy(true);setError("");setDetailError("");
    try{
      const record=await untilAborted(managementCommand("hermes-agent","hermes-detail",{id},{signal:controller.signal}),controller.signal);
      if(record.id!==id || typeof record.status?.status!=="string")throw new Error("선택한 작업의 상세를 확인할 수 없습니다.");
      if(detailFocus.current)detailFocus.current.success=true;
      setDetail(record);setDetailCheckedAt(new Date());setDiffPage(null);
    }catch(problem){if(!controller.signal.aborted || timedOut){const message=timedOut ? "작업 상세 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem);if(refreshing)setDetailError(message+" 이전 조회 내용을 표시합니다.");else setError(message);}}
    finally{clearTimeout(timer);if(detailRequest.current===controller){detailRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  useEffect(()=>{
    if(linkedJob && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(linkedJob))inspectJob(linkedJob);
  },[linkedJob]);
  useEffect(()=>{
    if(linkedJob && linkedStatus && detail?.id===linkedJob && detail.status.status!==linkedStatus && !busy)inspectJob(linkedJob);
  },[linkedJob,linkedStatus]);
  async function load(direction,event){
    if(listRequest.current)return;
    if(event?.currentTarget===document.activeElement)resultFocus.current={trigger:event.currentTarget,success:false};
    const controller=new AbortController();listRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");setListError("");
    try{
      const response=await untilAborted(fetch("/management/assistant/operations-jobs",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,
        body:JSON.stringify({query,status,direction,page:result?.page})}),controller.signal);
      if(!response.ok)throw new Error("운영 작업 목록을 불러올 수 없습니다.");
      const data=await untilAborted(response.json(),controller.signal);
      if(!validOperationsPage(data,query,status,direction,result?.page))throw new Error("운영 작업 목록 응답을 확인할 수 없습니다.");
      if(!controller.signal.aborted){if(resultFocus.current)resultFocus.current.success=true;setResult(data);setResultQuery(query.trim());}
    }catch(problem){if(!controller.signal.aborted || timedOut)setListError((timedOut ? "운영 작업 목록 조회 시간이 초과됐습니다. 다시 조회하세요." : requestErrorMessage(problem))+(result ? " 이전 조회 결과를 유지합니다." : ""));}
    finally{clearTimeout(timer);if(listRequest.current===controller){listRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  const page=result?.page;
  const same=page && resultQuery===query.trim() && page.status===status;
  const statusLabels={queued:"대기 중",pending:"대기 중",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",canceled:"취소"};
  const verificationLabels={...statusLabels,not_requested:"요청하지 않음",unknown:"확인 불가"};
  const filterStatuses=result?.statuses || {queued:"대기",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",paused:"일시정지",unknown:"확인 불가"};
  const pagination=position=> <OperationsPagination position={position} canPrevious={!listError && Boolean(same && page.offset)} canNext={!listError && Boolean(same && page.next_offset!=null)} onPage={load}/>;
  const detailSection = detail && <section ref={detailRef} tabIndex={-1} className="operations-job-detail operations-focus" aria-label="운영 작업 상세"><div className="operations-job-heading">{!detailOnly && <h3>작업 상세</h3>}<span className="operations-job-status">{operationStatusLabel(statusLabels,detail.status.status)}</span></div>
      {!detailOnly && <JobIdentifier id={detail.id} compact/>}
      {!detailOnly && <p>선택한 작업 상세는 목록 검색이나 페이지가 바뀌어도 유지됩니다.</p>}
      {detailError && <p role="alert">{detailError}</p>}
      <OperationsDetailData detail={detail} verificationLabels={verificationLabels}/>
      <details><summary>변경 내역</summary>{detail.diff_truncated && <p>변경 내역 일부만 표시했습니다.</p>}<pre ref={diffText} className="operations-focus" tabIndex={0} aria-label="변경 내역 내용">{diffPage?.text ?? (typeof detail.diff==="string" ? detail.diff || "기록된 변경이 없습니다." : detail.diff == null ? "기록된 변경이 없습니다." : "변경 내역 형식을 확인할 수 없습니다.")}</pre>
        {diffError && <p role="alert">{diffError}</p>}
        {detail.diff_truncated && <><button onClick={event=>readDiff(null,event)}>처음 부분부터 조회</button>
          {diffPage && <p>{diffPage.notice}</p>}
          {diffPage?.cursor.next_offset!=null && <button onClick={event=>readDiff(diffPage.cursor,event)}>다음 부분 조회</button>}</>}
      </details>
      {detail.result && <details><summary>결과 기록</summary><pre tabIndex={0} aria-label="결과 기록 내용">{JSON.stringify(detail.result,null,2)}</pre></details>}
      {detailCheckedAt && <p>조회 시각 · {detailCheckedAt.toLocaleString("ko-KR")}</p>}
      <button onClick={event=>inspectJob(detail.id,event)}>상세 새로고침</button>
      {!detailOnly && <button type="button" onClick={()=>{setDetail(null);(detailTriggerRef.current?.isConnected ? detailTriggerRef.current : searchRef.current)?.focus();}}>상세 닫기</button>}
    </section>;
  if(detailOnly)return <div aria-busy={busy}>{busy && <p role="status">작업 이력 조회 중…</p>}{error && <p role="alert">{error} <button type="button" onClick={()=>inspectJob(linkedJob)}>다시 조회</button></p>}{detailSection}</div>;
  return <fieldset className="operations-jobs" disabled={busy}><legend>운영 작업 이력</legend>
    {busy && <p role="status">요청을 처리하고 있습니다.</p>}
    <MapDatabaseReceipt/>
    <BuildingSessionReceipts key={session} session={session}/>
    <label>작업 ID 또는 지시문 <input ref={searchRef} value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter" && !e.nativeEvent.isComposing && !busy){e.preventDefault();load("first",e);}}}/></label>
    <label>작업 상태 <select value={status} onChange={e=>setStatus(e.target.value)}><option>전체</option>
      {status!=="전체" && !Object.hasOwn(filterStatuses,status) && <option value={status}>{status}</option>}
      {Object.entries(filterStatuses).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
    <button onClick={event=>load("first",event)}>작업 조회</button>
    {listError && <p role="alert">{listError}</p>}
    {error && <p role="alert">{error}</p>}
    {!result && !listError && !busy && <p>검색 조건을 입력하거나 전체 상태로 작업 조회를 누르세요.</p>}
    {result && <><section className="operations-job-results" aria-label="운영 작업 목록"><h3 ref={resultHeadingRef} tabIndex={-1} className="operations-focus">운영 작업</h3>
      <OperationsRefreshStatus loading={Boolean(listRequest.current)} hasPrevious={true} label="운영 작업 목록"/>
      {!same && <p className="operations-job-stale" role="status">검색 조건이 변경되었습니다. 아래는 이전 조회 결과입니다. 변경한 조건을 적용하려면 작업 조회를 누르세요.</p>}
      <p>{result.summary}</p>
      {pagination("위")}
      {result.rows.length ? <div className="operations-job-list">{result.rows.map(([id,state,gpuWait,prompt,reservation])=><article className="operations-job-card" key={id}>
        <div className="operations-job-heading"><strong>작업</strong><span className="operations-job-status">{state}</span></div>
        <JobIdentifier id={id} compact/><p className="operations-job-prompt">{prompt || "기록된 지시가 없습니다."}</p>
        <p className="operations-job-meta">GPU 대기 · {gpuWait}　 GPU 예약 · {reservation}</p>
        <button type="button" onClick={e=>{detailTriggerRef.current=e.currentTarget;inspectJob(id,e);}}>상세 보기</button>
      </article>)}</div> : <p>조회된 작업이 없습니다.</p>}</section>
      {pagination("아래")}</>}
    {detailSection}
    <button ref={gpuReload} onClick={loadGpu}>GPU 대기열·예약 조회</button>
    {gpuError && <p ref={priorityError} tabIndex={-1} className="operations-focus" role="alert">{gpuError}</p>}
    {!gpu && !gpuError && !busy && <p>GPU 대기열과 예약은 조회 버튼을 눌러 확인할 수 있습니다.</p>}
    <OperationsRefreshStatus loading={Boolean(gpuRequest.current)} hasPrevious={Boolean(gpu)} label="GPU 관측"/>
    {gpuCheckedAt && <p>GPU 관측 시각 · {gpuCheckedAt.toLocaleString("ko-KR")}{gpuStale && " · 이전 결과"}</p>}
    {gpu?.map(table=>table.available ? <div className="operations-gpu-table" key={table.title}><ResultTable table={gpuTable(table)}/></div> :
      <p role="status" key={table.title}>{table.summary}</p>)}
    {capture && <p ref={captureResult} tabIndex={-1} className="operations-focus" role="status">{capture}</p>}
    {inspection && <p ref={inspectionResult} tabIndex={-1} className="operations-focus" role="status">{inspection}</p>}
    {priority && <section ref={prioritySection} tabIndex={-1} className="operations-focus" aria-label="우선 실행 검토 결과"><p role="status">{priority.notice}</p>{priority.identifier && <JobIdentifier id={priority.identifier} compact/>}
      {priority.request && <><button onClick={event=>cancelOperation(event,priorityOrigin,setPriority)}>취소</button>
        <button onClick={prioritize}>확인 후 우선순위 변경</button></>}</section>}
    {recovery && <section ref={recoveryResult} tabIndex={-1} className="operations-focus" aria-label="예약 정리 검토 결과"><p role="status">{recovery.notice}</p>
      {recovery.request && <><label><input type="checkbox" checked={outsideChecked} onChange={e=>setOutsideChecked(e.target.checked)}/>별도 그룹의 GPU 프로세스를 확인했습니다</label>
        <button onClick={event=>cancelOperation(event,recoveryOrigin,setRecovery)}>취소</button><button disabled={!outsideChecked} onClick={recover}>확인 후 예약 정리</button></>}</section>}
    <label>우선순위 변경·예약 정리 접수 ID <input value={receiptId} aria-describedby="operations-receipt-hint" placeholder="priority_… 또는 recovery_…" onChange={e=>{setReceiptId(e.target.value);setReceiptNotice("");}}/></label>
    <p id="operations-receipt-hint">접수 시 표시된 ID 전체를 입력하세요. priority_ 또는 recovery_ 뒤에 숫자와 a–f로 된 64자리가 이어집니다.</p>
    <button disabled={!/^(priority|recovery)_[a-f0-9]{64}$/.test(receiptId.trim())} onClick={readReceipt}>접수 결과 조회</button>
    {receiptNotice && <p ref={receiptResult} tabIndex={-1} className="operations-focus" role="status">{receiptNotice}</p>}
  </fieldset>;
}
