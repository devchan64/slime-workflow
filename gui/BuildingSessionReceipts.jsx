import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {readBuildingSessionReceipts} from "./buildingProposalProtocol.mjs";
import ResultTable from "./ResultTable.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export function BuildingReceiptEmptyState({session,page,busy,error,rowCount}){
  if(!session || busy || error)return null;
  if(!page)return <p>현재 대화 접수 조회를 눌러 에셋 변경 기록을 확인하세요.</p>;
  if(rowCount===0)return <p>현재 조회한 대화 페이지에는 에셋 변경 접수가 없습니다.{(page.offset>0 || page.next_offset!=null) && " 다른 대화 페이지도 확인할 수 있습니다."}</p>;
  return null;
}

export default function BuildingSessionReceipts({session}){
  return <BuildingSessionReceiptsForSession key={session || ""} session={session}/>;
}

function BuildingSessionReceiptsForSession({session}){
  const [page,setPage]=useState(null),[rows,setRows]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null),[stale,setStale]=useState(false);
  const request=useRef(null),heading=useRef(null),refresh=useRef(null),focus=useRef(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  useEffect(()=>{if(busy || !focus.current)return;const pending=focus.current;focus.current=null;restoreLostFocus(document,pending.success ? heading.current : refresh.current);},[busy,page,error]);
  async function load(offset=0,snapshot,event){
    if(request.current)return;
    focus.current=event?.currentTarget===document.activeElement ? {success:false} : null;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const command=(service,name,payload)=>{if(controller.signal.aborted)return Promise.reject(new DOMException("조회가 중단됐습니다.","AbortError"));return untilAborted(managementCommand(service,name,payload,{signal:controller.signal}),controller.signal);};
      const result=await untilAborted(readBuildingSessionReceipts(command,session,offset,snapshot),controller.signal);
      if(focus.current)focus.current.success=true;
      setRows(result.rows);setPage(result.page);setCheckedAt(new Date());setStale(false);
    }catch(problem){if(!controller.signal.aborted || timedOut){setStale(true);setError((timedOut ? "대화 접수 이력 조회 시간이 초과됐습니다." : problem.message || "대화 접수 이력을 확인할 수 없습니다.")+(page ? " 이전 조회 결과를 표시합니다. 다시 조회하세요." : ""));}}
    finally{clearTimeout(timeout);if(request.current===controller)request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  return <section aria-label="대화 에셋 변경 접수"><h3 ref={heading} tabIndex={-1} className="operations-focus">대화 에셋 변경 접수</h3>
    {!session ? <p>대화를 선택하면 접수 기록을 확인할 수 있습니다.</p> : <button ref={refresh} type="button" disabled={busy} onClick={event=>load(0,undefined,event)}>현재 대화 접수 조회</button>}
    {busy && <p role="status">대화 접수 이력을 조회하고 있습니다.{page && " 아래는 마지막 조회 결과입니다."}</p>}
    {error && <p role="alert">{error}</p>}
    <BuildingReceiptEmptyState session={session} page={page} busy={busy} error={error} rowCount={rows.length}/>
    {page && <><p>조회 시각 · {checkedAt?.toLocaleString("ko-KR")}{stale && " · 이전 결과"}</p><ResultTable table={{title:"에셋 변경 접수",summary:"현재 대화 페이지의 접수 "+rows.length+"건",columns:["대화 작업 ID","접수 상태","GPU"],rows:rows.map(([id,...cells])=>[id && id!=="확인 불가" ? <JobIdentifier id={id} compact/> : id,...cells])}}/>
      {(page.offset>0 || page.next_offset!=null) && <nav className="ui-action-row" aria-label="대화 에셋 접수 페이지 이동">
      {page.offset>0 && <button type="button" disabled={busy || stale} onClick={event=>load(Math.max(0,page.offset-6),page.snapshot,event)}>최근 대화</button>}
      {page.next_offset!=null && <button type="button" disabled={busy || stale} onClick={event=>load(page.next_offset,page.snapshot,event)}>이전 대화</button>}</nav>}</>}
  </section>;
}
