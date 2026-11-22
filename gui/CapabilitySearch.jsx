import React, {useEffect, useRef, useState} from "react";

export default function CapabilitySearch({search, choose}) {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");
  const [loading,setLoading] = useState(true), [receivedAt,setReceivedAt] = useState(null);
  const [revision, refresh] = useState(0);
  const [pagination,setPagination] = useState({query:"",page:0});
  const headingRef=useRef(null),focusPage=useRef(false),refreshRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  useEffect(() => {
    const controller = new AbortController();
    let active=true,timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function load() {
      setLoading(true);setError("");
      try {
        const response = await fetch("/management/assistant/capabilities", {signal:controller.signal});
        if (!response.ok) throw new Error("관리 기능을 조회할 수 없습니다.");
        const record = await response.json();
        if (!record || typeof record.summary!=="string" || !Array.isArray(record.rows) || record.rows.some(row=>!Array.isArray(row) || row.length<8 || row.some(value=>typeof value!=="string"))) throw new Error("관리 기능 목록 형식을 확인할 수 없습니다.");
        if (!controller.signal.aborted) {setCatalog(record);setReceivedAt(new Date());}
      } catch (problem) {
        if (active && (timedOut || !controller.signal.aborted)) setError(timedOut ? "관리 기능 조회 시간이 초과됐습니다. 다시 시도하세요." : problem instanceof TypeError ? "관리 기능에 연결하지 못했습니다. 다시 시도하세요." : problem.message);
      } finally {clearTimeout(timer);if (active) setLoading(false);}
    }
    load();
    return () => {active=false;clearTimeout(timer);controller.abort();};
  }, [revision]);
  const query = search.trim().toLowerCase();
  const rows = catalog?.rows.filter(row => row.join(" ").toLowerCase().includes(query)) || [];
  useEffect(()=>{setPagination({query,page:0});},[query]);
  const currentPage=pagination.query===query?pagination.page:0;
  const pageCount=Math.max(1,Math.ceil(rows.length/20));
  const safePage=Math.min(currentPage,pageCount-1);
  const visibleRows=rows.slice(safePage*20,(safePage+1)*20);
  useEffect(()=>{if(focusPage.current){focusPage.current=false;headingRef.current?.focus({preventScroll:true});headingRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[safePage]);
  function changePage(next){focusPage.current=true;setPagination({query,page:next});}
  return <section aria-label="관리 기능 검색 결과">
    <button ref={refreshRef} disabled={loading} onClick={() => {restoreFocus.current=true;setLoading(true);refresh(value => value + 1);}}>{loading?"조회 중…":"관리 기능 새로고침"}</button>
    {error && <p role="alert">{error}{catalog && " · 이전 조회 결과를 유지합니다."}</p>}
    {loading && catalog && <p role="status">관리 기능을 다시 조회하고 있습니다.</p>}
    {catalog ? <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>
      <h3 ref={headingRef} tabIndex={-1}>관리 기능</h3><p>{rows.length}개 검색됨 · {catalog.summary}</p>
      {rows.length>0 && <p>{safePage+1} / {pageCount} 페이지 · {visibleRows.length}개 표시</p>}
      {rows.length===0 && <p role="status">검색 조건에 맞는 관리 기능이 없습니다. 검색어를 바꾸거나 지워 주세요.</p>}
      <ul className="service-registry-list">{visibleRows.map(([label,command,...fields]) => <li key={command}>
        <button type="button" onClick={() => choose(label,command)}>{label}</button>
        <details><summary>{command}</summary><dl>
          {["연결","입력","영향","GPU","재시도","확인 사항"].map((name,index) =>
            <React.Fragment key={name}><dt>{name}</dt><dd>{fields[index]}</dd></React.Fragment>
          )}
        </dl></details>
      </li>)}</ul>
      {safePage>0 && <button type="button" onClick={()=>changePage(safePage-1)}>이전 기능</button>}
      {safePage+1<pageCount && <button type="button" onClick={()=>changePage(safePage+1)}>다음 기능</button>}
    </> : !error && <p role="status">관리 기능 조회 중…</p>}
  </section>;
}
