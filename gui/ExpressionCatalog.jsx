import React, {useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";

export default function ExpressionCatalog({query,choose}) {
  const [cursor,setCursor]=useState({});
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const listRef=useRef(null),focusPage=useRef(false);
  useEffect(()=>{if(page && focusPage.current){focusPage.current=false;listRef.current?.focus({preventScroll:true});listRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[page]);
  useEffect(()=>{
    let active=true,deadline,timedOut=false;
    const controller=new AbortController();
    setLoading(true);
    setError("");
    const timer=setTimeout(async ()=>{
      deadline=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const result=await untilAborted(managementCommand("hermes-agent","hermes-expression-catalog",{query,limit:20,...cursor},{signal:controller.signal}),controller.signal);
        if(!result || !Array.isArray(result.records) || !Number.isInteger(result.total) || result.records.some(row=>!row || typeof row.id!=="string" || typeof row.label!=="string"))throw new Error("표정 목록을 확인할 수 없습니다.");
        if(active){setPage(result);setReceivedAt(new Date());}
      } catch(problem) {
        if(active){focusPage.current=false;setError(timedOut ? "표정 목록 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}
      } finally {clearTimeout(deadline);if(active)setLoading(false);}
    },200);
    return ()=>{active=false;clearTimeout(timer);clearTimeout(deadline);controller.abort();};
  },[query,cursor]);
  return <section aria-label="표정 프리셋 검색">
    {error && <p role="alert">{error}{page && " 이전 조회 결과를 유지합니다."} <button type="button" onClick={()=>setCursor({})}>처음부터 다시 조회</button></p>}
    {loading && page && <p role="status">새 목록 조회 중 · 아래는 이전 결과입니다.</p>}
    {!error && !page && <p role="status">표정 조회 중…</p>}
    {page && <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>

      <div ref={listRef} tabIndex={-1} aria-label="등록 표정 결과">{page.records.length===0 ? <><h3>등록 표정</h3><p role="status">검색 조건에 맞는 표정이 없습니다.</p></> : <ResultTable table={{title:"등록 표정",summary:"전체 "+page.total+"개",columns:["표정","ID와 동작"],
        rows:page.records.map(row=>[row.label,<div className="expression-catalog-action"><code>{row.id}</code><button type="button" aria-label={row.label+" 표정을 대화 입력에 추가"} onClick={()=>choose("표정 "+row.label,row.id)}>입력에 추가</button></div>])}}/>}</div>
      {page.offset>0 && <button disabled={loading || !!error} onClick={()=>{focusPage.current=true;setCursor({offset:Math.max(0,page.offset-20),snapshot:page.snapshot});}}>이전 표정</button>}
      {page.next_offset!=null && <button disabled={loading || !!error} onClick={()=>{focusPage.current=true;setCursor({offset:page.next_offset,snapshot:page.snapshot});}}>다음 표정</button>}
    </>}
  </section>;
}
