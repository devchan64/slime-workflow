import React, {useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import {requestErrorMessage} from "./requestError.mjs";

export default function TranslationResult({job, text}) {
  const [draft,setDraft] = useState(text);
  const [checks,setChecks] = useState(null);
  const [busy,setBusy] = useState(false);
  const [notice,setNotice] = useState("");
  const [stale,setStale] = useState(false);
  const textRef=useRef(null),copyRef=useRef(null),inspectRef=useRef(null),inspectRequest=useRef(null);
  useEffect(()=>()=>inspectRequest.current?.abort(),[]);
  const draftRef=useRef(draft);draftRef.current=draft;
  async function inspect() {
    if(inspectRequest.current)return;
    const controller=new AbortController();inspectRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const restoreFocus=document.activeElement===inspectRef.current;
    setBusy(true);setNotice("");
    try {
      const record = await managementCommand("prompt-translation","translation-status",{id:job},{signal:controller.signal});
      if (record.id!==job || !record.result) throw new Error("해당 작업의 번역 결과를 확인할 수 없습니다.");
      const {term_checks=[],quality_checks} = record.result;
      const rows = term_checks.map(item=>[item.source,item.target,item.status==="matched"?"일치":"불일치 · 확인 필요",item.source_ref || ""]);
      for (const item of quality_checks || []) {
        rows.push([item.source,item.target,({matched:"표현 발견 · 문맥 확인",reversed:"행·열 역전"})[item.status] || "확인 필요",item.source_ref || ""]);
      }
      setChecks({title:"용어·배치·조건 점검", summary:quality_checks ? "원본 번역 결과 기준" : "이전 작업 · 배치·조건 미검사",
        columns:["원문","번역어","결과","근거"],rows});
      setStale(false);
    } catch(problem) {if(!controller.signal.aborted || timedOut){setStale(Boolean(checks));setNotice("번역 점검을 조회하지 못했습니다 · "+(timedOut ? "조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem)));}}
    finally {clearTimeout(timeout);if(inspectRequest.current===controller)inspectRequest.current=null;if(!controller.signal.aborted || timedOut){setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body && inspectRef.current?.isConnected)inspectRef.current.focus();});}}
  }
  async function copy() {
    try {await navigator.clipboard.writeText(draft);setNotice(draftRef.current===draft ? "번역문을 복사했습니다." : "이전 번역문을 복사했습니다. 변경한 내용을 복사하려면 다시 누르세요.");}
    catch {if(document.activeElement===document.body || document.activeElement===copyRef.current){textRef.current?.focus();textRef.current?.select();}setNotice("번역문을 선택해 복사 단축키를 사용하세요.");}
  }
  return <section><label>복사용 번역문 <textarea ref={textRef} value={draft} onChange={e=>{setDraft(e.target.value);setNotice("");}}/></label>
    <button ref={copyRef} onClick={copy}>번역문 복사</button>
    <button ref={inspectRef} disabled={busy} onClick={inspect}>{busy ? "번역 점검 조회 중…" : "원본 번역 점검 조회"}</button>
    {checks && <>{stale && <p role="status">아래 점검 표는 마지막으로 조회한 결과입니다.</p>}<div className="translation-check-table" role="region" aria-label="번역 점검 표" tabIndex={0}><ResultTable table={checks}/></div></>}
    <p role="status">{notice}</p>
  </section>;
}
