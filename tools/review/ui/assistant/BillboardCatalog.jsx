import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

const categories={vegetation:"식생",herbaceous:"초본","large-trees":"대형 나무","rocks-minerals":"바위·광물",props:"소품"};

export default function BillboardCatalog({choose}){
  const [query,setQuery]=useState(""),[category,setCategory]=useState("");
  const [request,setRequest]=useState({offset:0,limit:10}),[page,setPage]=useState(null);
  const [selected,select]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    setPage(null);select(null);setError("");
    managementCommand("hermes-agent","hermes-billboard-catalog",request).then(result=>{
      if(active)setPage(result);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[request]);
  function search(e){
    e.preventDefault();
    setRequest({offset:0,limit:10,query,...(category?{category}:{})});
  }
  return <section><h2>공용 빌보드 에셋</h2>
    <form onSubmit={search}><label>분류<select value={category} onChange={e=>setCategory(e.target.value)}>
      <option value="">전체</option>{Object.entries(categories).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
      <label>이름·ID·모델링 설명<input maxLength={100} value={query} onChange={e=>setQuery(e.target.value)}/></label>
      <button>빌보드 검색</button></form>
    {error && <p role="alert">{error}</p>}
    {!page && !error && <p role="status">카탈로그 조회 중…</p>}
    {page && <><ResultTable table={{title:"검색 결과",summary:page.total+"종",columns:["이름","에셋 ID","분류"],
      rows:page.items.map(asset=>[<button onClick={()=>select(asset)}>{asset.name}</button>,asset.id,categories[asset.category]])}}/>
      {page.offset>0 && <button onClick={()=>setRequest({...request,offset:Math.max(0,page.offset-page.limit)})}>이전 페이지</button>}
      {page.next_offset!=null && <button onClick={()=>setRequest({...request,offset:page.next_offset})}>다음 페이지</button>}</>}
    {selected && <section><h3>{selected.name}</h3><p>{selected.modeling.purpose}</p><p>{selected.modeling.composition}</p>
      <ResultTable table={{title:"사용 맵",summary:selected.maps_truncated?"처음 20개 맵":selected.maps.length+"개 맵",
        columns:["맵","원본 경로","사용 횟수"],rows:selected.maps.map(map=>[map.map,map.source_path,map.occurrences ?? "미확인"])}}/>
      {choose && <button onClick={()=>choose("빌보드 "+selected.name,selected.id)}>대화 입력에 추가</button>}
    </section>}
  </section>;
}
