import React, {useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import {latestRequest} from "./latestRequest.mjs";
import {anchorHistoryRequest,validAnchorHistoryPage} from "./anchorHistoryPage.mjs";

export default function AnchorHistory() {
  const [animation,setAnimation]=useState("");
  const [version,setVersion]=useState("");
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [receivedAt,setReceivedAt]=useState(null);
  const resultRef=useRef(null),focusPage=useRef(false);
  useEffect(()=>{if(page && focusPage.current){focusPage.current=false;resultRef.current?.focus({preventScroll:true});resultRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[page]);
  const request=useRef(null);
  if(!request.current)request.current=latestRequest();

  async function load(next,offset=null) {
    const token=request.current.start();
    const payload=anchorHistoryRequest(animation,version,next ? {...page,next_offset:offset ?? page.next_offset} : null);
    setBusy(true);
    setError("");
    try {
      const result=await managementCommand("hermes-agent","hermes-anchor-history-observe",payload);
      if(!request.current.isCurrent(token))return;
      if(!validAnchorHistoryPage(result,payload,next)) {
        throw new Error("이력이 변경되었거나 페이지 정보를 확인할 수 없습니다. 다시 조회하세요.");
      }
      focusPage.current=next;setPage(result);setReceivedAt(new Date());
    } catch(problem) {
      if(request.current.isCurrent(token)){focusPage.current=false;setError((problem instanceof TypeError?"앵커 이력에 연결하지 못했습니다. 다시 조회하세요.":problem.message)+(page?" 이전 조회 결과를 유지합니다.":""));}
    } finally {
      if(request.current.isCurrent(token))setBusy(false);
    }
  }
  function edit(setter,value) {
    request.current.invalidate();
    setBusy(false);
    setter(value);
    setPage(null);
    setError("");
  }
  function pagination(position){return page && <nav className="anchor-history-pagination" aria-label={"앵커 이력 페이지 "+position}>
    <button type="button" disabled={!!error || page.offset<=0} onClick={()=>load(true,Math.max(0,page.offset-20))}>이전 이력</button>
    <span>{page.total ? `${page.offset+1}–${page.offset+page.records.length} / ${page.total}건` : "0건"}</span>
    <button type="button" disabled={!!error || page.next_offset==null} onClick={()=>load(true)}>다음 이력</button>
  </nav>;}
  return <fieldset disabled={busy}><legend>과거 앵커 검수 이력</legend>
    <form className="anchor-history-search" onSubmit={event=>{event.preventDefault();load(false);}}>
      <label>애니메이션 ID<input required value={animation} onChange={e=>edit(setAnimation,e.target.value)}/></label>
      <label>애니메이션 버전<input required value={version} onChange={e=>edit(setVersion,e.target.value)}/></label>
      <button disabled={!animation.trim() || !version.trim()}>이력 조회</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">앵커 이력을 조회하고 있습니다.</p>}
    {page && <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>}
    {pagination("상단")}
    {page && <div ref={resultRef} tabIndex={-1} aria-label="앵커 검수 이력 결과"><ResultTable table={{title:"과거 좌표 검수 기록",summary:"전체 "+page.total+"건",
      columns:["이력 ID","저장 시각","프레임 수"],rows:page.records.map(row=>[row.id,row.created_at,row.frames])}}/></div>}
    {page?.note && <p>{page.note}</p>}
    {page?.records.length>5 && pagination("하단")}
  </fieldset>;
}
