import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import {validExpressionCatalogPage,firstExpressionPage,expressionCursorForQuery,resetExpressionQuery} from "./expressionCatalogPage.mjs";

export default function ExpressionCatalog({query,choose}) {
  const pageReasonId=useId();
  const [pagination,setPagination]=useState({query,cursor:firstExpressionPage});
  const cursor=expressionCursorForQuery(pagination,query);
  const [page,setPage]=useState(null);
  const [pageQuery,setPageQuery]=useState(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const currentQuery=useRef(query),requestRevision=useRef(0),navigationPending=useRef(true);currentQuery.current=query;
  const listRef=useRef(null),errorRef=useRef(null),pageOrigin=useRef(null),focusPage=useRef(false);
  useEffect(()=>{focusPage.current=false;setPagination(current=>resetExpressionQuery(current,query));},[query]);
  useEffect(()=>{if(page && focusPage.current){focusPage.current=false;if(document.activeElement===document.body || document.activeElement===pageOrigin.current){listRef.current?.focus({preventScroll:true});listRef.current?.scrollIntoView({block:"start",inline:"nearest"});}}},[page]);
  useEffect(()=>{if(!loading && error && focusPage.current){focusPage.current=false;if(document.activeElement===document.body || document.activeElement===pageOrigin.current)errorRef.current?.focus();}},[loading,error]);
  useEffect(()=>{
    let active=true,deadline,timedOut=false;
    const revision=requestRevision.current;
    const controller=new AbortController();
    navigationPending.current=true;setLoading(true);
    setError("");
    const timer=setTimeout(async ()=>{
      deadline=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const result=await untilAborted(managementCommand("hermes-agent","hermes-expression-catalog",{query,limit:20,...cursor},{signal:controller.signal}),controller.signal);
        if(!validExpressionCatalogPage(result,cursor))throw new Error("표정 목록을 확인할 수 없습니다.");
        if(active && currentQuery.current===query && requestRevision.current===revision){setPage(result);setPageQuery(query);setReceivedAt(new Date());}
      } catch(problem) {
        if(active && currentQuery.current===query && requestRevision.current===revision)setError(timedOut ? "표정 목록 조회 시간이 초과됐습니다." : requestErrorMessage(problem));
      } finally {clearTimeout(deadline);if(active && currentQuery.current===query && requestRevision.current===revision){navigationPending.current=false;setLoading(false);}}
    },200);
    return ()=>{active=false;clearTimeout(timer);clearTimeout(deadline);controller.abort();};
  },[query,cursor]);
  function navigate(event,next){
    if(navigationPending.current)return;
    navigationPending.current=true;requestRevision.current++;setLoading(true);
    pageOrigin.current=event.currentTarget;focusPage.current=document.activeElement===event.currentTarget;
    setPagination({query,cursor:next});
  }
  return <section className="expression-catalog" aria-label="표정 프리셋 검색">
    {error && <><p ref={errorRef} tabIndex={-1} role="alert">{error}{page && (page.records.length ? " 이전 조회 결과를 유지합니다." : " 이전 조회에서 표시할 표정이 없었습니다.")}</p><button type="button" onClick={event=>navigate(event,{})}>처음부터 다시 조회</button></>}
    {loading && page && <p role="status">새 목록 조회 중 · {page.records.length ? "아래는 이전 결과입니다." : "이전 조회에서 표시할 표정이 없었습니다."}</p>}
    {!error && !page && <p role="status">표정 조회 중…</p>}
    {page && <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>
      {pageQuery!==query && !loading && <p role="status">검색 조건이 변경되었습니다. {page.records.length ? "아래는 이전 검색 결과입니다." : "이전 검색에서 표시할 표정이 없었습니다."}</p>}

      <div ref={listRef} tabIndex={-1} aria-label="등록 표정 결과">{page.records.length===0 ? <><h3>등록 표정</h3><p role="status">{loading || error || pageQuery!==query ? "이전 조회에서 표시할 표정이 없었습니다." : "검색 조건에 맞는 표정이 없습니다."}</p></> : <ResultTable table={{title:"등록 표정",summary:"전체 "+page.total+"개 · "+(page.offset+1)+"–"+(page.offset+page.records.length)+"번째",columns:["표정","ID와 동작"],
        rows:page.records.map(row=>[row.label,<div className="expression-catalog-action"><code>{row.id}</code><button type="button" aria-label={row.label+" 표정을 대화 입력에 추가"} onClick={()=>choose("표정 "+row.label,row.id)}>입력에 추가</button></div>])}}/>}</div>
      {(page.offset>0 || page.next_offset!=null) && <nav className="expression-catalog-pagination" aria-label="표정 목록 페이지">
      {(loading || error || pageQuery!==query) && <p id={pageReasonId}>{loading ? "목록 조회가 끝나면 페이지를 이동할 수 있습니다." : error ? "목록을 다시 조회한 뒤 페이지를 이동하세요." : "변경된 검색 결과를 확인한 뒤 페이지를 이동하세요."}</p>}
      {page.offset>0 && <button type="button" disabled={loading || !!error || pageQuery!==query} aria-describedby={loading || error || pageQuery!==query ? pageReasonId : undefined} onClick={event=>navigate(event,{offset:Math.max(0,page.offset-20),snapshot:page.snapshot})}>이전 표정</button>}
      {page.next_offset!=null && <button type="button" disabled={loading || !!error || pageQuery!==query} aria-describedby={loading || error || pageQuery!==query ? pageReasonId : undefined} onClick={event=>navigate(event,{offset:page.next_offset,snapshot:page.snapshot})}>다음 표정</button>}</nav>}
    </>}
  </section>;
}
