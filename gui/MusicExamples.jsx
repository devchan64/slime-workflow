import React,{useEffect,useState} from "react";

export default function MusicExamples({apply}) {
  const [open,setOpen]=useState(false);
  const [examples,setExamples]=useState(null);
  const [selected,select]=useState("");
  const [error,setError]=useState("");
  useEffect(()=>{
    if(!open || examples)return;
    const controller=new AbortController();
    async function load(){
      setError("");
      try{
        const response=await fetch("/management/assistant/heartmula-examples",{signal:controller.signal});
        if(!response.ok)throw new Error("음악 예제를 불러올 수 없습니다.");
        const rows=await response.json();
        if(!controller.signal.aborted){setExamples(rows);select(rows[0]?.id || "");}
      }catch(problem){if(!controller.signal.aborted)setError(problem.message);}
    }
    load();
    return ()=>controller.abort();
  },[open,examples]);
  const row=examples?.find(item=>item.id===selected);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>음악 예제</summary>
    {error && <p role="alert">{error}</p>}
    {examples && <label>예제 선택 <select value={selected} onChange={event=>select(event.target.value)}>
      {examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>}
    {row && <>
      <p>{row.description}</p><p>출력 상한 {row.request.duration_seconds}초 · 시드 {row.request.seed}</p>
      <p>{row.request.prompt}</p><pre>{row.request.lyrics}</pre>
      <button type="button" onClick={()=>apply(row.request)}>예제를 입력에 적용</button>
    </>}
  </details>;
}
