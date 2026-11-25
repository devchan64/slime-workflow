import React, {useEffect, useId, useRef, useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import RecoverableImage from "./RecoverableImage.jsx";
import {validWorldMap,worldMapLinks,worldMapDirectionLabel} from "./worldMapValidation.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {imageRetryUrl} from "./imageRetryUrl.mjs";
import {startImageLoadDeadline} from "./imageLoadDeadline.mjs";
import {choiceLabels} from "./choiceLabels.mjs";

export function WorldMapThumbnail({src,x,y,failed,onError,onLoad}) {
  return failed ? <g><rect x={x-64} y={y-92} width="128" height="128" fill="none" stroke="currentColor"/><text x={x} y={y-24} textAnchor="middle" fill="currentColor">미리보기 없음</text></g> : <image href={src} x={x-64} y={y-92} width="128" height="128" onError={onError} onLoad={onLoad}/>;
}

export function WorldMapMarker({node,label,x,y,selected,href,onSelect,revision}) {
  const [failed,setFailed]=useState(false),[loaded,setLoaded]=useState(false);
  const idCharacters=Array.from(node.id);
  const shortId=idCharacters.length>20 ? idCharacters.slice(0,19).join("")+"…" : node.id;
  const cancelDeadline=useRef(null);
  useEffect(()=>{
    if(loaded || failed)return;
    const cancel=startImageLoadDeadline(()=>setFailed(true));
    cancelDeadline.current=cancel;
    return ()=>{cancel();if(cancelDeadline.current===cancel)cancelDeadline.current=null;};
  },[loaded,failed]);
  return <a href={href} aria-label={label+" 선택"+(failed ? " · 미리보기 없음" : "")} aria-current={selected ? "true" : undefined} onClick={onSelect}>
    <title>{label} 선택</title><WorldMapThumbnail src={imageRetryUrl(node.thumbnail.url,revision)} x={x} y={y} failed={failed} onError={()=>{cancelDeadline.current?.();setFailed(true);}} onLoad={()=>{cancelDeadline.current?.();setLoaded(true);}}/>
    {selected && <rect className="world-map-selected-marker" x={x-69} y={y-97} width="138" height="138" fill="none" vectorEffect="non-scaling-stroke" aria-hidden="true"/>}
    <text x={x} y={y+56} textAnchor="middle" fill="currentColor">{node.name}</text>
    <text x={x} y={y+78} textAnchor="middle" fill="currentColor">{node.safeTown?"도시":"필드"} {selected && "· 선택"}</text>
    {label!==node.name && <text x={x} y={y+96} textAnchor="middle" fill="currentColor">{shortId}</text>}
  </a>;
}

export function WorldMapStatus({checkedAt,error,loading,loaded,mapCount}) {
  return <>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p role="alert">{error} {loaded && "아래는 마지막 조회 결과입니다."} 다시 불러오기를 시도하세요.</p>}
    {loading && <p role="status">맵 원본 조회 중… {loaded && "아래는 마지막 조회 결과입니다."}</p>}
    {loaded && mapCount===0 && <p>{loading || error ? "마지막으로 조회한 목록에 등록된 맵이 없습니다." : "등록된 맵이 없습니다. 맵을 등록한 뒤 원본을 다시 불러오세요."}</p>}
  </>;
}

export default function WorldMap() {
  const session = new URLSearchParams(location.search).get("session");
  const conversation = "/management/assistant/" + (session ? "?" + new URLSearchParams({session}) : "");
  const [maps,setMaps]=useState([]);
  const [id,setId]=useState(new URLSearchParams(location.search).get("map"));
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true),[loaded,setLoaded]=useState(false),[checkedAt,setCheckedAt]=useState(null);
  const [revision,setRevision]=useState(0);
  const [imageRevision,setImageRevision]=useState(0);
  const [zoom,setZoom]=useState(1);
  const viewportHelpId=useId(),selectionHelpId=useId();
  const viewport=useRef(null),selectRef=useRef(null),reloadRef=useRef(null),reloadPending=useRef(true),restoreReloadFocus=useRef(false),restoreMapFocus=useRef(false);
  useEffect(()=>{
    if(!loading && restoreReloadFocus.current){
      restoreReloadFocus.current=false;
      restoreLostFocus(document,reloadRef.current);
    }
  },[loading]);
  useEffect(()=>{
    if(!loading && restoreMapFocus.current){
      restoreMapFocus.current=false;
      restoreLostFocus(document,(maps.length ? selectRef : reloadRef).current);
    }
  },[maps,loading]);
  useEffect(()=>{
    document.title="월드맵 검수";
    const controller=new AbortController();let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reloadPending.current=true;setLoading(true);setError("");
    untilAborted((async()=>{
        const response=await untilAborted(fetch("/management/map-assets/world",{signal:controller.signal,cache:"no-store"}),controller.signal);
        if(!response.ok) throw new Error("맵 원본 조회 실패 · HTTP "+response.status);
        const data=await untilAborted(response.json(),controller.signal);
        if(!validWorldMap(data))throw new Error("월드맵 응답 형식을 확인할 수 없습니다.");
        return data;
      })(),controller.signal).then(data=>{if(active){restoreMapFocus.current=Boolean(viewport.current?.contains(document.activeElement));if(restoreMapFocus.current)restoreReloadFocus.current=false;setMaps(data.maps);setId(current=>current || data.maps[0]?.id || null);setImageRevision(value=>value+1);setLoaded(true);setCheckedAt(new Date());}})
      .catch(problem=>{if(active)setError(timedOut ? "맵 원본 조회 시간이 초과됐습니다." : requestErrorMessage(problem));})
      .finally(()=>{clearTimeout(timeout);if(active){reloadPending.current=false;setLoading(false);}});
    return ()=>{active=false;reloadPending.current=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  const nodes=new Map(maps.map(node=>[node.id,node]));
  const labels=new Map(choiceLabels(maps.map(node=>[node.name,node.id])));
  const links=worldMapLinks(maps);
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
    const url=new URL(location.href);url.searchParams.set("map",next);history.replaceState(history.state,"",url);
  }
  return <section className="world-map-review">
    <a href={conversation}>헤르메스 대화</a><h1>월드맵 검수</h1>
    <button ref={reloadRef} type="button" aria-disabled={loading} onClick={event=>{if(reloadPending.current)return;reloadPending.current=true;restoreReloadFocus.current=document.activeElement===event.currentTarget;setLoading(true);setRevision(v=>v+1);}}>{loading ? "원본 조회 중…" : "원본 다시 불러오기"}</button>
    <WorldMapStatus checkedAt={checkedAt} error={error} loading={loading} loaded={loaded} mapCount={maps.length}/>
    {maps.length>0 && <>
      <p>검증 통과 · 맵 {maps.length}개 · 지도 간 연결 {links.length}개</p>
      <label className="world-map-select">맵 선택 <select ref={selectRef} value={selected?.id || ""} aria-describedby={!selected ? selectionHelpId : undefined} onChange={e=>select(e.target.value)}>
        {!selected && <option value="" disabled>등록되지 않은 맵입니다. 맵을 선택하세요.</option>}
        {maps.map(node=><option key={node.id} value={node.id}>{labels.get(node.id)}</option>)}</select></label>
      {!selected && <p id={selectionHelpId} role="status">선택한 맵을 현재 목록에서 찾지 못했습니다. 목록에서 다른 맵을 선택하세요.</p>}
      <div className="ui-action-row" role="group" aria-label="월드맵 화면 조정">
        <button type="button" aria-disabled={zoom<=.1} title={zoom<=.1 ? "최소 배율입니다." : undefined} onClick={()=>setZoom(v=>Math.max(.1,v*.8))}>축소</button>
        <button type="button" aria-disabled={zoom>=2} title={zoom>=2 ? "최대 배율입니다." : undefined} onClick={()=>setZoom(v=>Math.min(2,v*1.25))}>확대</button>
        <button type="button" onClick={()=>setZoom(Math.max(.1,Math.min(1,viewport.current.clientWidth/width,innerHeight*.65/height)))}>전체 보기</button>
        <button type="button" disabled={!selected} aria-describedby={!selected ? selectionHelpId : undefined} onClick={()=>{const area=viewport.current;if(!area)return;area.scrollTo({left:x(selected)*zoom-area.clientWidth/2,top:y(selected)*zoom-area.clientHeight/2});area.scrollIntoView({block:"nearest"});area.focus({preventScroll:true});}}>선택 맵 보기</button>
        <output aria-live="polite">확대 {Math.round(zoom*100)}%{zoom<=.1 ? " · 최소 배율" : zoom>=2 ? " · 최대 배율" : ""}</output>
      </div>
      <p id={viewportHelpId}>지도 영역에 초점을 두고 방향키로 스크롤할 수 있습니다. 맵은 목록이나 지도에서 선택하세요. 미리보기가 없으면 원본을 다시 불러와 재시도하세요.</p>
      <div ref={viewport} className="world-map-viewport" role="region" tabIndex={0} aria-label="월드맵 스크롤" aria-describedby={viewportHelpId}>
        <svg aria-label="전체 맵과 이동 연결" width={width*zoom} height={height*zoom} viewBox={`0 0 ${width} ${height}`}>
          {links.map(([from,to])=>
            <line key={JSON.stringify([from,to])} x1={x(nodes.get(from))} y1={y(nodes.get(from))} x2={x(nodes.get(to))} y2={y(nodes.get(to))} stroke="currentColor"/>)}
          {maps.map(node=><WorldMapMarker key={JSON.stringify([node.id,node.thumbnail.url,imageRevision])} node={node} label={labels.get(node.id)} x={x(node)} y={y(node)} selected={selected?.id===node.id} href={mapUrl(node.id)} revision={imageRevision} onSelect={e=>{if(e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)return;e.preventDefault();select(node.id);}}/>)}
        </svg>
      </div>
      {selected && <><h2>{labels.get(selected.id)}</h2><div className="world-map-thumbnail"><RecoverableImage src={selected.thumbnail.url} name={labels.get(selected.id)+" 특징"} kind="썸네일"/></div>
        <p>{selected.thumbnail.managementId} · {selected.thumbnail.version}</p><p>SHA-256 · {selected.thumbnail.sha256}</p><p>{selected.thumbnail.path}</p>
        <div className="world-map-connections"><ResultTable table={{title:"선택 맵의 이동 연결",emptyMessage:"이 맵에 등록된 이동 연결이 없습니다.",columns:["연결 맵","방향","출발 웨이포인트","도착 웨이포인트"],rows:selected.connections.map(edge=>[labels.get(edge.target),worldMapDirectionLabel(edge.direction),edge.id,edge.targetWaypointId ?? "없음"])}}/></div>
      </>}
    </>}
  </section>;
}
