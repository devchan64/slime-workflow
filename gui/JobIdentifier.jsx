import React,{useEffect,useRef,useState} from "react";
import ClipboardCopyButton from "./ClipboardCopyButton.jsx";
import {writeClipboardText} from "./clipboardWrite.mjs";

export default function JobIdentifier({id,compact=false,label="작업 ID"}){
  return <JobIdentifierForValue key={JSON.stringify([id,compact,label])} id={id} compact={compact} label={label}/>;
}

function JobIdentifierForValue({id,compact=false,label="작업 ID"}){
  const [notice,setNotice]=useState("");
  const valueRef=useRef(null),buttonRef=useRef(null);
  const request=useRef(0),timer=useRef(null);
  const currentId=useRef(id);currentId.current=id;
  useEffect(()=>{request.current++;clearTimeout(timer.current);setNotice("");},[id]);
  useEffect(()=>()=>{request.current++;clearTimeout(timer.current);},[]);
  if(typeof id!=="string" || !id)return null;
  async function copy(){
    const sequence=++request.current;clearTimeout(timer.current);
    try{await writeClipboardText(id);if(currentId.current===id && request.current===sequence){setNotice(label+"를 복사했습니다.");timer.current=setTimeout(()=>setNotice(""),3000);}}
    catch{
      if(currentId.current!==id || request.current!==sequence)return;
      const value=valueRef.current;
      if(document.activeElement===document.body || document.activeElement===buttonRef.current){
        value?.focus();
        if(compact && value){const selection=window.getSelection?.();if(selection){const range=document.createRange();range.selectNodeContents(value);selection.removeAllRanges();selection.addRange(range);}}
        else value?.select();
      }
      setNotice("ID를 선택해 복사 단축키를 사용하세요.");
    }
  }
  if(compact)return <span className="job-identifier job-identifier-compact"><code ref={valueRef} tabIndex={-1}>{id}</code><ClipboardCopyButton ref={buttonRef} onClick={copy} label={label+" 복사 · "+id} title={label+" 복사"}/><span role="status">{notice}</span></span>;
  return <div className="job-identifier"><label>{label}<input ref={valueRef} aria-label={label} type="text" readOnly value={id} onFocus={event=>event.currentTarget.select()}/></label>
    <ClipboardCopyButton ref={buttonRef} onClick={copy} label={label+" 복사 · "+id} title={label+" 복사"}/><span role="status">{notice}</span></div>;
}
