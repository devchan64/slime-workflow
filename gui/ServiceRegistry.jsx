import React, {useEffect, useId, useRef, useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";

function restrictions(items) {
  return items.map(item => item.command+" · "+(item.reason ?? item.note)).join(" / ");
}

export default function ServiceRegistry({query}) {
  const pageReasonId=useId();
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState(null);
  const [pageQuery,setPageQuery]=useState("");
  const [error, setError] = useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const [revision, refresh] = useState(0);
  const listRef=useRef(null),focusNextPage=useRef(false),refreshRef=useRef(null),restoreFocus=useRef(false),firstPageRef=useRef(null),focusFailure=useRef(false),refreshPending=useRef(true);
  useEffect(()=>{focusNextPage.current=false;focusFailure.current=false;setOffset(0);},[query]);
  useEffect(()=>{if(!loading && (restoreFocus.current || focusFailure.current)){const failed=focusFailure.current;restoreFocus.current=false;focusFailure.current=false;if(document.activeElement===document.body)(failed ? firstPageRef.current || refreshRef.current : refreshRef.current)?.focus();}},[loading]);
  useEffect(()=>{if(page && focusNextPage.current){focusNextPage.current=false;if(document.activeElement===document.body){listRef.current?.focus({preventScroll:true});listRef.current?.scrollIntoView({block:"start",inline:"nearest"});}}},[page]);
  useEffect(() => {
    let active = true;
    const controller=new AbortController();
    let timeoutId,timedOut=false;
    refreshPending.current=true;setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      timeoutId=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const result = await untilAborted(managementCommand("hermes-agent","hermes-service-registration",{query,offset,limit:10},{signal:controller.signal}),controller.signal);
        if (!result || (result.note!=null && typeof result.note!=="string") || !Array.isArray(result.services) || !Number.isInteger(result.total) || result.total<0 || result.offset!==offset || result.services.length>10 || offset+result.services.length>result.total ||
            (result.next_offset===null ? offset+result.services.length!==result.total : result.next_offset!==offset+result.services.length || result.next_offset>=result.total || !result.services.length) ||
            result.services.some(row=>!row || typeof row.service!=="string" || ![row.commands,row.hermes_links].every(items=>Array.isArray(items) && items.every(item=>typeof item==="string")) || ![row.gateway_blocked,row.known_service_blocked,row.conditional_limitations].every(items=>Array.isArray(items) && items.every(item=>item && typeof item.command==="string" && typeof (item.reason ?? item.note)==="string")))) throw new Error("서비스 목록 형식을 확인할 수 없습니다.");
        if (active && !controller.signal.aborted) {setPage(result);setPageQuery(query);setReceivedAt(new Date());}
      } catch (problem) {
        if (active) {focusFailure.current=focusNextPage.current;focusNextPage.current=false;setError(timedOut ? "서비스 목록 조회 시간이 초과됐습니다. 다시 시도하세요." : problem instanceof TypeError ? "서비스 목록에 연결하지 못했습니다. 다시 시도하세요." : problem?.message || "서비스 목록을 조회하지 못했습니다. 다시 시도하세요.");}
      } finally {clearTimeout(timeoutId);if(active){refreshPending.current=false;setLoading(false);}}
    }, 200);
    return () => {active = false; clearTimeout(timer);clearTimeout(timeoutId);controller.abort();};
  }, [query,offset,revision]);
  return <section aria-label="서비스 등록 목록">
    <button ref={refreshRef} type="button" disabled={loading} onClick={event => {if(refreshPending.current)return;refreshPending.current=true;restoreFocus.current=document.activeElement===event.currentTarget;setLoading(true);refresh(value => value+1);}}>{loading?"조회 중…":"등록 목록 새로고침"}</button>
    {error && <p role="alert">{error}{page && " · 이전 조회 결과를 유지합니다."}</p>}
    {error && offset>0 && <button ref={firstPageRef} type="button" onClick={event=>{focusNextPage.current=document.activeElement===event.currentTarget;setOffset(0);}}>첫 페이지부터 다시 조회</button>}
    {loading && page && <p role="status">새 목록을 조회 중입니다. 아래는 이전 결과입니다.</p>}
    {page ? <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>
      <h3 ref={listRef} tabIndex={-1}>등록 서비스</h3>
      <p>{pageQuery?.trim() ? <>검색어 · <strong>{pageQuery.trim()}</strong></> : "검색 조건 · 전체 서비스"}</p>
      {query!==pageQuery && <p role="status">검색 조건이 변경되어 아래는 이전 검색 결과입니다.</p>}
      <p>전체 {page.total}개 · {page.services.length}개 표시</p>
      {page.services.length===0 && <p role="status">{pageQuery?.trim() ? "검색 조건에 맞는 서비스가 없습니다. 검색어를 바꾸거나 지워 주세요." : "등록된 서비스가 없습니다."}</p>}
      <ul className="service-registry-list">{page.services.map(record=><li key={record.service}>
        <strong>{record.service}</strong>
        <details><summary>명령과 제한 확인</summary><dl>
          <dt>등록 명령</dt><dd>{record.commands.join(", ") || "기록 없음"}</dd>
          <dt>게이트웨이 명시 차단</dt><dd>{restrictions(record.gateway_blocked) || "기록 없음"}</dd>
          <dt>확인된 서비스 차단</dt><dd>{restrictions(record.known_service_blocked) || "기록 없음"}</dd>
          <dt>조건부 제한</dt><dd>{restrictions(record.conditional_limitations) || "기록 없음"}</dd>
          <dt>헤르메스 연결 기능</dt><dd>{record.hermes_links.join(", ") || "기록 없음"}</dd>
        </dl></details>
      </li>)}</ul>
      <p>{page.note}</p>
      {(offset>0 || page.next_offset!=null) && (loading || error || query!==pageQuery) && <p id={pageReasonId}>{loading ? "목록 조회가 끝나면 페이지를 이동할 수 있습니다." : error ? "목록을 다시 조회한 뒤 페이지를 이동하세요." : "변경된 검색 결과를 확인한 뒤 페이지를 이동하세요."}</p>}
      {offset>0 && <button type="button" disabled={loading || !!error || query!==pageQuery} aria-describedby={loading || error || query!==pageQuery ? pageReasonId : undefined} onClick={event => {focusNextPage.current=document.activeElement===event.currentTarget;setOffset(Math.max(0,offset-10));}}>이전 서비스</button>}
      {page.next_offset!=null && <button type="button" disabled={loading || !!error || query!==pageQuery} aria-describedby={loading || error || query!==pageQuery ? pageReasonId : undefined} onClick={event => {focusNextPage.current=document.activeElement===event.currentTarget;setOffset(page.next_offset);}}>다음 서비스</button>}
    </> : !error && <p role="status">등록 서비스 조회 중…</p>}
  </section>;
}
