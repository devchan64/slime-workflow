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

function SearchResults({query,choose,add,disabled}){
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
        <><button onClick={()=>choose("Kimodo 키프레임",row.id)}>입력에 추가</button>
          <button disabled={disabled} onClick={()=>add(row.id)}>배치에 추가</button></>])}}/>
      {cursor.offset>0 && <button onClick={()=>setCursor({offset:Math.max(0,cursor.offset-20),snapshot:page.snapshot})}>이전 키프레임</button>}
      {page.next_offset!=null && <button onClick={()=>setCursor({offset:page.next_offset,snapshot:page.snapshot})}>다음 키프레임</button>}
      {selected && <Preview key={selected} id={selected}/>}</>}
  </section>;
}

export default function KeyframeCatalog({query,choose}){
  const [rows,setRows]=useState([]),[frames,setFrames]=useState("");
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[review,setReview]=useState(null);
  function edit(next){
    setRows(next);setReview(null);setError("");
  }
  async function validate(event){
    event.preventDefault();setBusy(true);setError("");setReview(null);
    try{
      const result=await managementCommand("hermes-agent","hermes-kimodo-keyframe-validate",{
        frames:Number(frames),keyframes:rows.map(row=>({id:row.id,frame:Number(row.frame)}))
      });
      if(!Array.isArray(result.placements) || result.placements.length!==rows.length || !result.skeleton_signature_sha256){
        throw new Error("배치 검증 결과를 확인할 수 없습니다.");
      }
      setReview(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <>
    <SearchResults key={query} query={query} choose={choose} disabled={busy || rows.length>=20}
      add={id=>edit([...rows,{id,frame:""}])}/>
    {rows.length>0 && <form onSubmit={validate}><fieldset disabled={busy}><legend>출력 프레임 배치</legend>
      <label>총 출력 프레임 수 (30~300)<input type="number" required min="30" max="300" value={frames}
        onChange={e=>{setFrames(e.target.value);setReview(null);setError("");}}/></label>
      {rows.map((row,index)=><div key={index}><label>{row.id} · 출력 프레임
        <input type="number" required min="1" max={frames || undefined} value={row.frame}
          onChange={e=>edit(rows.map((item,i)=>i===index?{...item,frame:e.target.value}:item))}/></label>
        <button type="button" onClick={()=>edit(rows.filter((_,i)=>i!==index))}>삭제</button></div>)}
      <button>원본과 배치 검증</button>
      {error && <p role="alert">{error}</p>}
      {review && <><p role="status">{review.placements.length}개 배치 검증 완료 · {review.note}</p>
        <ResultTable table={{title:"검증된 키프레임 배치",columns:["출력 프레임","키프레임 ID"],
          rows:review.placements.map(row=>[row.frame,row.id])}}/>
        <button type="button" onClick={()=>choose("Kimodo 키프레임 배치",JSON.stringify({frames:Number(frames),keyframes:review.placements}))}>검증한 배치를 대화 입력에 추가</button></>}
    </fieldset></form>}
  </>;
}
