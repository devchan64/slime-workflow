import React,{useEffect,useRef,useState} from "react";

export default function MusicExamples({apply}) {
  const [open,setOpen]=useState(false);
  const [examples,setExamples]=useState(null);
  const [selected,select]=useState("");
  const [applied,setApplied]=useState("");
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false),[attempt,setAttempt]=useState(0);
  const selectRef=useRef(null),summaryRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{
    if(!open || examples)return;
    const controller=new AbortController();
    async function load(){
      setError("");setLoading(true);
      try{
        const response=await fetch("/management/assistant/heartmula-examples",{signal:controller.signal});
        if(!response.ok)throw new Error("음악 예제를 불러올 수 없습니다.");
        const rows=await response.json();
        if(!Array.isArray(rows) || rows.some(row=>!row || typeof row.id!=="string" || typeof row.label!=="string" || !row.request || typeof row.request.prompt!=="string" || typeof row.request.lyrics!=="string"))throw new Error("음악 예제 목록 형식을 확인할 수 없습니다.");
        if(!controller.signal.aborted){setExamples(rows);select(rows[0]?.id || "");}
      }catch(problem){if(!controller.signal.aborted)setError(problem.message);}
      finally{if(!controller.signal.aborted)setLoading(false);}
    }
    load();
    return ()=>controller.abort();
  },[open,examples,attempt]);
  useEffect(()=>{
    if(examples===null || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)(examples.length ? selectRef : summaryRef).current?.focus();
  },[examples]);
  useEffect(()=>{
    if(!error || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)retryRef.current?.focus();
  },[error]);
  const row=examples?.find(item=>item.id===selected);
  return <details className="music-examples" onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary ref={summaryRef}>음악 예제</summary>
    {loading && <p role="status">음악 예제 조회 중…</p>}
    {error && <div role="alert"><p>{error}</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=true;setAttempt(value=>value+1);}}>다시 시도</button></div>}
    {examples?.length===0 && <p>등록된 음악 예제가 없습니다.</p>}
    {examples?.length>0 && <label>예제 선택 <select ref={selectRef} value={selected} onChange={event=>{select(event.target.value);setApplied("");}}>
      {examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>}
    {row && <>
      <p>{row.description}</p><p>출력 상한 {row.request.duration_seconds}초 · 시드 {row.request.seed}</p>
      <p>{row.request.prompt}</p><details><summary>가사 미리보기</summary><pre tabIndex={0} aria-label="예제 가사 미리보기">{row.request.lyrics}</pre></details>
      <p>적용하면 음악 태그, 가사, 출력 시간과 시드를 예제 값으로 바꿉니다.</p>
      <button type="button" onClick={()=>{apply(row.request);setApplied(row.label);}}>예제를 입력에 적용</button>
      {applied && <p role="status">{applied} 예제를 입력에 적용했습니다. 아래에서 값을 수정할 수 있습니다.</p>}
    </>}
  </details>;
}
