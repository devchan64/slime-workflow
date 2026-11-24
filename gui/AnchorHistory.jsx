import React, {useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import {latestRequest} from "./latestRequest.mjs";
import {anchorHistoryRequest,validAnchorHistoryPage} from "./anchorHistoryPage.mjs";

export default function AnchorHistory() {
  const [animation,setAnimation]=useState("");
  const [version,setVersion]=useState("");
  const [page,setPage]=useState(null);
  const [pageFilters,setPageFilters]=useState(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [receivedAt,setReceivedAt]=useState(null);
  const resultRef=useRef(null),focusPage=useRef(null),searchButton=useRef(null),focusSearch=useRef(false);
  useEffect(()=>{if(page && focusPage.current){const trigger=focusPage.current;focusPage.current=null;if(document.activeElement===trigger || document.activeElement===document.body){resultRef.current?.focus({preventScroll:true});resultRef.current?.scrollIntoView({block:"start",inline:"nearest"});}}},[page]);
  useEffect(()=>{if(!busy && focusSearch.current){focusSearch.current=false;if(document.activeElement===document.body && searchButton.current && !searchButton.current.disabled)searchButton.current.focus({preventScroll:true});}},[busy,page,error]);
  const request=useRef(null);
  const activeRequest=useRef(null);
  if(!request.current)request.current=latestRequest();
  useEffect(()=>()=>{request.current.invalidate();activeRequest.current?.abort();},[]);
  const filtersChanged=Boolean(pageFilters && (animation.trim()!==pageFilters.animation || version.trim()!==pageFilters.version));

  async function load(next,offset=null,event) {
    if(next && filtersChanged)return;
    const focusTrigger=next && event?.currentTarget===document.activeElement ? event.currentTarget : null;
    const token=request.current.start();
    const payload=anchorHistoryRequest(animation,version,next ? {...page,next_offset:offset ?? page.next_offset} : null);
    activeRequest.current?.abort();
    const controller=new AbortController();activeRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);
    setError("");
    try {
      const result=await untilAborted(managementCommand("hermes-agent","hermes-anchor-history-observe",payload,{signal:controller.signal}),controller.signal);
      if(!request.current.isCurrent(token))return;
      if(!validAnchorHistoryPage(result,payload,next)) {
        throw new Error("이력이 변경되었거나 페이지 정보를 확인할 수 없습니다. 다시 조회하세요.");
      }
      focusPage.current=focusTrigger;setPage(result);setPageFilters({animation:payload.animation_id,version:payload.animation_version});setReceivedAt(new Date());
    } catch(problem) {
      if(request.current.isCurrent(token)){focusPage.current=null;setError((timedOut?"앵커 이력 조회 시간이 초과됐습니다. 다시 조회하세요.":problem instanceof TypeError?"앵커 이력에 연결하지 못했습니다. 다시 조회하세요.":problem.message)+(page?" 이전 조회 결과를 유지합니다.":""));}
    } finally {
      clearTimeout(timer);if(activeRequest.current===controller)activeRequest.current=null;
      if(request.current.isCurrent(token))setBusy(false);
    }
  }
  function edit(setter,value) {
    request.current.invalidate();
    activeRequest.current?.abort();
    focusPage.current=null;
    focusSearch.current=false;
    setBusy(false);
    setter(value);
    setError("");
  }
  function pagination(position){return page && <nav className="anchor-history-pagination" aria-label={"앵커 이력 페이지 "+position}>
    <button type="button" disabled={busy || !!error || filtersChanged || page.offset<=0} onClick={event=>load(true,Math.max(0,page.offset-20),event)}>이전 이력</button>
    <span>{page.total ? `${page.offset+1}–${page.offset+page.records.length} / ${page.total}건` : "0건"}</span>
    <button type="button" disabled={busy || !!error || filtersChanged || page.next_offset==null} onClick={event=>load(true,null,event)}>다음 이력</button>
  </nav>;}
  return <fieldset><legend>과거 앵커 검수 이력</legend>
    <form className="anchor-history-search" onSubmit={event=>{event.preventDefault();focusSearch.current=document.activeElement===searchButton.current;load(false);}}>
      <label>애니메이션 ID<input required value={animation} onChange={e=>edit(setAnimation,e.target.value)}/></label>
      <label>애니메이션 버전<input required value={version} onChange={e=>edit(setVersion,e.target.value)}/></label>
      <button ref={searchButton} disabled={busy || !animation.trim() || !version.trim()}>이력 조회</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">앵커 이력을 조회하고 있습니다.{page && " 아래는 마지막 조회 결과입니다."}</p>}
    {page && filtersChanged && <p role="status">검색 조건이 변경되었습니다. 아래는 이전 조건의 결과입니다. 이력 조회를 눌러 새 조건을 적용하세요.</p>}
    {!page && !busy && !error && <p>애니메이션 ID와 버전을 입력한 뒤 이력을 조회하세요.</p>}
    {page && <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>}
    {pagination("상단")}
    {page && <div ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="앵커 검수 이력 결과"><div className="anchor-history-table"><ResultTable table={{title:"과거 좌표 검수 기록",summary:"전체 "+page.total+"건",
      columns:["이력 ID","저장 시각","프레임 수"],rows:page.records.map(row=>[row.id,row.created_at,row.frames])}}/></div></div>}
    {page?.note && <p>{page.note}</p>}
    {page?.records.length>5 && pagination("하단")}
  </fieldset>;
}
