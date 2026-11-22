import React,{useEffect,useRef,useState} from "react";

export default function CopyTextButton({value,label,buttonLabel}){
  const [state,setState]=useState(""),current=useRef(value),fallback=useRef(null),button=useRef(null),request=useRef(0),timer=useRef(null);
  current.current=value;
  useEffect(()=>{request.current++;setState("");clearTimeout(timer.current);},[value]);
  useEffect(()=>()=>{request.current++;clearTimeout(timer.current);},[]);
  useEffect(()=>{if(state==="fallback" && fallback.current){fallback.current.focus();fallback.current.select();}},[state]);
  async function copy(){
    const sequence=++request.current;
    clearTimeout(timer.current);
    try{await navigator.clipboard.writeText(value);if(current.current===value && request.current===sequence){setState("copied");timer.current=setTimeout(()=>setState(""),3000);}}
    catch{if(current.current===value && request.current===sequence){setState("fallback");if(fallback.current){fallback.current.focus();fallback.current.select();}}}
  }
  return <span className="message-copy"><button ref={button} type="button" aria-label={label} onClick={copy}>{buttonLabel}</button><span role="status">{state==="copied" ? "복사했습니다." : state==="fallback" ? "복사할 내용을 선택했습니다. 복사 단축키를 사용하세요." : ""}</span>{state==="fallback" && <><button type="button" onClick={()=>{request.current++;clearTimeout(timer.current);setState("");requestAnimationFrame(()=>button.current?.focus());}}>선택 닫기</button><textarea ref={fallback} readOnly aria-label={label+"용 선택 내용"} value={value} onFocus={event=>event.currentTarget.select()}/></>}</span>;
}
