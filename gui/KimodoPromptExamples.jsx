import React,{useRef,useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";

export default function KimodoPromptExamples({apply,applySettings}){
  const [rows,setRows]=useState([]),[id,select]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [loaded,setLoaded]=useState(false);
  const selectRef=useRef(null);
  const loadRef=useRef(null);
  function focusIfIdle(target){if(document.activeElement===document.body || document.activeElement===loadRef.current)target?.focus();}
  async function load(){
    setBusy(true);setError("");
    let hasExamples=false;
    try{
      const response=await fetch("/management/assistant/kimodo-prompt-examples");
      if(!response.ok)throw new Error("동작 설명 예시를 불러올 수 없습니다.");
      const examples=await response.json();
      if(!Array.isArray(examples))throw new Error("동작 설명 예시 응답을 확인할 수 없습니다.");
      hasExamples=examples.length>0;
      setRows(examples);select(examples[0]?.id || "");setLoaded(true);
      if(examples.length)requestAnimationFrame(()=>focusIfIdle(selectRef.current));
    }catch(problem){setError(requestErrorMessage(problem));}
    finally{setBusy(false);if(!hasExamples)requestAnimationFrame(()=>focusIfIdle(loadRef.current));}
  }
  const selected=rows.find(row=>row.id===id);
  return <section aria-label="동작 설명 예시">
    {!rows.length && <button ref={loadRef} type="button" disabled={busy} onClick={load}>{busy?"예시 조회 중…":error?"동작 설명 예시 다시 조회":"동작 설명 예시 조회"}</button>}
    {loaded && !rows.length && !busy && !error && <p role="status">등록된 동작 설명 예시가 없습니다.</p>}
    {selected && <><label>동작 설명 예시 <select ref={selectRef} value={id} onChange={e=>select(e.target.value)}>
      {rows.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
      <details><summary>동작 설명 미리보기</summary><pre>{selected.prompt}</pre></details><button type="button" onClick={()=>apply(selected.prompt)}>동작 설명에 적용</button>
      {applySettings && <button type="button" onClick={()=>applySettings(selected.id)}>예시 설정과 참조 함께 적용</button>}</>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
