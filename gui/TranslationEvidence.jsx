import React, {useEffect,useRef,useState} from "react";
import ActionButton from "./ActionButton.jsx";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";

export function validTranslationEvidence(result) {
  return Boolean(result && typeof result.note === "string" && Array.isArray(result.candidates) && result.candidates.every(item=>item && typeof item.heading === "string" && typeof item.path === "string" && typeof item.text === "string" && Array.isArray(item.matched_terms) && item.matched_terms.every(term=>typeof term === "string")));
}

export default function TranslationEvidence({source,call}) {
  const [busy,setBusy]=useState(false);
  const [result,setResult]=useState(null);
  const [error,setError]=useState("");
  const request=useRef(null);
  const searchButton=useRef(null),restoreFocus=useRef(false);
  const sourceRef=useRef(source);sourceRef.current=source;
  useEffect(()=>()=>{request.current?.abort();},[]);
  useEffect(()=>{request.current?.abort();request.current=null;setBusy(false);setResult(null);setError("");},[source]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body && searchButton.current && !searchButton.current.disabled)searchButton.current.focus();}},[busy]);
  async function search() {
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    restoreFocus.current=document.activeElement===searchButton.current;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setResult(null);setError("");
    try {
      const next=await untilAborted(call("translation-evidence",{text:source},{signal:controller.signal}),controller.signal);
      if(!validTranslationEvidence(next))throw new Error("문서 검색 응답을 확인할 수 없습니다.");
      if(!controller.signal.aborted && sourceRef.current===source)setResult({source,value:next});
    } catch(problem){if(request.current===controller && sourceRef.current===source && (!controller.signal.aborted || timedOut))setError(timedOut ? "문서 검색 시간이 초과됐습니다. 다시 검색하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  return <details><summary>작가 AI 문서에서 용어 후보 찾기</summary>
    <ActionButton buttonRef={searchButton} reasons={[busy && "문서를 검색하고 있습니다.",!source.trim() && "검색할 한국어 원문을 입력하세요."]} onClick={search}>원문으로 문서 검색</ActionButton>
    {busy && <p role="status">문서를 검색하고 있습니다.</p>}
    {error && <p role="alert">{error}</p>}
    {result?.source===source && <><p role="status">{result.value.candidates.length ? `${result.value.candidates.length}건` : "검색된 문서 후보가 없습니다."} · {result.value.note}</p>
      {result.value.candidates.map((item,index)=><section key={index}><strong>{item.heading}</strong>
        <p>{item.path} · {item.matched_terms.join(", ")}</p><p>{item.text}</p></section>)}</>}
  </details>;
}
