import React,{useEffect,useState} from "react";

export default function JobIdentifier({id,compact=false}){
  const [notice,setNotice]=useState("");
  useEffect(()=>{setNotice("");},[id]);
  if(typeof id!=="string" || !id)return null;
  async function copy(){
    try{await navigator.clipboard.writeText(id);setNotice("작업 ID를 복사했습니다.");}
    catch{setNotice("복사하지 못했습니다. 표시된 ID를 직접 선택해 복사하세요.");}
  }
  if(compact)return <span className="job-identifier job-identifier-compact"><code>{id}</code><button type="button" onClick={copy} aria-label={"작업 ID 복사 · "+id}>복사</button><span role="status">{notice}</span></span>;
  return <div className="job-identifier"><label>작업 ID<input aria-label="작업 ID" type="text" readOnly value={id} onFocus={event=>event.currentTarget.select()}/></label>
    <button type="button" onClick={copy} aria-label={"작업 ID 복사 · "+id}>ID 복사</button><span role="status">{notice}</span></div>;
}
