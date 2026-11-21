import React, {useEffect,useState} from "react";

export default function GeneratorChangelog({generator}) {
  const [open,setOpen]=useState(false);
  const [index,setIndex]=useState(0);
  const [revision,setRevision]=useState(0);
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    if (!open) return;
    const controller=new AbortController();
    setPage(null);setError("");
    async function load() {
      try {
        const response=await fetch("/management/assistant/changelog/"+encodeURIComponent(generator)+"?page="+index,
          {cache:"no-store",signal:controller.signal});
        if (!response.ok) throw new Error("변경 기록 조회 실패 · HTTP "+response.status);
        const result=await response.json();
        if (!controller.signal.aborted) setPage(result);
      } catch(problem) {
        if (!controller.signal.aborted) setError(problem.message);
      }
    }
    load();
    return ()=>controller.abort();
  },[open,generator,index,revision]);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}><summary>생성기 변경 기록</summary>
    {open && <>
      {error && <p role="alert">{error}</p>}
      <div className="choice-buttons">
        <button type="button" disabled={!page || page.index===0} onClick={()=>setIndex(page.index-1)}>이전 페이지</button>
        <button type="button" disabled={!page || page.index+1>=page.count} onClick={()=>setIndex(page.index+1)}>다음 페이지</button>
        <button type="button" onClick={()=>setRevision(value=>value+1)}>새로고침</button>
      </div>
      {page && <><p>{page.date || "날짜 없음"} · {page.index+1} / {page.count}</p><pre>{page.content}</pre></>}
    </>}
  </details>;
}
