import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function Preview({id}){
  const [result,setResult]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    managementCommand("hermes-agent","hermes-kimodo-keyframe-preview",{keyframe_id:id}).then(value=>{
      if(value.id!==id || !value.image_base64)throw new Error("선택한 키프레임을 확인할 수 없습니다.");
      if(active)setResult(value);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[id]);
  if(error)return <p role="alert">{error}</p>;
  if(!result)return <p role="status">원본 확인 중…</p>;
  return <figure><img src={"data:image/png;base64,"+result.image_base64} alt={id+" 키프레임"} style={{maxWidth:"100%"}}/>
    <figcaption>{id} · PNG SHA-256 <code>{result.sha256}</code></figcaption></figure>;
}

export default function KeyframeCatalog({query,choose}){
  const [cursor,setCursor]=useState({}),[page,setPage]=useState(null);
  const [error,setError]=useState(""),[selected,select]=useState("");
  useEffect(()=>{
    let active=true;
    setPage(null);select("");setError("");
    const timer=setTimeout(()=>{
      managementCommand("hermes-agent","hermes-kimodo-keyframes",{query,limit:20,...cursor})
        .then(result=>{if(active)setPage(result);})
        .catch(problem=>{if(active)setError(problem.message);});
    },200);
    return ()=>{active=false;clearTimeout(timer);};
  },[query,cursor]);
  return <section aria-label="Kimodo 키프레임 검색">
    {error && <p role="alert">{error} <button onClick={()=>setCursor({})}>다시 조회</button></p>}
    {!error && !page && <p role="status">키프레임 조회 중…</p>}
    {page && <><ResultTable table={{title:"등록 키프레임",summary:"검색 결과 "+page.total+"개",
      columns:["ID","태그","원본 프레임","대화"],rows:page.items.map(row=>[
        <button onClick={()=>select(row.id)}>{row.id}</button>,row.tag,row.source_frame,
        <button onClick={()=>choose("Kimodo 키프레임",row.id)}>입력에 추가</button>])}}/>
      {cursor.offset>0 && <button onClick={()=>setCursor({offset:Math.max(0,cursor.offset-20),snapshot:page.snapshot})}>이전 키프레임</button>}
      {page.next_offset!=null && <button onClick={()=>setCursor({offset:page.next_offset,snapshot:page.snapshot})}>다음 키프레임</button>}
      {selected && <Preview key={selected} id={selected}/>}</>}
  </section>;
}
