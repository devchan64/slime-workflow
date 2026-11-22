import React,{useEffect,useRef,useState} from "react";

export default function JobIdentifier({id,compact=false,label="작업 ID"}){
  const [notice,setNotice]=useState("");
  const valueRef=useRef(null);
  const currentId=useRef(id);currentId.current=id;
  useEffect(()=>{setNotice("");},[id]);
  if(typeof id!=="string" || !id)return null;
  async function copy(){
    try{await navigator.clipboard.writeText(id);if(currentId.current===id)setNotice(label+"를 복사했습니다.");}
    catch{
      if(currentId.current!==id)return;
      const value=valueRef.current;
      value?.focus();
      if(compact && value){const range=document.createRange();range.selectNodeContents(value);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}
      else value?.select();
      setNotice("ID를 선택했습니다. 복사 단축키를 사용하세요.");
    }
  }
  if(compact)return <span className="job-identifier job-identifier-compact"><code ref={valueRef} tabIndex={-1}>{id}</code><button type="button" onClick={copy} aria-label={label+" 복사 · "+id}>복사</button><span role="status">{notice}</span></span>;
  return <div className="job-identifier"><label>{label}<input ref={valueRef} aria-label={label} type="text" readOnly value={id} onFocus={event=>event.currentTarget.select()}/></label>
    <button type="button" onClick={copy} aria-label={label+" 복사 · "+id}>ID 복사</button><span role="status">{notice}</span></div>;
}
