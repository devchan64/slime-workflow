import React,{useEffect,useRef,useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import PromptWordCount from "./PromptWordCount.jsx";

export function validMusicExamples(rows){
  return Array.isArray(rows) && rows.every(row=>row && typeof row.id==="string" && row.id.trim() && typeof row.label==="string" && row.label.trim() && typeof row.description==="string" && row.request && typeof row.request.prompt==="string" && typeof row.request.lyrics==="string" && Number.isFinite(row.request.duration_seconds) && row.request.duration_seconds>=5 && row.request.duration_seconds<=300 && Number.isSafeInteger(row.request.seed) && row.request.seed>=0) && new Set(rows.map(row=>row.id)).size===rows.length;
}
export function musicExampleInputs({prompt,lyrics,duration_seconds,seed}){
  return {prompt,lyrics,duration_seconds,seed};
}
export function MusicExampleDetail({row,apply,onApplied}){
  return <>
    <p>{row.description}</p><p>출력 상한 {row.request.duration_seconds}초 · 시드 {row.request.seed}</p>
    <p>{row.request.prompt} <PromptWordCount text={row.request.prompt} label="예제 프롬프트"/></p><details><summary>가사 미리보기</summary><pre tabIndex={0} aria-label="예제 가사 미리보기">{row.request.lyrics}</pre></details>
    <p>적용하면 음악 태그, 가사, 출력 시간과 시드를 예제 값으로 바꿉니다.</p>
    <button type="button" onClick={()=>{apply(musicExampleInputs(row.request));onApplied(row.label);}}>예제를 입력에 적용</button>
  </>;
}

export default function MusicExamples({apply}) {
  const [open,setOpen]=useState(false);
  const [examples,setExamples]=useState(null);
  const [selected,select]=useState("");
  const [applied,setApplied]=useState("");
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false),[attempt,setAttempt]=useState(0);
  const selectRef=useRef(null),summaryRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false),retryPending=useRef(false);
  useEffect(()=>{
    if(!open || examples)return;
    const controller=new AbortController();let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function load(){
      setError("");setLoading(true);
      try{
        const rows=await untilAborted((async()=>{const response=await fetch("/management/assistant/heartmula-examples",{signal:controller.signal});
        if(!response.ok)throw new Error("음악 예제를 불러올 수 없습니다.");return response.json();})(),controller.signal);
        if(!validMusicExamples(rows))throw new Error("음악 예제 목록 형식을 확인할 수 없습니다.");
        if(!controller.signal.aborted){setExamples(rows);select(rows[0]?.id || "");}
      }catch(problem){if(active)setError(timedOut ? "음악 예제 조회 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
      finally{clearTimeout(timeout);if(active){retryPending.current=false;setLoading(false);}}
    }
    load();
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[open,examples,attempt]);
  useEffect(()=>{
    if(!open || examples===null || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)(examples.length ? selectRef : summaryRef).current?.focus();
  },[open,examples]);
  useEffect(()=>{
    if(!open || !error || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)retryRef.current?.focus();
  },[open,error]);
  const row=examples?.find(item=>item.id===selected);
  return <details className="music-examples" onToggle={event=>{if(!event.currentTarget.open)restoreFocus.current=false;setOpen(event.currentTarget.open);}}>
    <summary ref={summaryRef}>음악 예제</summary>
    {loading && <p role="status">음악 예제 조회 중…</p>}
    {error && <div><p role="alert">{error}</p><button ref={retryRef} type="button" onClick={()=>{if(retryPending.current)return;retryPending.current=true;restoreFocus.current=document.activeElement===retryRef.current;setError("");setLoading(true);setAttempt(value=>value+1);}}>다시 시도</button></div>}
    {examples?.length===0 && <p>등록된 음악 예제가 없습니다.</p>}
    {examples?.length>0 && <label>예제 선택 <select ref={selectRef} value={selected} onChange={event=>{select(event.target.value);setApplied("");}}>
      {examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>}
    {row && <><MusicExampleDetail row={row} apply={apply} onApplied={setApplied}/>{applied && <p role="status">{applied} 예제를 입력에 적용했습니다. 아래에서 값을 수정할 수 있습니다.</p>}</>}
  </details>;
}
