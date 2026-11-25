import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ClipboardCopyButton from "./ClipboardCopyButton.jsx";
import {writeClipboardText} from "./clipboardWrite.mjs";
import ResultTable from "./ResultTable.jsx";
import {requestErrorMessage} from "./requestError.mjs";

export function translationCheckTable(result) {
  const validItems=items=>Array.isArray(items) && items.every(item=>item && typeof item.source==="string" && typeof item.target==="string" && typeof item.status==="string" && (item.source_ref==null || typeof item.source_ref==="string"));
  if(!result || typeof result!=="object" || (result.term_checks!=null && !validItems(result.term_checks)) || (result.quality_checks!=null && !validItems(result.quality_checks)))throw new Error("번역 점검 응답 형식을 확인할 수 없습니다.");
  const rows=(result.term_checks || []).map(item=>[item.source,item.target,item.status==="matched" ? "일치" : item.status==="mismatch" ? "불일치 · 확인 필요" : "확인 필요",item.source_ref || ""]);
  for(const item of result.quality_checks || [])rows.push([item.source,item.target,item.status==="matched" ? "표현 발견 · 문맥 확인" : item.status==="reversed" ? "행·열 역전" : "확인 필요",item.source_ref || ""]);
  return {title:"용어·배치·조건 점검",emptyMessage:"표시할 용어·배치·조건 점검 항목이 없습니다.",summary:result.quality_checks ? "원본 번역 결과 기준" : "이전 작업 · 배치·조건 미검사",columns:["원문","번역어","결과","근거"],rows};
}

export function TranslationCheckStatus({busy,stale,hasChecks,sourceChanged,busyId}){
  if(busy)return <p id={busyId} role="status">원본 번역 점검을 조회하고 있습니다.{hasChecks && (sourceChanged ? " 아래 점검 표는 이전 원본 번역 기준입니다." : " 아래 점검 표는 마지막으로 조회한 결과입니다.")}</p>;
  if(hasChecks && sourceChanged)return <p role="status">아래 점검 표는 이전 원본 번역 기준입니다. 현재 원본을 다시 점검하세요.</p>;
  return stale && hasChecks ? <p role="status">아래 점검 표는 마지막으로 조회한 결과입니다.</p> : null;
}

export function TranslationSourceNotice({changed}){
  return changed ? <p role="status">원본 번역 결과가 변경됐습니다. 현재 복사 초안은 이전 내용을 유지합니다. 최신 원본을 사용하려면 필요한 내용을 복사한 뒤 결과를 다시 여세요.</p> : null;
}

export default function TranslationResult(props) {
  return <TranslationResultForJob key={props.job} {...props}/>;
}

function TranslationResultForJob({job, text}) {
  const busyId=useId();
  const originalText=useRef(text);
  const sourceText=useRef(text);sourceText.current=text;
  const [draft,setDraft] = useState(text);
  const [checks,setChecks] = useState(null);
  const [checkSource,setCheckSource] = useState(null);
  const [busy,setBusy] = useState(false);
  const [notice,setNoticeState] = useState(""),[noticeError,setNoticeError]=useState(false);
  function setNotice(message,{error=false}={}){setNoticeState(message);setNoticeError(error);}
  const [stale,setStale] = useState(false);
  const textRef=useRef(null),copyRef=useRef(null),inspectRef=useRef(null),inspectRequest=useRef(null),focusFrame=useRef(null);
  const copySequence=useRef(0);
  useEffect(()=>()=>{copySequence.current++;inspectRequest.current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);},[]);
  const draftRef=useRef(draft);draftRef.current=draft;
  async function inspect() {
    if(inspectRequest.current)return;
    if(focusFrame.current!==null){cancelAnimationFrame(focusFrame.current);focusFrame.current=null;}
    const controller=new AbortController();inspectRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const restoreFocus=document.activeElement===inspectRef.current;
    setBusy(true);setNotice("");
    try {
      const record = await untilAborted(managementCommand("prompt-translation","translation-status",{id:job},{signal:controller.signal}),controller.signal);
      if (record.id!==job || !record.result) throw new Error("해당 작업의 번역 결과를 확인할 수 없습니다.");
      if(typeof record.result.text!=="string" || record.result.text!==sourceText.current)throw new Error("표시된 원본 번역과 점검 대상이 다릅니다. 결과를 다시 조회하세요.");
      setChecks(translationCheckTable(record.result));
      setCheckSource(record.result.text);
      setStale(false);
    } catch(problem) {if(!controller.signal.aborted || timedOut){setStale(Boolean(checks));setNotice("번역 점검을 조회하지 못했습니다 · "+(timedOut ? "조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem)),{error:true});}}
    finally {clearTimeout(timeout);if(inspectRequest.current===controller)inspectRequest.current=null;if(!controller.signal.aborted || timedOut){setBusy(false);if(restoreFocus)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;if(document.activeElement===document.body && inspectRef.current?.isConnected && !inspectRef.current.matches(":disabled"))inspectRef.current.focus();});}}
  }
  async function copy() {
    const sequence=++copySequence.current,value=draftRef.current;
    try {await writeClipboardText(value);if(sequence===copySequence.current)setNotice(draftRef.current===value ? "번역문을 복사했습니다." : "이전 번역문을 복사했습니다. 변경한 내용을 복사하려면 다시 누르세요.");}
    catch {if(sequence!==copySequence.current)return;if(draftRef.current===value && (document.activeElement===document.body || document.activeElement===copyRef.current) && textRef.current?.isConnected && !textRef.current.matches(":disabled")){textRef.current.focus();textRef.current.select();}setNotice(draftRef.current===value ? "복사 여부를 확인하지 못했습니다. 번역문을 선택해 복사 단축키를 사용하세요." : "이전 번역문의 복사 여부를 확인하지 못했습니다. 현재 내용을 복사하려면 다시 누르세요.",{error:true});}
  }
  return <section className="translation-result"><TranslationSourceNotice changed={text!==originalText.current}/><label>복사용 번역문 <textarea ref={textRef} value={draft} onChange={e=>{draftRef.current=e.target.value;setDraft(e.target.value);setNotice("");}}/></label>
    <div className="choice-buttons">
    <ClipboardCopyButton ref={copyRef} onClick={copy} label="번역문 복사"/>
    <button ref={inspectRef} disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>{busy ? "번역 점검 조회 중…" : "원본 번역 점검 조회"}</button>
    </div>
    <TranslationCheckStatus busy={busy} stale={stale} hasChecks={Boolean(checks)} sourceChanged={Boolean(checks && checkSource!==text)} busyId={busyId}/>
    {checks && <div className="translation-check-table"><ResultTable table={checks}/></div>}
    <p role={noticeError ? "alert" : "status"}>{notice}</p>
  </section>;
}
