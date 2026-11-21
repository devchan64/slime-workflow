import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function Sheet({path,source}){
  const [detail,setDetail]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    managementCommand("character-animation","sheet-image",{path,source}).then(record=>{
      if(record.path!==path || !record.image)throw new Error("선택한 시트 원본을 확인할 수 없습니다.");
      if(active)setDetail(record);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[path,source]);
  if(error)return <p role="alert">{error}</p>;
  if(!detail)return <p role="status">원본 시트를 불러오는 중…</p>;
  const frames=detail.animation?.frames;
  return <section><h2>{path}</h2><img src={"data:image/png;base64,"+detail.image} alt="원본 스프라이트 시트" style={{maxWidth:"100%"}}/>
    {detail.layout && <p>{detail.layout.columns}열 × {detail.layout.rows}행</p>}
    {frames?.length>0 && <ResultTable table={{title:"등록 프레임 좌표",summary:frames.length+"프레임",
      columns:["프레임","X","Y","너비","높이","앵커 X","앵커 Y"],
      rows:frames.map(({rect,anchor},index)=>[index+1,rect.x,rect.y,rect.width,rect.height,anchor.x,anchor.y])}}/>}
  </section>;
}

export default function SpriteSheetEditor(){
  const [source,setSource]=useState("assets"),[query,setQuery]=useState("");
  const [request,setRequest]=useState(null),[items,setItems]=useState(null),[selected,select]=useState("");
  const [error,setError]=useState("");
  useEffect(()=>{
    if(!request)return;
    let active=true;
    managementCommand("character-animation","sheet-search",request).then(result=>{
      if(active)setItems(result.items);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[request]);
  function search(nextSource){
    setItems(null);setError("");select("");setRequest({source:nextSource,query});
  }
  return <article><h1>스프라이트 시트 편집기</h1>
    <form onSubmit={event=>{event.preventDefault();search(source);}}>
      <label>검색 원본<select value={source} onChange={event=>{setSource(event.target.value);search(event.target.value);}}>
        <option value="assets">에셋 스프라이트</option><option value="baseline">베이스라인 스프라이트</option></select></label>
      <label>스프라이트 검색<input value={query} onChange={event=>setQuery(event.target.value)}/></label>
      <button>원본 검색</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {request && !items && !error && <p role="status">스프라이트 검색 중…</p>}
    {items && <ResultTable table={{title:"검색 결과",summary:items.length+"개 시트",columns:["스프라이트","원본 경로"],
      rows:items.map(item=>[<button onClick={()=>select(item.path)}>{item.label}</button>,item.path])}}/>}
    {selected && <Sheet key={source+":"+selected} path={selected} source={source}/>}
  </article>;
}
