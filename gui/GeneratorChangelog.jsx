import React, {useEffect,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import {requestErrorMessage} from "./requestError.mjs";

export default function GeneratorChangelog({generator,card=false}) {
  const [open,setOpen]=useState(false);
  const [index,setIndex]=useState(0);
  const [revision,setRevision]=useState(0);
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  useEffect(()=>{
    if (!open) return;
    const controller=new AbortController();
    let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setPage(null);setError("");setLoading(true);
    async function load() {
      try {
        const response=await fetch("/management/assistant/changelog/"+encodeURIComponent(generator)+"?page="+index,
          {cache:"no-store",signal:controller.signal});
        if (!response.ok) throw new Error("변경 기록 조회 실패 · HTTP "+response.status);
        const result=await response.json();
        if(!result || typeof result.content!=="string" || !Number.isInteger(result.index) || result.index<0 || !Number.isInteger(result.count) || result.count<=result.index || (result.date!=null && typeof result.date!=="string"))throw new Error("변경 기록 응답을 확인할 수 없습니다.");
        if (!controller.signal.aborted) setPage(result);
      } catch(problem) {
        if (active) setError(timedOut ? "변경 기록 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));
      } finally {
        clearTimeout(timeout);if(active)setLoading(false);
      }
    }
    load();
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[open,generator,index,revision]);
  const content=<>
      {loading && <p role="status">변경 기록을 불러오는 중…</p>}
      {error && <p role="alert">{error}</p>}
      <div className="choice-buttons">
        <button type="button" disabled={!page || page.index===0} onClick={()=>setIndex(page.index-1)}>이전 페이지</button>
        <button type="button" disabled={!page || page.index+1>=page.count} onClick={()=>setIndex(page.index+1)}>다음 페이지</button>
        <button type="button" onClick={()=>setRevision(value=>value+1)}>새로고침</button>
      </div>
      {page && <><p>{page.date || "날짜 없음"} · {page.index+1} / {page.count}</p><pre>{page.content}</pre></>}
    </>;
  if(card)return <GeneratorSectionCard title="생성기 변경 기록" summary="업데이트 내역" className="generator-changelog" onOpenChange={setOpen}>{open && content}</GeneratorSectionCard>;
  return <details className="generator-changelog" onToggle={event=>setOpen(event.currentTarget.open)}><summary>생성기 변경 기록</summary>{open && content}</details>;
}
