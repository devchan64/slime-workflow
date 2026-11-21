import React, {useEffect, useRef, useState} from "react";

export default function WorldMap() {
  const [maps,setMaps]=useState([]);
  const [id,setId]=useState(new URLSearchParams(location.search).get("map"));
  const [error,setError]=useState("");
  const [revision,setRevision]=useState(0);
  const [zoom,setZoom]=useState(1);
  const viewport=useRef(null);
  useEffect(()=>{
    document.title="월드맵 검수";
    const controller=new AbortController();
    setMaps([]);setError("");
    fetch("/management/map-assets/world",{signal:controller.signal,cache:"no-store"})
      .then(async response=>{
        if(!response.ok) throw new Error("맵 원본 조회 실패 · HTTP "+response.status);
        const data=await response.json();
        if(!data.maps?.length) throw new Error("등록된 맵이 없습니다.");
        if(!controller.signal.aborted)setMaps(data.maps);
      }).catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});
    return ()=>controller.abort();
  },[revision]);
  const nodes=new Map(maps.map(node=>[node.id,node]));
  const selected=id ? nodes.get(id) : maps[0];
  const columns=maps.map(node=>node.column), rows=maps.map(node=>node.row);
  const left=Math.min(...columns),top=Math.min(...rows);
  const width=(Math.max(...columns)-left+1)*190,height=(Math.max(...rows)-top+1)*210;
  const x=node=>(node.column-left+.5)*190,y=node=>(node.row-top+.5)*210;
  function select(next) {
    setId(next);
    const url=new URL(location.href);url.searchParams.set("map",next);history.replaceState(null,"",url);
  }
  return <section style={{padding:"1rem"}}>
    <a href="/management/assistant/">헤르메스 대화</a><h1>월드맵 검수</h1>
    <button onClick={()=>setRevision(v=>v+1)}>원본 다시 불러오기</button>
    {error && <p role="alert">{error}</p>}
    {!maps.length && !error && <p>맵 원본 조회 중…</p>}
    {maps.length>0 && <>
      <p>검증 통과 · 맵 {maps.length}개 · 연결 {maps.reduce((n,node)=>n+node.connections.length,0)/2}개</p>
      <label>맵 선택 <select value={selected?.id || ""} onChange={e=>select(e.target.value)}>
        {!selected && <option value="">등록되지 않은 맵입니다. 맵을 선택하세요.</option>}
        {maps.map(node=><option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
      <button onClick={()=>setZoom(v=>Math.max(.1,v*.8))}>축소</button>
      <button onClick={()=>setZoom(v=>Math.min(2,v*1.25))}>확대</button>
      <button onClick={()=>setZoom(Math.min(1,viewport.current.clientWidth/width,innerHeight*.65/height))}>전체 보기</button>
      <div ref={viewport} tabIndex={0} aria-label="월드맵 스크롤" style={{overflow:"auto",maxHeight:"65vh"}}>
        <svg aria-label="전체 맵과 이동 연결" width={width*zoom} height={height*zoom} viewBox={`0 0 ${width} ${height}`}>
          {maps.flatMap(node=>node.connections.filter(edge=>node.id<edge.target).map(edge=>
            <line key={node.id+"/"+edge.target} x1={x(node)} y1={y(node)} x2={x(nodes.get(edge.target))} y2={y(nodes.get(edge.target))} stroke="currentColor"/>))}
          {maps.map(node=><a href={"?map="+encodeURIComponent(node.id)} key={node.id} onClick={e=>{e.preventDefault();select(node.id);}}>
            <title>{node.name} 선택</title><image href={node.thumbnail.url} x={x(node)-64} y={y(node)-92} width="128" height="128"/>
            <text x={x(node)} y={y(node)+56} textAnchor="middle" fill="currentColor">{node.name}</text>
            <text x={x(node)} y={y(node)+78} textAnchor="middle" fill="currentColor">{node.safeTown?"도시":"필드"} {selected?.id===node.id && "· 선택"}</text>
          </a>)}
        </svg>
      </div>
      {selected && <><h2>{selected.name}</h2><img src={selected.thumbnail.url} width="256" alt={selected.name+" 특징 썸네일"}/>
        <p>{selected.thumbnail.managementId} · {selected.thumbnail.version}</p><p>SHA-256 · {selected.thumbnail.sha256}</p><p>{selected.thumbnail.path}</p>
        <table><caption>선택 맵의 이동 연결</caption><thead><tr>{["연결 맵","방향","출발 웨이포인트","도착 웨이포인트"].map(label=><th key={label}>{label}</th>)}</tr></thead>
          <tbody>{selected.connections.map(edge=><tr key={edge.id}><td>{nodes.get(edge.target).name}</td><td>{edge.direction}</td><td>{edge.id}</td><td>{edge.targetWaypointId}</td></tr>)}</tbody></table>
      </>}
    </>}
  </section>;
}
