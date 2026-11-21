import React,{useEffect,useState} from "react";

import {managementCommand} from "./managementCommand.js";

export default function MapReview(){
  const field=location.pathname.replace(/\/$/,"").endsWith("/field-map");
  const title=field?"야외필드":"도시맵";
  const [cell,setCell]=useState(null),[reading,setReading]=useState(false);
  const [source,setSource]=useState(null),[draft,setDraft]=useState(null),[preview,setPreview]=useState(null);
  const [past,setPast]=useState([]),[future,setFuture]=useState([]);
  const [texture,setTexture]=useState(""),[objectId,setObjectId]=useState("");
  const [editing,setEditing]=useState(false);
  const [wall,setWall]=useState("");
  const [floor,setFloor]=useState("");
  const [brush,setBrush]=useState("pan"),[strokeCount,setStrokeCount]=useState(0);
  const [storageNotice,setStorageNotice]=useState("");
  const [recovery,setRecovery]=useState(null);
  function downloadDraft(map,text){
    const url=URL.createObjectURL(new Blob([text],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download=map+"-draft.json";
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function importDraft(file){
    if(!file)return;
    setReading(true);
    try{
      const record=JSON.parse(await file.text());
      const next=record.version===1?record.state?.draft:record;
      if(next?.map!==draft.map || next.revision!==draft.revision)throw new Error("현재 지도와 원본 리비전이 일치하는 초안을 선택하세요.");
      await applyDraft(next,"import");
    }catch(error){setFeedback(error.message);}
    finally{setReading(false);}
  }
  async function discardDraft(){
    if(!window.confirm("현재 지도의 미저장 초안과 편집 이력을 버릴까요?"))return;
    setReading(true);
    try{
      const fresh=await managementCommand("map-assets","map-edit-load",{map:draft.map});
      await window.mapReviewApplyDraft(fresh.render);
      sessionStorage.removeItem(storageKey(draft.map));
      setCell(null);setSource(null);setDraft(null);setPreview(null);
      setPast([]);setFuture([]);setBrush("pan");setStorageNotice("");setFeedback("지도 원본을 다시 불러왔습니다.");
    }catch(error){setFeedback(error.message);}
    finally{setReading(false);}
  }
  function discardRecovery(){
    try{
      if(sessionStorage.getItem(storageKey(recovery.map))!==recovery.raw){
        setFeedback("임시본이 변경되었습니다. 셀을 다시 조회하세요.");return;
      }
      sessionStorage.removeItem(storageKey(recovery.map));setRecovery(null);
      setFeedback("임시본을 삭제했습니다. 셀을 다시 조회해 현재 원본으로 시작하세요.");
    }catch(error){setFeedback(error.message);}
  }
  const storageKey=map=>"slime-map-editor-draft-v1:"+map;
  useEffect(()=>{
    if(!draft || (!past.length && !future.length))return;
    try{
      sessionStorage.setItem(storageKey(draft.map),JSON.stringify({version:1,savedAt:new Date().toISOString(),
        state:{snapshot:source,draft,history:past,future}}));
      setStorageNotice("현재 탭에 초안과 편집 이력을 보관했습니다.");
    }catch(error){setStorageNotice("탭 임시저장 실패 · "+error.message);}
  },[draft,past,future,source]);
  const placed=draft?.objects || [];
  const atCell=item=>cell && item.position.column===cell.column && item.position.row===cell.row;
  const selectedObject=placed.find(item=>item.id===objectId);
  function makeBillboard(objects,column,row,textureKey){
    const ids=new Set(objects.map(item=>item.id));
    let number=1;
    while(ids.has("editor-billboard-"+number))number++;
    return {id:"editor-billboard-"+number,kind:"decoration",textureKey,tileAnchor:"center",position:{column,row}};
  }
  function addObject(){
    const object=makeBillboard(placed,cell.column,cell.row,texture);
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
    const next={...draft,cells:[...cells,{column,row,tile,height:Number(height),blocked,...(cell.wall?{wall:cell.wall}:{})}]};
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
        if(action==="import")setCell(null);
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
      try{sessionStorage.removeItem(storageKey(draft.map));setStorageNotice("");}
      catch(error){setStorageNotice("임시본 정리 실패 · "+error.message);}
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
      let current=draft;
      if(!current){
        let raw;
        try{raw=sessionStorage.getItem(storageKey(map));}
        catch(error){setStorageNotice("탭 임시저장을 사용할 수 없습니다. "+error.message);}
        setRecovery(null);
        if(raw){
          setRecovery({map,raw});
          const saved=JSON.parse(raw),state=saved.state;
          if(saved.version!==1 || !Array.isArray(state?.history) || !Array.isArray(state.future) ||
            ![state.draft,...state.history,...state.future].every(item=>item?.map===map && item.revision===snapshot.revision &&
              Array.isArray(item.cells) && Array.isArray(item.objects)))throw new Error("원본 리비전 또는 임시본 형식이 달라 복원할 수 없습니다.");
          const checked=await managementCommand("map-assets","map-edit-preview",state.draft);
          await window.mapReviewApplyDraft(checked.render);
          setRecovery(null);current=state.draft;setPast(state.history);setFuture(state.future);setPreview(checked);
        }else current={map,revision:snapshot.revision,cells:[],
        objects:snapshot.tiles.objects.filter(item=>item.kind==="decoration"),
        ...(snapshot.terrain.terrainEffects?{terrainEffects:snapshot.terrain.terrainEffects}:{})};
        setDraft(current);
      }
      const {column,row}=selected;
      const tile=snapshot.tiles.rows[row][column];
      setCell({column,row,tile,height:snapshot.terrain.elevations[row][column],
        blocked:snapshot.terrain.blocked.some(([x,y])=>x===column && y===row),
        ...current.cells.find(item=>item.column===column && item.row===row)});
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
  useEffect(()=>{
    if(!field || !ready)return;
    const receive=()=>setStrokeCount(value=>value+1);
    window.addEventListener("map-editor-brush",receive);
    return ()=>window.removeEventListener("map-editor-brush",receive);
  },[field,ready]);
  useEffect(()=>{
    if(!field || !ready)return;
    window.mapReviewBrushTool=draft?brush:"pan";
    window.mapReviewBrushTexture=texture;window.mapReviewBrushTile=floor;window.mapReviewBrushWall=wall;
  },[field,ready,brush,draft,floor,wall,texture]);
  useEffect(()=>{
    const queue=window.mapReviewBrushQueue;
    if(reading || !draft || !queue?.length)return;
    const stroke=queue.shift();
    try{
      const cells=new Map(draft.cells.map(item=>[[item.column,item.row].join(","),item]));
      let objects=[...draft.objects];
      for(const {column,row,tool,tile,wall:wallTile,texture:asset,object:id} of stroke){
        if(tool==="place"){
          if(!source.textures.includes(asset))throw new Error("배치할 빌보드 에셋을 선택하세요.");
          objects.push(makeBillboard(objects,column,row,asset));
          continue;
        }
        if(tool==="delete"){
          objects=objects.filter(item=>item.id!==id);
          continue;
        }
        if(!["raise","lower","floor","wall"].includes(tool))throw new Error("지원하지 않는 지도 브러시입니다.");
        const key=[column,row].join(",");
        const current=cells.get(key) || {column,row,tile:source.tiles.rows[row][column],
          height:source.terrain.elevations[row][column],
          blocked:source.terrain.blocked.some(([x,y])=>x===column && y===row)};
        if(tool==="wall"){
          if(!source.wall_tiles?.includes(wallTile))throw new Error("벽면 타일을 선택하세요.");
          cells.set(key,{...current,wall:wallTile});
          continue;
        }
        if(tool==="floor"){
          if(!Object.hasOwn(source.codes,tile))throw new Error("바닥 브러시용 타일을 선택하세요.");
          cells.set(key,{...current,tile,blocked:current.blocked || source.blocked_tile_codes.includes(tile)});
          continue;
        }
        const height=current.height+(tool==="raise"?1:-1);
        if(height<0 || height>20)throw new Error("높이는 0~20 범위입니다.");
        cells.set(key,{...current,height});
      }
      setCell(null);
      applyDraft({...draft,objects,cells:[...cells.values()]},"edit").finally(()=>{
        window.mapReviewBrushBusy=false;window.mapReviewFlushBrushQueue?.();
      });
    }catch(error){
      setFeedback(error.message);window.mapReviewBrushBusy=false;window.mapReviewFlushBrushQueue?.();
    }
  },[strokeCount,reading,draft]);
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
      <section hidden={field}><label>건물 선택<select id="building"><option value="">건물 선택</option></select></label></section>
      {[["zoom-out","축소"],["zoom-in","확대"],["actual-size","사람 중심 · 100%"],["fit","전체 보기"]].map(([id,label])=><button key={id} id={id}>{label}</button>)}
      <output id="zoom-level" aria-live="polite"/>
      {[["show-character","기본 캐릭터",true],["show-safe-boundary","결계탑 · 결계 오러",true],["edges","메시 경계",false],["tile-edges","타일 경계",false],["blocked-areas","이동금지 영역",false]].map(([id,label,checked])=>
        <label key={id}><input type="checkbox" id={id} defaultChecked={checked} onChange={()=>window.mapReviewDisplayOptions(...["show-character","show-safe-boundary","edges"].map(key=>document.getElementById(key).checked),"contrast",document.getElementById("tile-edges").checked,document.getElementById("blocked-areas").checked)}/>{label}</label>)}
      <button onClick={exportImage}>전체 맵 PNG 내보내기</button><a id="map-export-download" hidden>PNG 다운로드</a>
    </fieldset>
    <p role="status" id="status">지도를 불러오는 중입니다.</p>{feedback && <p role="status">{feedback}</p>}
    {field && <fieldset disabled={!ready || reading}><legend>셀 검수</legend>
      <label><input type="checkbox" onChange={event=>{window.mapReviewEditingEnabled=event.target.checked;setEditing(event.target.checked);setBrush("pan");window.mapReviewSelectedCell=null;setCell(null);}}/>캐릭터 이동 대신 셀 선택</label>
      <button onClick={inspectCell}>선택 셀 속성 조회</button>
      {cell && <form onSubmit={previewCell}><p>열 {cell.column} · 행 {cell.row} · {cell.tile} · 높이 {cell.height} · {cell.blocked?"이동 금지":"이동 가능"} · 배치물 {placed.filter(atCell).map(item=>item.id).join(", ") || "없음"}</p>
        <label>지형<select value={cell.tile} onChange={e=>editCell("tile",e.target.value)}>
          {Object.entries(source.codes).map(([code,name])=><option key={code} value={code}>{name} · {code}</option>)}</select></label>
        <label>높이<input type="number" required min="0" max="20" step="1" value={cell.height} onChange={e=>editCell("height",e.target.value)}/></label>
        <label><input type="checkbox" checked={cell.blocked} onChange={e=>editCell("blocked",e.target.checked)}/>이동 금지</label>
        <button>초안 검증 및 미리보기</button></form>}
      {recovery && <section aria-label="임시본 복구"><p>복원하지 못한 임시본을 파일로 보관하거나 삭제할 수 있습니다.</p>
        <button onClick={()=>downloadDraft(recovery.map,recovery.raw)}>임시본 JSON 다운로드</button>
        <button onClick={()=>{if(window.confirm("이 탭에 보관한 "+recovery.map+" 임시본을 삭제할까요?"))discardRecovery();}}>임시본 삭제</button>
      </section>}
      {draft && <details><summary>초안 보관 및 복원</summary>
        <button onClick={()=>downloadDraft(draft.map,JSON.stringify(draft,null,2))}>초안 JSON 다운로드</button>
        <label>초안 JSON 불러오기<input type="file" accept=".json,application/json" onChange={event=>{
          const file=event.target.files[0];event.target.value="";importDraft(file);
        }}/></label>
        <button onClick={discardDraft}>초안 버리고 원본 다시 읽기</button>
      </details>}
      {storageNotice && <p role="status">{storageNotice}</p>}
      {draft && <label>지도 드래그 도구<select value={brush} disabled={!editing} onChange={e=>setBrush(e.target.value)}>
        <option value="pan">이동·셀 선택</option><option value="floor" disabled={!source?.blocked_tile_codes}>바닥 칠하기</option><option value="wall" disabled={!source?.wall_tiles?.length}>벽면 칠하기</option><option value="raise">높이 올리기</option><option value="lower">높이 내리기</option><option value="place">빌보드 배치</option><option value="delete">빌보드 삭제</option>
      </select></label>}
      {draft && brush==="wall" && <label>브러시 벽면 타일<select value={wall} onChange={e=>setWall(e.target.value)}>
        <option value="">타일 선택</option>{source.wall_tiles.map(key=><option key={key}>{key}</option>)}
      </select></label>}
      {draft && brush==="floor" && <label>브러시 바닥 타일<select value={floor} onChange={e=>setFloor(e.target.value)}>
        <option value="">타일 선택</option>{Object.entries(source.codes).map(([code,name])=><option key={code} value={code}>{name} · {code}</option>)}
      </select></label>}
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
