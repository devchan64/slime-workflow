import React, {useEffect, useRef, useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import {validWorldMap} from "./worldMapValidation.mjs";

export default function WorldMap() {
  const session = new URLSearchParams(location.search).get("session");
  const conversation = "/management/assistant/" + (session ? "?" + new URLSearchParams({session}) : "");
  const [maps,setMaps]=useState([]);
  const [id,setId]=useState(new URLSearchParams(location.search).get("map"));
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[loaded,setLoaded]=useState(false),[checkedAt,setCheckedAt]=useState(null);
  const [revision,setRevision]=useState(0);
  const [zoom,setZoom]=useState(1);
  const viewport=useRef(null);
  useEffect(()=>{
    document.title="월드맵 검수";
    const controller=new AbortController();let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    untilAborted((async()=>{
        const response=await fetch("/management/map-assets/world",{signal:controller.signal,cache:"no-store"});
        if(!response.ok) throw new Error("맵 원본 조회 실패 · HTTP "+response.status);
        const data=await response.json();
        if(!validWorldMap(data))throw new Error("월드맵 응답 형식을 확인할 수 없습니다.");
        return data;
      })(),controller.signal).then(data=>{if(active){setMaps(data.maps);setLoaded(true);setCheckedAt(new Date());}})
      .catch(problem=>{if(active)setError(timedOut ? "맵 원본 조회 시간이 초과됐습니다." : requestErrorMessage(problem));})
      .finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  const nodes=new Map(maps.map(node=>[node.id,node]));
  const selected=id ? nodes.get(id) : maps[0];
  const columns=maps.map(node=>node.column), rows=maps.map(node=>node.row);
  const left=Math.min(...columns),top=Math.min(...rows);
  const width=(Math.max(...columns)-left+1)*190,height=(Math.max(...rows)-top+1)*210;
  const x=node=>(node.column-left+.5)*190,y=node=>(node.row-top+.5)*210;
  function mapUrl(next){
    const url=new URL(location.href);url.searchParams.set("map",next);return url.href;
  }
  function select(next) {
    setId(next);
    const url=new URL(location.href);url.searchParams.set("map",next);history.replaceState(null,"",url);
  }
  return <section style={{padding:"1rem"}}>
    <a href={conversation}>헤르메스 대화</a><h1>월드맵 검수</h1>
    <button disabled={loading} onClick={()=>setRevision(v=>v+1)}>{loading ? "원본 조회 중…" : "원본 다시 불러오기"}</button>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p role="alert">{error} {loaded && "아래는 마지막 조회 결과입니다."} 다시 불러오기를 시도하세요.</p>}
    {loading && <p role="status">맵 원본 조회 중… {loaded && "아래는 마지막 조회 결과입니다."}</p>}
    {loaded && !maps.length && !error && <p>등록된 맵이 없습니다.</p>}
    {maps.length>0 && <>
      <p>검증 통과 · 맵 {maps.length}개 · 연결 {maps.reduce((n,node)=>n+node.connections.length,0)/2}개</p>
      <label>맵 선택 <select value={selected?.id || ""} onChange={e=>select(e.target.value)}>
        {!selected && <option value="">등록되지 않은 맵입니다. 맵을 선택하세요.</option>}
        {maps.map(node=><option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
      {!selected && <p role="status">주소에 지정된 맵을 찾지 못했습니다. 목록에서 맵을 선택하세요.</p>}
      <button onClick={()=>setZoom(v=>Math.max(.1,v*.8))}>축소</button>
      <button onClick={()=>setZoom(v=>Math.min(2,v*1.25))}>확대</button>
      <button onClick={()=>setZoom(Math.max(.1,Math.min(1,viewport.current.clientWidth/width,innerHeight*.65/height)))}>전체 보기</button>
      <output aria-live="polite">확대 {Math.round(zoom*100)}%</output>
      <div ref={viewport} role="region" tabIndex={0} aria-label="월드맵 스크롤" style={{overflow:"auto",maxHeight:"65vh"}}>
        <svg aria-label="전체 맵과 이동 연결" width={width*zoom} height={height*zoom} viewBox={`0 0 ${width} ${height}`}>
          {maps.flatMap(node=>node.connections.filter(edge=>node.id<edge.target).map(edge=>
            <line key={node.id+"/"+edge.target} x1={x(node)} y1={y(node)} x2={x(nodes.get(edge.target))} y2={y(nodes.get(edge.target))} stroke="currentColor"/>))}
          {maps.map(node=><a href={mapUrl(node.id)} key={node.id} aria-label={node.name+" 선택"} aria-current={selected?.id===node.id ? "true" : undefined} onClick={e=>{if(e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)return;e.preventDefault();select(node.id);}}>
            <title>{node.name} 선택</title><image href={node.thumbnail.url} x={x(node)-64} y={y(node)-92} width="128" height="128"/>
            <text x={x(node)} y={y(node)+56} textAnchor="middle" fill="currentColor">{node.name}</text>
            <text x={x(node)} y={y(node)+78} textAnchor="middle" fill="currentColor">{node.safeTown?"도시":"필드"} {selected?.id===node.id && "· 선택"}</text>
          </a>)}
        </svg>
      </div>
      {selected && <><h2>{selected.name}</h2><img src={selected.thumbnail.url} width="256" alt={selected.name+" 특징 썸네일"}/>
        <p>{selected.thumbnail.managementId} · {selected.thumbnail.version}</p><p>SHA-256 · {selected.thumbnail.sha256}</p><p>{selected.thumbnail.path}</p>
        <div className="world-map-connections" role="region" aria-label="선택 맵의 이동 연결" tabIndex={0}><ResultTable table={{title:"선택 맵의 이동 연결",columns:["연결 맵","방향","출발 웨이포인트","도착 웨이포인트"],rows:selected.connections.map(edge=>[nodes.get(edge.target).name,edge.direction,edge.id,edge.targetWaypointId ?? "없음"])}}/></div>
      </>}
    </>}
  </section>;
}
