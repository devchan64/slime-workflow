import React, {useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import {validExpressionCatalogPage} from "./expressionCatalogPage.mjs";

export default function ExpressionCatalog({query,choose}) {
  const [cursor,setCursor]=useState({});
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const listRef=useRef(null),errorRef=useRef(null),pageOrigin=useRef(null),focusPage=useRef(false);
  useEffect(()=>{if(page && focusPage.current){focusPage.current=false;if(document.activeElement===document.body || document.activeElement===pageOrigin.current){listRef.current?.focus({preventScroll:true});listRef.current?.scrollIntoView({block:"start",inline:"nearest"});}}},[page]);
  useEffect(()=>{if(!loading && error && focusPage.current){focusPage.current=false;if(document.activeElement===document.body || document.activeElement===pageOrigin.current)errorRef.current?.focus();}},[loading,error]);
  useEffect(()=>{
    let active=true,deadline,timedOut=false;
    const controller=new AbortController();
    setLoading(true);
    setError("");
    const timer=setTimeout(async ()=>{
      deadline=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const result=await untilAborted(managementCommand("hermes-agent","hermes-expression-catalog",{query,limit:20,...cursor},{signal:controller.signal}),controller.signal);
        if(!validExpressionCatalogPage(result,cursor))throw new Error("표정 목록을 확인할 수 없습니다.");
        if(active){setPage(result);setReceivedAt(new Date());}
      } catch(problem) {
        if(active)setError(timedOut ? "표정 목록 조회 시간이 초과됐습니다." : requestErrorMessage(problem));
      } finally {clearTimeout(deadline);if(active)setLoading(false);}
    },200);
    return ()=>{active=false;clearTimeout(timer);clearTimeout(deadline);controller.abort();};
  },[query,cursor]);
  return <section className="expression-catalog" aria-label="표정 프리셋 검색">
    {error && <p ref={errorRef} tabIndex={-1} role="alert">{error}{page && " 이전 조회 결과를 유지합니다."} <button type="button" onClick={event=>{pageOrigin.current=event.currentTarget;focusPage.current=document.activeElement===event.currentTarget;setCursor({});}}>처음부터 다시 조회</button></p>}
    {loading && page && <p role="status">새 목록 조회 중 · 아래는 이전 결과입니다.</p>}
    {!error && !page && <p role="status">표정 조회 중…</p>}
    {page && <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>

      <div ref={listRef} tabIndex={-1} aria-label="등록 표정 결과">{page.records.length===0 ? <><h3>등록 표정</h3><p role="status">검색 조건에 맞는 표정이 없습니다.</p></> : <ResultTable table={{title:"등록 표정",summary:"전체 "+page.total+"개 · "+(page.offset+1)+"–"+(page.offset+page.records.length)+"번째",columns:["표정","ID와 동작"],
        rows:page.records.map(row=>[row.label,<div className="expression-catalog-action"><code>{row.id}</code><button type="button" aria-label={row.label+" 표정을 대화 입력에 추가"} onClick={()=>choose("표정 "+row.label,row.id)}>입력에 추가</button></div>])}}/>}</div>
      {(page.offset>0 || page.next_offset!=null) && <nav className="expression-catalog-pagination" aria-label="표정 목록 페이지">
      {page.offset>0 && <button type="button" disabled={loading || !!error} onClick={event=>{pageOrigin.current=event.currentTarget;focusPage.current=document.activeElement===event.currentTarget;setCursor({offset:Math.max(0,page.offset-20),snapshot:page.snapshot});}}>이전 표정</button>}
      {page.next_offset!=null && <button type="button" disabled={loading || !!error} onClick={event=>{pageOrigin.current=event.currentTarget;focusPage.current=document.activeElement===event.currentTarget;setCursor({offset:page.next_offset,snapshot:page.snapshot});}}>다음 표정</button>}</nav>}
    </>}
  </section>;
}
