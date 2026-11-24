import React, {useEffect,useRef,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import {requestErrorMessage} from "./requestError.mjs";
import {untilAborted} from "./managementCommand.js";
import {validChangelogPage} from "./changelogPage.mjs";

export default function GeneratorChangelog({generator,card=false}) {
  const [open,setOpen]=useState(false);
  const [position,setPosition]=useState({generator,index:0});
  const index=position.generator===generator ? position.index : 0;
  const [revision,setRevision]=useState(0);
  const [page,setPage]=useState(null);
  const [error,setError]=useState(null);
  const [loading,setLoading]=useState(false);
  const refreshRef=useRef(null),focusRequest=useRef(null),requestBusy=useRef(false);
  useEffect(()=>{setPosition({generator,index:0});focusRequest.current=null;},[generator]);
  useEffect(()=>{if(!open)focusRequest.current=null;},[open]);
  useEffect(()=>{
    if(loading || !focusRequest.current)return;
    const target=focusRequest.current;focusRequest.current=null;
    if(document.activeElement===document.body)(target.isConnected && !target.disabled ? target : refreshRef.current)?.focus();
  },[loading]);
  useEffect(()=>{
    if (!open) return;
    const controller=new AbortController();
    let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    requestBusy.current=true;setError(null);setLoading(true);
    async function load() {
      try {
        const result=await untilAborted((async()=>{
          const response=await fetch("/management/assistant/changelog/"+encodeURIComponent(generator)+"?page="+index,
            {cache:"no-store",signal:controller.signal});
          if (!response.ok) throw new Error("변경 기록 조회 실패 · HTTP "+response.status);
          return response.json();
        })(),controller.signal);
        if(!validChangelogPage(result,index))throw new Error("변경 기록 응답을 확인할 수 없습니다.");
        if (!controller.signal.aborted) setPage({...result,generator});
      } catch(problem) {
        if (active) setError({generator,message:timedOut ? "변경 기록 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem)});
      } finally {
        clearTimeout(timeout);if(active){requestBusy.current=false;setLoading(false);}
      }
    }
    load();
    return ()=>{active=false;requestBusy.current=false;clearTimeout(timeout);controller.abort();};
  },[open,generator,index,revision]);
  const visiblePage=page?.generator===generator ? page : null;
  const visibleError=error?.generator===generator ? error.message : "";
  function navigate(target,event){if(requestBusy.current)return;requestBusy.current=true;focusRequest.current=event.currentTarget;setLoading(true);if(target===index)setRevision(value=>value+1);else setPosition({generator,index:target});}
  function refresh(){if(requestBusy.current)return;requestBusy.current=true;setLoading(true);setRevision(value=>value+1);}
  const content=<>
      {loading && <p role="status">변경 기록을 불러오는 중…</p>}
      {visibleError && <p role="alert">{visibleError}</p>}
      {visiblePage && (loading || visibleError) && <p>아래는 마지막으로 조회한 변경 기록입니다.</p>}
      <div className="choice-buttons">
        <button type="button" disabled={loading || !visiblePage || visiblePage.index===0} onClick={event=>navigate(visiblePage.index-1,event)}>이전 페이지</button>
        <button type="button" disabled={loading || !visiblePage || visiblePage.index+1>=visiblePage.count} onClick={event=>navigate(visiblePage.index+1,event)}>다음 페이지</button>
        <button ref={refreshRef} type="button" aria-disabled={loading} onClick={refresh}>{loading ? "조회 중…" : "새로고침"}</button>
      </div>
      {visiblePage && <><p>{visiblePage.date || "날짜 없음"} · {visiblePage.index+1} / {visiblePage.count}</p><pre tabIndex={0} aria-label="변경 기록 내용">{visiblePage.content}</pre></>}
    </>;
  if(card)return <GeneratorSectionCard title="생성기 변경 기록" summary="업데이트 내역" className="generator-changelog" onOpenChange={setOpen}>{open && content}</GeneratorSectionCard>;
  return <details className="generator-changelog" onToggle={event=>setOpen(event.currentTarget.open)}><summary>생성기 변경 기록</summary>{open && content}</details>;
}
