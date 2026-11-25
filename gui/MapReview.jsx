import React,{useEffect,useId,useRef,useState} from "react";

import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {progressDeadline} from "./progressDeadline.mjs";
import ActionButton from "./ActionButton.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {validMapDraftPreview,mapDraftSaveReason,isMapCellDirty,invalidMapCellHeight,readMapCell} from "./mapDraftPreview.mjs";

export function MapDraftFileInput({cellDirty,error,onFile,inputRef}){
  return <><label>초안 JSON 불러오기<input ref={inputRef} type="file" accept=".json,application/json" disabled={cellDirty} aria-invalid={error ? true : undefined} aria-describedby={[cellDirty && "map-cell-pending-reason",error && "map-import-error"].filter(Boolean).join(" ") || undefined} onChange={event=>{
    const file=event.target.files[0],focused=event.currentTarget===document.activeElement;event.target.value="";onFile(file,focused);
  }}/></label>{error && <p id="map-import-error" role="alert">{error}</p>}</>;
}

export function MapCoordinateInput({axis,value,onChange}){
  const errorId=useId();
  const invalid=value.trim()==="" || !Number.isInteger(Number(value)) || Number(value)<0;
  return <div><label>셀 {axis} (0부터 시작)<input type="number" required min="0" step="1" value={value} aria-invalid={invalid || undefined} aria-describedby={invalid ? errorId : undefined} onChange={event=>onChange(event.target.value)}/></label>{invalid && <small id={errorId}>0 이상의 정수를 입력하세요.</small>}</div>;
}

export function MapReviewNavigation({field,destination,onNavigate,saving,cellDirty,unsafeAutosave}){
  const help=[saving && "map-saving-status",cellDirty && "map-cell-pending-reason",unsafeAutosave && "map-storage-failure"].filter(Boolean).join(" ") || undefined;
  return <nav aria-label="지도 검수 이동"><a href={destination(field?"town":"field")} onClick={onNavigate} aria-describedby={help}>{field?"도시맵":"야외필드"} 검수</a> · <a href={destination("battle")} onClick={onNavigate} aria-describedby={help}>전투필드 검수</a></nav>;
}

export default function MapReview(){
  const field=location.pathname.replace(/\/$/,"").endsWith("/field-map");
  const title=field?"야외필드":"도시맵";
  const [cell,setCell]=useState(null),[reading,setReading]=useState(false);
  const heightErrorId=useId();
  const [cellOriginal,setCellOriginal]=useState(null);
  const [source,setSource]=useState(null),[draft,setDraft]=useState(null),[preview,setPreview]=useState(null);
  const [past,setPast]=useState([]),[future,setFuture]=useState([]);
  const [texture,setTexture]=useState(""),[objectId,setObjectId]=useState("");
  const [cellColumn,setCellColumn]=useState("0"),[cellRow,setCellRow]=useState("0");
  const [editing,setEditing]=useState(false);
  const [wall,setWall]=useState("");
  const [floor,setFloor]=useState("");
  const [brush,setBrush]=useState("pan"),[strokeCount,setStrokeCount]=useState(0);
  const [storageNotice,setStorageNotice]=useState("");
  const [saving,setSaving]=useState(false);
  const [saveUncertain,setSaveUncertain]=useState(false);
  const [storageFailed,setStorageFailed]=useState(false);
  const [importError,setImportError]=useState("");
  const [recovery,setRecovery]=useState(null);
  const readRequest=useRef(null),importRequest=useRef(null),savingRef=useRef(false),cellFormRef=useRef(null),feedbackRef=useRef(null),restorePreviewFocus=useRef(false),importInputRef=useRef(null),restoreImportFocus=useRef(false),discardedRecovery=useRef(new Set());
  useEffect(()=>()=>{readRequest.current?.abort();importRequest.current?.abort();},[]);
  async function readMap(command,payload){
    const controller=new AbortController();readRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{return await untilAborted(managementCommand("map-assets",command,payload,{signal:controller.signal}),controller.signal);}
    catch(problem){if(timedOut)throw new Error("지도 조회 또는 초안 검증 시간이 초과됐습니다. 다시 시도하세요.");throw problem;}
    finally{clearTimeout(timeout);if(readRequest.current===controller)readRequest.current=null;}
  }
  async function applyMapPreview(render){
    const controller=new AbortController();readRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{await untilAborted(window.mapReviewApplyDraft(render,{signal:controller.signal}),controller.signal);}
    catch(error){if(timedOut)throw new Error("지도 미리보기 적용 시간이 초과됐습니다. 다시 시도하세요.");throw error;}
    finally{clearTimeout(timeout);if(readRequest.current===controller)readRequest.current=null;}
  }
  function downloadDraft(map,text){
    const url=URL.createObjectURL(new Blob([text],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download=map+"-draft.json";
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function importDraft(file,focused=false){
    if(!file || importRequest.current || readRequest.current || savingRef.current)return;
    restoreImportFocus.current=focused;
    const controller=new AbortController();importRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setImportError("");setReading(true);
    try{
      const text=await untilAborted(file.text(),controller.signal);
      clearTimeout(timeout);
      let record;
      try{record=JSON.parse(text);}catch{throw new Error("올바른 JSON 초안 파일을 선택하세요.");}
      if(!record || typeof record!=="object" || Array.isArray(record))throw new Error("올바른 JSON 초안 파일을 선택하세요.");
      const next=record.version===1?record.state?.draft:record;
      if(next?.map!==draft.map || next.revision!==draft.revision)throw new Error("현재 지도와 원본 리비전이 일치하는 초안을 선택하세요.");
      if(controller.signal.aborted)return;
      await applyDraft(next,"import");
    }catch(error){if(timedOut)setImportError("초안 파일 읽기 시간이 초과됐습니다. 파일을 다시 선택하세요.");else if(!controller.signal.aborted)setImportError(requestErrorMessage(error));}
    finally{clearTimeout(timeout);if(importRequest.current===controller)importRequest.current=null;if(!controller.signal.aborted || timedOut)setReading(false);}
  }
  async function discardDraft(){
    if(!window.confirm("현재 지도의 미저장 초안과 편집 이력을 버릴까요?"))return;
    setReading(true);
    try{
      const fresh=await readMap("map-edit-load",{map:draft.map});
      await applyMapPreview(fresh.render);
      let storageError="";
      try{sessionStorage.removeItem(storageKey(draft.map));discardedRecovery.current.delete(draft.map);}
      catch(error){discardedRecovery.current.add(draft.map);storageError="탭 임시본을 삭제하지 못했습니다. 페이지를 다시 열면 이전 초안이 자동 복원될 수 있습니다. "+requestErrorMessage(error);}
      setCell(null);setSource(null);setDraft(null);setPreview(null);
      setPast([]);setFuture([]);setBrush("pan");setStorageFailed(false);setSaveUncertain(false);setStorageNotice(storageError);setFeedback("지도 원본을 다시 불러왔습니다.");
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
      discardedRecovery.current.delete(draft.map);
      setStorageFailed(false);
      setStorageNotice("현재 탭에 초안과 편집 이력을 보관했습니다.");
    }catch(error){setStorageFailed(true);setStorageNotice("탭 임시저장 실패 · "+requestErrorMessage(error));}
  },[draft,past,future,source]);
  const placed=draft?.objects || [];
  const cellDirty=isMapCellDirty(cell,cellOriginal);
  const unsafeAutosave=Boolean(draft && (past.length || future.length) && storageFailed);
  useEffect(()=>{
    if(!cellDirty && !unsafeAutosave && !saving && !saveUncertain)return;
    const warn=event=>{event.preventDefault();event.returnValue=true;};
    window.addEventListener("beforeunload",warn);
    return ()=>window.removeEventListener("beforeunload",warn);
  },[cellDirty,unsafeAutosave,saving,saveUncertain]);
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
    if(invalidMapCellHeight(cell.height))return;
    restorePreviewFocus.current=event.currentTarget.contains(document.activeElement);
    const {column,row,tile,height,blocked}=cell;
    const cells=draft.cells.filter(item=>item.column!==column || item.row!==row);
    const next={...draft,cells:[...cells,{column,row,tile,height:Number(height),blocked,...(cell.wall?{wall:cell.wall}:{})}]};
    await applyDraft(next,"cell");
  }
  async function applyDraft(next,action){
    if(cellDirty && action!=="cell"){setFeedback("변경한 셀 입력을 먼저 검증하거나 셀 입력 취소를 선택하세요.");return;}
    setReading(true);setPreview(null);setFeedback("");
    try{
      const result=await readMap("map-edit-preview",next);
      if(!validMapDraftPreview(result))throw new Error("초안 검증 결과 형식을 확인할 수 없습니다.");
      await applyMapPreview(result.render);
      if(action==="undo"){
        setPast(past.slice(0,-1));setFuture([...future,draft]);setCell(null);setCellOriginal(null);
      }else if(action==="redo"){
        setFuture(future.slice(0,-1));setPast([...past,draft]);setCell(null);setCellOriginal(null);
      }else{
        setPast([...past,draft]);setFuture([]);
        if(action==="import"){setCell(null);setCellOriginal(null);}
        else if(cell){const updated=next.cells.find(item=>item.column===cell.column && item.row===cell.row);if(updated){setCell(updated);setCellOriginal(updated);}}
      }
      setStorageFailed(true);setDraft(next);setPreview(result);
      setFeedback("검증 완료 · 변경 셀 "+result.cells+"개 · 도달 가능 "+result.reachable+"칸");
    }catch(error){setFeedback(requestErrorMessage(error));}
    finally{setReading(false);}
  }
  async function save(event){
    if(savingRef.current || mapDraftSaveReason(preview))return;
    restorePreviewFocus.current=Boolean(event && event.currentTarget===document.activeElement);
    savingRef.current=true;
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setSaving(true);setReading(true);setPreview(null);setFeedback("");
    try{
      const result=await untilAborted(managementCommand("map-assets","map-edit-save",{...draft,token:preview.token},{signal:controller.signal}),controller.signal);
      if(result.map!==draft.map || result.saved!==true)throw new Error("저장 결과를 확인할 수 없습니다.");
      try{sessionStorage.removeItem(storageKey(draft.map));discardedRecovery.current.delete(draft.map);setStorageNotice("");}
      catch(error){discardedRecovery.current.add(draft.map);setStorageNotice("저장 후 탭 임시본을 삭제하지 못했습니다. 페이지를 다시 열면 이전 초안이 자동 복원될 수 있습니다. "+requestErrorMessage(error));}
      setPast([]);setFuture([]);setCell(null);setSource(null);setDraft(null);setStorageFailed(false);setSaveUncertain(false);setFeedback(result.map+" 저장 완료");
    }catch(error){setSaveUncertain(true);setFeedback("저장 결과를 확인하지 못했습니다. 다시 저장하기 전에 원본 상태를 확인하세요. · "+(timedOut ? "저장 응답 시간이 초과됐습니다." : requestErrorMessage(error)));}
    finally{clearTimeout(timeout);savingRef.current=false;setSaving(false);setReading(false);}
  }
  async function inspectSaveRevision(event){
    if(!draft)return;
    restorePreviewFocus.current=Boolean(event && event.currentTarget===document.activeElement);
    setReading(true);setFeedback("");
    try{
      const result=await readMap("map-edit-load",{map:draft.map});
      if(result?.map!==draft.map || typeof result.revision!=="string" || !result.revision)throw new Error("원본 리비전을 확인할 수 없습니다.");
      setFeedback((result.revision===draft.revision ? "조회 시점에 원본 리비전이 초안의 기준과 같습니다." : "조회 시점에 원본 리비전이 초안의 기준과 다릅니다.")+" 저장이 아직 진행 중일 수 있으므로 이 조회만으로 저장 완료 여부를 판단할 수 없습니다. 초안을 보관하고 원본 상태를 확인하세요.");
    }catch(error){setFeedback("원본 상태 조회 실패 · "+requestErrorMessage(error));}
    finally{setReading(false);}
  }
  async function inspectCell(override=null){
    if(cellDirty){setFeedback("변경한 셀 입력을 먼저 검증하거나 셀 입력 취소를 선택하세요.");return;}
    const selected=override || window.mapReviewSelectedCell;
    if(!selected){setFeedback("지도를 눌러 셀을 선택하거나 아래 열·행을 입력해 조회하세요.");return;}
    const focusAtStart=document.activeElement;
    setReading(true);
    try{
      const map=window.mapReviewControlOptions().selected;
      const snapshot=source?.map===map ? source : await readMap("map-edit-load",{map});
      const originalCell=readMapCell(snapshot,map,selected);
      setSource(snapshot);window.mapReviewSelectedCell=selected;
      let current=draft;
      if(!current){
        let raw;
        try{if(!discardedRecovery.current.has(map))raw=sessionStorage.getItem(storageKey(map));}
        catch(error){setStorageNotice("탭 임시저장을 사용할 수 없습니다. "+error.message);}
        setRecovery(null);
        if(raw){
          setRecovery({map,raw});
          const saved=JSON.parse(raw),state=saved.state;
          if(saved.version!==1 || !Array.isArray(state?.history) || !Array.isArray(state.future) ||
            ![state.draft,...state.history,...state.future].every(item=>item?.map===map && item.revision===snapshot.revision &&
              Array.isArray(item.cells) && Array.isArray(item.objects)))throw new Error("원본 리비전 또는 임시본 형식이 달라 복원할 수 없습니다.");
          const checked=await readMap("map-edit-preview",state.draft);
          if(!validMapDraftPreview(checked))throw new Error("복원 초안 검증 결과 형식을 확인할 수 없습니다.");
          await applyMapPreview(checked.render);
          setRecovery(null);current=state.draft;setStorageFailed(true);setPast(state.history);setFuture(state.future);setPreview(checked);
        }else current={map,revision:snapshot.revision,cells:[],
        objects:snapshot.tiles.objects.filter(item=>item.kind==="decoration"),
        ...(snapshot.terrain.terrainEffects?{terrainEffects:snapshot.terrain.terrainEffects}:{})};
        setDraft(current);
      }
      const {column,row}=selected;
      const nextCell={...originalCell,
        ...current.cells.find(item=>item.column===column && item.row===row)};
      setCell(nextCell);setCellOriginal(nextCell);
      setFeedback("");
      requestAnimationFrame(()=>{if(document.activeElement===focusAtStart || document.activeElement===document.body)cellFormRef.current?.focus({preventScroll:true});});
    }catch(error){setFeedback(error.message);requestAnimationFrame(()=>{if(document.activeElement===focusAtStart || document.activeElement===document.body)feedbackRef.current?.focus();});}
    finally{setReading(false);}
  }
  const [ready,setReady]=useState(false),[feedback,setFeedback]=useState("");
  useEffect(()=>{if(!reading && feedback && restorePreviewFocus.current){restorePreviewFocus.current=false;restoreLostFocus(document,feedbackRef.current);}},[reading,feedback]);
  useEffect(()=>{if(reading || !restoreImportFocus.current)return;restoreImportFocus.current=false;const target=importInputRef.current;if(target?.isConnected && !target.matches(':disabled'))restoreLostFocus(document,target);},[reading,importError]);
  const [loadError,setLoadError]=useState("");
  const recoveryParams=new URLSearchParams({mapKind:field?"field":"town"});
  const recoveryMap=new URLSearchParams(location.search).get("map");
  if(recoveryMap)recoveryParams.set("map",recoveryMap);
  useEffect(()=>{
    let active=true,timedOut=false;
    const controller=new AbortController();
    const cancelDeadline=progressDeadline(window,"map-review-load-progress",()=>{timedOut=true;controller.abort();});
    setLoadError("");setReady(false);
    const url=new URL(location.href);
    url.searchParams.set("mapKind",field?"field":"town");
    history.replaceState(history.state,"",url);
    untilAborted(import(new URL("/isloon-map-review/block-map-review.js",location.origin).href),controller.signal).then(()=>{
      if(active)setReady(true);
    }).catch(error=>{if(active)setLoadError(timedOut ? "지도 검수 화면을 불러오는 시간이 초과됐습니다." : requestErrorMessage(error));}).finally(cancelDeadline);
    return ()=>{active=false;cancelDeadline();controller.abort();};
  },[field]);
  useEffect(()=>{
    if(!field || !ready)return;
    const receive=()=>setStrokeCount(value=>value+1);
    window.addEventListener("map-editor-brush",receive);
    return ()=>window.removeEventListener("map-editor-brush",receive);
  },[field,ready]);
  useEffect(()=>{
    if(!field || !ready)return;
    window.mapReviewBrushTool=draft && !cellDirty ? brush : "pan";
    window.mapReviewBrushTexture=texture;window.mapReviewBrushTile=floor;window.mapReviewBrushWall=wall;
  },[field,ready,brush,draft,floor,wall,texture,cellDirty]);
  useEffect(()=>{if(!field || !ready)return;window.mapReviewBrushReadOnly=reading;return()=>{window.mapReviewBrushReadOnly=false;};},[field,ready,reading]);
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
  function guardNavigation(event){
    if((cellDirty || unsafeAutosave || saving) && event.button===0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey){event.preventDefault();setFeedback(saving ? "지도 저장 결과를 확인하는 중입니다." : cellDirty ? "변경한 셀 입력을 먼저 검증하거나 셀 입력 취소를 선택하세요." : "탭 임시저장을 확인하지 못했습니다. 이동 전 초안을 저장하거나 JSON으로 내려받으세요.");}
  }
  return <article className="map-review"><MapReviewNavigation field={field} destination={destination} onNavigate={guardNavigation} saving={saving} cellDirty={cellDirty} unsafeAutosave={unsafeAutosave}/>
    <h1 id="map-title">{title} 검수</h1>
    <fieldset className="map-view-controls" disabled={!ready}><legend>지도와 시점</legend>
      <div className="map-selection-row"><label>맵 선택<select id="map-select" disabled={Boolean(draft) || reading} aria-describedby={draft ? "map-change-reason" : undefined}/></label><button id="load-map" disabled={Boolean(draft) || reading} aria-describedby={draft ? "map-change-reason" : undefined}>맵 불러오기</button></div>
      {draft && <p id="map-change-reason">현재 지도 초안이 열려 있습니다. 지도를 바꾸려면 초안을 저장하거나 초안 보관 및 복원에서 원본으로 되돌리세요.</p>}
      <section className="map-selection-row" hidden={field}><label>건물 선택<select id="building"><option value="">건물 선택</option></select></label></section>
      <div className="ui-action-row" role="group" aria-label="지도 시점">
        {[["zoom-out","축소"],["zoom-in","확대"],["actual-size","사람 중심 · 100%"],["fit","전체 보기"]].map(([id,label])=><button key={id} id={id}>{label}</button>)}
        <output id="zoom-level" aria-live="polite"/>
      </div>
      <div className="map-display-options" role="group" aria-label="지도 표시 옵션">
      {[["show-character","기본 캐릭터",true],["show-safe-boundary","결계탑 · 결계 오러",true],["edges","메시 경계",false],["tile-edges","타일 경계",false],["blocked-areas","이동금지 영역",false]].map(([id,label,checked])=>
        <label key={id}><input type="checkbox" id={id} defaultChecked={checked} onChange={()=>window.mapReviewDisplayOptions(...["show-character","show-safe-boundary","edges"].map(key=>document.getElementById(key).checked),"contrast",document.getElementById("tile-edges").checked,document.getElementById("blocked-areas").checked)}/>{label}</label>)}
      </div>
      <button onClick={exportImage}>전체 맵 PNG 내보내기</button><a id="map-export-download" hidden>PNG 다운로드</a>
    </fieldset>
    <p role="status" id="status">{loadError ? "지도 검수 화면을 불러오지 못했습니다." : "지도를 불러오는 중입니다."}</p>
    {loadError && <div role="alert"><p>{loadError} 새 탭에서 지도 검수를 다시 열 수 있습니다.</p><a href={"/management/frame/map-review/?"+recoveryParams} target="_blank" rel="noopener noreferrer">새 탭에서 지도 검수 열기</a></div>}
    {feedback && <p ref={feedbackRef} className="map-review-feedback" role="status" tabIndex={-1}>{feedback}</p>}
    {field && reading && <p id={saving ? "map-saving-status" : "map-reading-status"} role="status">{saving ? "지도 저장 결과를 확인하고 있습니다." : "지도 조회 또는 초안 처리를 진행하고 있습니다."}</p>}
    {field && <fieldset disabled={!ready || reading} aria-describedby={reading ? (saving ? "map-saving-status" : "map-reading-status") : undefined}><legend>셀 검수</legend>
      {saveUncertain && <section aria-label="저장 결과 확인"><p>이전 저장 결과가 불확실합니다. 초안은 유지됩니다. 새로 검증하거나 원본 리비전을 조회해도 이전 저장의 완료 여부가 확인되는 것은 아닙니다.</p><button type="button" onClick={inspectSaveRevision}>현재 원본 리비전 확인</button></section>}
      <label><input type="checkbox" checked={editing} aria-describedby={cellDirty ? "map-cell-pending-reason" : undefined} onChange={event=>{if(cellDirty){setFeedback("변경한 셀 입력을 먼저 검증하거나 셀 입력 취소를 선택하세요.");return;}window.mapReviewEditingEnabled=event.target.checked;setEditing(event.target.checked);setBrush("pan");window.mapReviewSelectedCell=null;setCell(null);setCellOriginal(null);}}/>캐릭터 이동 대신 셀 선택</label>
      <p id="map-cell-selection-help">지도를 눌러 셀을 선택한 뒤 조회하거나, 아래 열·행을 입력해 바로 조회할 수 있습니다.</p>
      <button aria-describedby={["map-cell-selection-help",cellDirty && "map-cell-pending-reason"].filter(Boolean).join(" ")} onClick={()=>inspectCell()}>선택 셀 속성 조회</button>
      <form className="map-cell-inspect-form" onSubmit={event=>{event.preventDefault();inspectCell({column:Number(cellColumn),row:Number(cellRow)});}}>
        <div className="generator-settings-grid">
        <MapCoordinateInput axis="열" value={cellColumn} onChange={setCellColumn}/>
        <MapCoordinateInput axis="행" value={cellRow} onChange={setCellRow}/>
        </div>
        <button type="submit" aria-describedby={cellDirty ? "map-cell-pending-reason" : undefined}>입력한 셀 속성 조회</button>
      </form>
      {cell && <form ref={cellFormRef} className="map-cell-editor" tabIndex={-1} aria-label="선택 셀 편집" onSubmit={previewCell}><p>열 {cell.column} · 행 {cell.row} · {cell.tile} · 높이 {cell.height} · {cell.blocked?"이동 금지":"이동 가능"} · 배치물 {placed.filter(atCell).map(item=>item.id).join(", ") || "없음"}</p>
        <div className="generator-settings-grid">
        <label>지형<select value={cell.tile} onChange={e=>editCell("tile",e.target.value)}>
          {Object.entries(source.codes).map(([code,name])=><option key={code} value={code}>{name} · {code}</option>)}</select></label>
        <div><label>높이<input type="number" required min="0" max="20" step="1" value={cell.height} aria-invalid={invalidMapCellHeight(cell.height) || undefined} aria-describedby={invalidMapCellHeight(cell.height) ? heightErrorId : undefined} onChange={e=>editCell("height",e.target.value)}/></label>{invalidMapCellHeight(cell.height) && <small id={heightErrorId}>0~20의 정수를 입력하세요.</small>}</div>
        </div>
        <label><input type="checkbox" checked={cell.blocked} onChange={e=>editCell("blocked",e.target.checked)}/>이동 금지</label>
        {cellDirty && <p role="status">이 셀 입력은 검증 전이라 초안 자동 보관과 JSON 다운로드에 포함되지 않습니다.</p>}
        <div className="ui-action-row"><ActionButton type="submit" reasons={[invalidMapCellHeight(cell.height) && "높이를 0~20의 정수로 수정하세요."]}>초안 검증 및 미리보기</ActionButton>{cellDirty && <button type="button" onClick={event=>{if(document.activeElement===event.currentTarget)cellFormRef.current?.focus({preventScroll:true});setCell(cellOriginal);setFeedback("셀 입력을 이전 값으로 되돌렸습니다.");}}>셀 입력 취소</button>}</div></form>}
      {recovery && <section aria-label="임시본 복구"><p>복원하지 못한 임시본을 파일로 보관하거나 삭제할 수 있습니다.</p>
        <div className="ui-action-row"><button onClick={()=>downloadDraft(recovery.map,recovery.raw)}>임시본 JSON 다운로드</button>
        <button onClick={()=>{if(window.confirm("이 탭에 보관한 "+recovery.map+" 임시본을 삭제할까요?"))discardRecovery();}}>임시본 삭제</button></div>
      </section>}
      {draft && <details><summary>초안 보관 및 복원</summary>
        <button onClick={()=>downloadDraft(draft.map,JSON.stringify(draft,null,2))}>초안 JSON 다운로드</button>
        <MapDraftFileInput inputRef={importInputRef} cellDirty={cellDirty} error={importError} onFile={importDraft}/>
        <button onClick={discardDraft}>초안 버리고 원본 다시 읽기</button>
      </details>}
      {storageNotice && <p role="status">{storageNotice}</p>}
      {unsafeAutosave && <p id="map-storage-failure">이동 전 초안을 저장하거나 JSON으로 내려받으세요.</p>}
      {cellDirty && <p id="map-cell-pending-reason">다른 초안 조작을 하려면 셀 입력을 먼저 검증하거나 취소하세요.</p>}
      {draft && <label>지도 드래그 도구<select value={brush} disabled={!editing || cellDirty} aria-describedby={cellDirty ? "map-cell-pending-reason" : !editing ? "map-brush-reason" : undefined} onChange={e=>setBrush(e.target.value)}>
        <option value="pan">이동·셀 선택</option><option value="floor" disabled={!source?.blocked_tile_codes}>바닥 칠하기</option><option value="wall" disabled={!source?.wall_tiles?.length}>벽면 칠하기</option><option value="raise">높이 올리기</option><option value="lower">높이 내리기</option><option value="place">빌보드 배치</option><option value="delete">빌보드 삭제</option>
      </select></label>}
      {draft && !editing && <p id="map-brush-reason">드래그 도구를 사용하려면 셀 선택을 켜세요.</p>}
      {draft && brush==="wall" && <label>브러시 벽면 타일<select value={wall} onChange={e=>setWall(e.target.value)}>
        <option value="">타일 선택</option>{source.wall_tiles.map(key=><option key={key}>{key}</option>)}
      </select></label>}
      {draft && brush==="floor" && <label>브러시 바닥 타일<select value={floor} onChange={e=>setFloor(e.target.value)}>
        <option value="">타일 선택</option>{Object.entries(source.codes).map(([code,name])=><option key={code} value={code}>{name} · {code}</option>)}
      </select></label>}
      {draft && <fieldset><legend>빌보드 배치</legend>
        <label>추가할 에셋<select value={texture} onChange={e=>setTexture(e.target.value)}>
          <option value="">에셋 선택</option>{(source.textures || []).map(key=><option key={key}>{key}</option>)}</select></label>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!cell && "지도에서 셀을 선택하고 속성을 조회하세요.",!source.textures?.includes(texture) && "추가할 에셋을 선택하세요."]} onClick={addObject}>선택 셀에 추가</ActionButton>
        <label>배치 ID<select value={selectedObject?.id || ""} onChange={e=>setObjectId(e.target.value)}>
          <option value="">배치 선택</option>{placed.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!selectedObject && "이동할 배치를 선택하세요.",!cell && "이동할 셀을 선택하고 속성을 조회하세요.",selectedObject && cell && atCell(selectedObject) && "이미 선택한 셀에 있습니다."]} onClick={moveObject}>선택 셀로 이동</ActionButton>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!selectedObject && "삭제할 배치를 선택하세요."]} onClick={()=>applyDraft({...draft,objects:placed.filter(item=>item.id!==objectId)},"edit")}>선택 배치 삭제</ActionButton>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!cell ? "셀을 선택하고 속성을 조회하세요." : !placed.some(atCell) && "선택한 셀에 빌보드가 없습니다."]} onClick={()=>applyDraft({...draft,objects:placed.filter(item=>!atCell(item))},"edit")}>선택 셀의 빌보드 모두 삭제</ActionButton>
      </fieldset>}
      {draft && <div>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!past.length && "되돌릴 편집이 없습니다."]} onClick={()=>applyDraft(past[past.length-1],"undo")}>한 단계 되돌리기</ActionButton>
        <ActionButton reasons={[cellDirty && "셀 입력을 먼저 검증하거나 취소하세요.",!future.length && "다시 실행할 편집이 없습니다."]} onClick={()=>applyDraft(future[future.length-1],"redo")}>한 단계 다시 실행</ActionButton>
        <span>편집 이력 {past.length} / {past.length+future.length}단계</span>
      </div>}
      {preview && <ActionButton reasons={[mapDraftSaveReason(preview)]} onClick={save}>검증된 초안 저장</ActionButton>}
    </fieldset>}
    <p id="map-keyboard-help">지도에 초점을 둔 뒤 방향키로 화면 이동, Shift+방향키로 캐릭터 이동, +·−로 확대·축소, 0으로 전체 보기를 사용할 수 있습니다.{field && " 셀은 위의 열·행 입력으로도 조회할 수 있습니다."}</p>
    <canvas id="map" className="map-review-canvas" width="768" height="576" tabIndex="0" aria-label={title+" 지도"} aria-describedby="map-keyboard-help" style={{width:"100%",aspectRatio:"4/3",touchAction:"none"}}/>
    {[["tile","지형 타일"],["building","건물 스프라이트"],["billboard","빌보드"],["structure","결계·경비 구조물"]].map(([id,label])=>
      <details key={id}><summary>{label} 원본</summary><div id={"applied-"+id+"-list"}/></details>)}
  </article>;
}
