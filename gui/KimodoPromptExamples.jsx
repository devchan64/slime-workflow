import React,{useEffect,useRef,useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";
import {readKimodoJson} from "./readKimodoInput.mjs";
import {validKimodoExampleList} from "./kimodoExampleValidation.mjs";

export default function KimodoPromptExamples({apply,applySettings}){
  const [rows,setRows]=useState([]),[id,select]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [loaded,setLoaded]=useState(false);
  const selectRef=useRef(null);
  const loadRef=useRef(null),request=useRef(null);
  useEffect(()=>()=>{const current=request.current;request.current=null;current?.abort();},[]);
  function focusIfIdle(target){if(document.activeElement===document.body || document.activeElement===loadRef.current)target?.focus();}
  async function load(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    let hasExamples=false;
    try{
      const examples=await readKimodoJson("/management/assistant/kimodo-prompt-examples",controller.signal,"동작 설명 예시를 불러올 수 없습니다.");
      if(!validKimodoExampleList(examples))throw new Error("동작 설명 예시 응답을 확인할 수 없습니다.");
      if(request.current!==controller)return;
      hasExamples=examples.length>0;
      setRows(examples);select(examples[0]?.id || "");setLoaded(true);
      if(examples.length)requestAnimationFrame(()=>focusIfIdle(selectRef.current));
    }catch(problem){if(request.current===controller)setError(timedOut ? "동작 설명 예시 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}
    finally{clearTimeout(timer);if(request.current===controller){request.current=null;setBusy(false);if(!hasExamples)requestAnimationFrame(()=>focusIfIdle(loadRef.current));}}
  }
  const selected=rows.find(row=>row.id===id);
  return <section aria-label="동작 설명 예시">
    {!rows.length && <button ref={loadRef} type="button" disabled={busy} onClick={load}>{busy?"예시 조회 중…":error?"동작 설명 예시 다시 조회":"동작 설명 예시 조회"}</button>}
    {loaded && !rows.length && !busy && !error && <p role="status">등록된 동작 설명 예시가 없습니다.</p>}
    {selected && <><label>동작 설명 예시 <select ref={selectRef} value={id} onChange={e=>select(e.target.value)}>
      {rows.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
      <details><summary>동작 설명 미리보기</summary><pre>{selected.prompt}</pre></details><button type="button" onClick={()=>apply(selected.prompt)}>동작 설명에 적용</button>
      {applySettings && <button type="button" onClick={event=>applySettings(selected.id,event.currentTarget)}>예시 설정과 참조 함께 적용</button>}</>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
