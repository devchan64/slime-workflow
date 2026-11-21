import React,{useEffect,useState} from "react";

import {managementCommand} from "./managementCommand.js";

export default function MapReview(){
  const field=location.pathname.replace(/\/$/,"").endsWith("/field-map");
  const title=field?"야외필드":"도시맵";
  const [cell,setCell]=useState(null),[reading,setReading]=useState(false);
  const [source,setSource]=useState(null),[draft,setDraft]=useState(null),[preview,setPreview]=useState(null);
  const [past,setPast]=useState([]),[future,setFuture]=useState([]);
  const [texture,setTexture]=useState(""),[objectId,setObjectId]=useState("");
  const placed=draft?.objects || [];
  const atCell=item=>cell && item.position.column===cell.column && item.position.row===cell.row;
  const selectedObject=placed.find(item=>item.id===objectId);
  function addObject(){
    const ids=new Set(placed.map(item=>item.id));
    let number=1;
    while(ids.has("editor-billboard-"+number))number++;
    const object={id:"editor-billboard-"+number,kind:"decoration",textureKey:texture,tileAnchor:"center",
      position:{column:cell.column,row:cell.row}};
    applyDraft({...draft,objects:[...placed,object]},"edit");
  }
  function moveObject(){
    const objects=placed.map(item=>item.id===objectId?{...item,position:{column:cell.column,row:cell.row}}:item);
    applyDraft({...draft,objects},"edit");
  }
  function editCell(key,value){
    setCell({...cell,[key]:value});setPreview(null);
  }
  async function previewCell(event){
    event.preventDefault();
    const {column,row,tile,height,blocked}=cell;
    const cells=draft.cells.filter(item=>item.column!==column || item.row!==row);
    const next={...draft,cells:[...cells,{column,row,tile,height:Number(height),blocked}]};
    await applyDraft(next,"edit");
  }
  async function applyDraft(next,action){
    setReading(true);setPreview(null);
    try{
      const result=await managementCommand("map-assets","map-edit-preview",next);
      await window.mapReviewApplyDraft(result.render);
      if(action==="undo"){
        setPast(past.slice(0,-1));setFuture([...future,draft]);setCell(null);
      }else if(action==="redo"){
        setFuture(future.slice(0,-1));setPast([...past,draft]);setCell(null);
      }else{
        setPast([...past,draft]);setFuture([]);
      }
      setDraft(next);setPreview(result);
      setFeedback("검증 완료 · 변경 셀 "+result.cells+"개 · 도달 가능 "+result.reachable+"칸");
    }catch(error){setFeedback(error.message);}
    finally{setReading(false);}
  }
  async function save(){
    if(!preview?.changed || !preview.save_available || !preview.token)return;
    setReading(true);setPreview(null);
    try{
      const result=await managementCommand("map-assets","map-edit-save",{...draft,token:preview.token});
      if(result.map!==draft.map || result.saved!==true)throw new Error("저장 결과를 확인할 수 없습니다.");
      setPast([]);setFuture([]);setCell(null);setSource(null);setDraft(null);setFeedback(result.map+" 저장 완료");
    }catch(error){setFeedback(error.message+" · 저장 상태를 확인하세요.");}
    finally{setReading(false);}
  }
  async function inspectCell(){
    const selected=window.mapReviewSelectedCell;
    if(!selected){setFeedback("지도에서 셀을 선택하세요.");return;}
    setReading(true);setCell(null);
    try{
      const map=window.mapReviewControlOptions().selected;
      const snapshot=source || await managementCommand("map-assets","map-edit-load",{map});
      setSource(snapshot);
      if(!draft)setDraft({map,revision:snapshot.revision,cells:[],
        objects:snapshot.tiles.objects.filter(item=>item.kind==="decoration"),
        ...(snapshot.terrain.terrainEffects?{terrainEffects:snapshot.terrain.terrainEffects}:{})});
      const {column,row}=selected;
      const tile=snapshot.tiles.rows[row][column];
      setCell({column,row,tile,height:snapshot.terrain.elevations[row][column],
        blocked:snapshot.terrain.blocked.some(([x,y])=>x===column && y===row),
        ...draft?.cells.find(item=>item.column===column && item.row===row)});
      setFeedback("");
    }catch(error){setFeedback(error.message);}
    finally{setReading(false);}
  }
  const [ready,setReady]=useState(false),[feedback,setFeedback]=useState("");
  useEffect(()=>{
    let active=true;
    const url=new URL(location.href);
    url.searchParams.set("mapKind",field?"field":"town");
    history.replaceState(null,"",url);
    import(new URL("/isloon-map-review/block-map-review.js",location.origin).href).then(()=>{
      if(active)setReady(true);
    }).catch(error=>{if(active)setFeedback(error.message);});
    return ()=>{active=false;};
  },[]);
  const destination=kind=>{
    const url=new URL(location.href);
    url.pathname="/management/frame/map-review/";
    url.searchParams.delete("map");url.searchParams.set("mapKind",kind);
    return url.href;
  };
  async function exportImage(){
    try{setFeedback(await window.mapReviewExportImage());}
    catch(error){setFeedback(error.message);}
  }
  return <article><nav><a href={destination(field?"town":"field")}>{field?"도시맵":"야외필드"} 검수</a> · <a href={destination("battle")}>전투필드 검수</a></nav>
    <h1 id="map-title">{title} 검수</h1>
    <fieldset disabled={!ready}><legend>지도와 시점</legend>
      <label>맵 선택<select id="map-select"/></label><button id="load-map">맵 불러오기</button>
      <label>건물 선택<select id="building"><option value="">건물 선택</option></select></label>
      {[["zoom-out","축소"],["zoom-in","확대"],["actual-size","사람 중심 · 100%"],["fit","전체 보기"]].map(([id,label])=><button key={id} id={id}>{label}</button>)}
      <output id="zoom-level" aria-live="polite"/>
      {[["show-character","기본 캐릭터",true],["show-safe-boundary","결계탑 · 결계 오러",true],["edges","메시 경계",false],["tile-edges","타일 경계",false],["blocked-areas","이동금지 영역",false]].map(([id,label,checked])=>
        <label key={id}><input type="checkbox" id={id} defaultChecked={checked} onChange={()=>window.mapReviewDisplayOptions(...["show-character","show-safe-boundary","edges"].map(key=>document.getElementById(key).checked),"contrast",document.getElementById("tile-edges").checked,document.getElementById("blocked-areas").checked)}/>{label}</label>)}
      <button onClick={exportImage}>전체 맵 PNG 내보내기</button><a id="map-export-download" hidden>PNG 다운로드</a>
    </fieldset>
    <p role="status" id="status">지도를 불러오는 중입니다.</p>{feedback && <p role="status">{feedback}</p>}
    {field && <fieldset disabled={!ready || reading}><legend>셀 검수</legend>
      <label><input type="checkbox" onChange={event=>{window.mapReviewEditingEnabled=event.target.checked;window.mapReviewSelectedCell=null;setCell(null);}}/>캐릭터 이동 대신 셀 선택</label>
      <button onClick={inspectCell}>선택 셀 속성 조회</button>
      {cell && <form onSubmit={previewCell}><p>열 {cell.column} · 행 {cell.row} · {cell.tile} · 높이 {cell.height} · {cell.blocked?"이동 금지":"이동 가능"} · 배치물 {placed.filter(atCell).map(item=>item.id).join(", ") || "없음"}</p>
        <label>지형<select value={cell.tile} onChange={e=>editCell("tile",e.target.value)}>
          {Object.entries(source.codes).map(([code,name])=><option key={code} value={code}>{name} · {code}</option>)}</select></label>
        <label>높이<input type="number" required min="0" max="20" step="1" value={cell.height} onChange={e=>editCell("height",e.target.value)}/></label>
        <label><input type="checkbox" checked={cell.blocked} onChange={e=>editCell("blocked",e.target.checked)}/>이동 금지</label>
        <button>초안 검증 및 미리보기</button></form>}
      {draft && <fieldset><legend>빌보드 배치</legend>
        <label>추가할 에셋<select value={texture} onChange={e=>setTexture(e.target.value)}>
          <option value="">에셋 선택</option>{(source.textures || []).map(key=><option key={key}>{key}</option>)}</select></label>
        <button disabled={!cell || !source.textures?.includes(texture)} onClick={addObject}>선택 셀에 추가</button>
        <label>배치 ID<select value={selectedObject?.id || ""} onChange={e=>setObjectId(e.target.value)}>
          <option value="">배치 선택</option>{placed.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
        <button disabled={!selectedObject || !cell || atCell(selectedObject)} onClick={moveObject}>선택 셀로 이동</button>
        <button disabled={!selectedObject} onClick={()=>applyDraft({...draft,objects:placed.filter(item=>item.id!==objectId)},"edit")}>선택 배치 삭제</button>
        <button disabled={!placed.some(atCell)} onClick={()=>applyDraft({...draft,objects:placed.filter(item=>!atCell(item))},"edit")}>선택 셀의 빌보드 모두 삭제</button>
      </fieldset>}
      {draft && <div>
        <button disabled={!past.length} onClick={()=>applyDraft(past[past.length-1],"undo")}>한 단계 되돌리기</button>
        <button disabled={!future.length} onClick={()=>applyDraft(future[future.length-1],"redo")}>한 단계 다시 실행</button>
        <span>편집 이력 {past.length} / {past.length+future.length}단계</span>
      </div>}
      {preview && <button disabled={!preview.changed || !preview.save_available || !preview.token} onClick={save}>검증된 초안 저장</button>}
    </fieldset>}
    <canvas id="map" width="768" height="576" tabIndex="0" aria-label={title+" · 방향키로 이동"} style={{width:"100%",aspectRatio:"4/3",touchAction:"none"}}/>
    {[["tile","지형 타일"],["building","건물 스프라이트"],["billboard","빌보드"],["structure","결계·경비 구조물"]].map(([id,label])=>
      <details key={id}><summary>{label} 원본</summary><div id={"applied-"+id+"-list"}/></details>)}
  </article>;
}
