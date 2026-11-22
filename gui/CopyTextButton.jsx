import React,{useEffect,useRef,useState} from "react";
import {writeClipboardText} from "./clipboardWrite.mjs";

export default function CopyTextButton({value,label,buttonLabel}){
  const [state,setState]=useState(""),current=useRef(value),fallback=useRef(null),button=useRef(null),request=useRef(0),timer=useRef(null);
  current.current=value;
  useEffect(()=>{request.current++;setState("");clearTimeout(timer.current);},[value]);
  useEffect(()=>()=>{request.current++;clearTimeout(timer.current);},[]);
  function focusFallback(){if(fallback.current && (document.activeElement===document.body || document.activeElement===button.current)){fallback.current.focus();fallback.current.select();}}
  useEffect(()=>{if(state==="fallback")focusFallback();},[state]);
  async function copy(){
    const sequence=++request.current;
    clearTimeout(timer.current);
    try{await writeClipboardText(value);if(current.current===value && request.current===sequence){setState("copied");timer.current=setTimeout(()=>setState(""),3000);}}
    catch{if(current.current===value && request.current===sequence){setState("fallback");focusFallback();}}
  }
  return <span className="message-copy"><button ref={button} type="button" aria-label={label} onClick={copy}>{buttonLabel}</button><span role="status">{state==="copied" ? "복사했습니다." : state==="fallback" ? "클립보드 복사 여부를 확인하지 못했습니다. 아래 내용에서 복사 단축키를 사용하세요." : ""}</span>{state==="fallback" && <><button type="button" onClick={()=>{request.current++;clearTimeout(timer.current);setState("");requestAnimationFrame(()=>button.current?.focus());}}>선택 닫기</button><textarea ref={fallback} readOnly aria-label={label+"용 선택 내용"} value={value} onFocus={event=>event.currentTarget.select()}/></>}</span>;
}
