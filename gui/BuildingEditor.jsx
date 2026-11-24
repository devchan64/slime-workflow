import React,{useEffect,useId,useRef,useState} from "react";
import {drawBuildingPreview} from "./drawBuildingPreview.js";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ActionButton from "./ActionButton.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import RecoverableImage from "./RecoverableImage.jsx";
import {readLocalImageBase64} from "./readLocalImage.mjs";

const fields=[
  ["anchorX","앵커 X",0,16],["anchorY","앵커 Y",0,16],
  ["displayWidthAdjustment","가로 크기 보정 (px)",-2048,2048,1],
  ["displayHeightAdjustment","세로 크기 보정 (px)",-2048,2048,1],
  ["shadowOffsetColumn","그림자 열 이동 (타일)",-4,4],["shadowOffsetRow","그림자 행 이동 (타일)",-4,4],
  ["shadowScaleX","그림자 열 배율",0.1,4],["shadowScaleY","그림자 행 배율",0.1,4],
];

export function validBuildingCatalog(result){
  if(!Number.isInteger(result?.generation) || result.generation<0 || !Array.isArray(result.assets))return false;
  const ids=new Set();
  return result.assets.every(row=>{
    if(!row || typeof row.texture!=="string" || !row.texture || ids.has(row.texture) || !Number.isFinite(row.width) || row.width<=0 || !Number.isFinite(row.height) || row.height<=0 || !row.properties || typeof row.properties!=="object" || Array.isArray(row.properties) || !Array.isArray(row.maps))return false;
    ids.add(row.texture);
    if(!Number.isFinite(row.properties.anchorX) || !Number.isFinite(row.properties.anchorY) || fields.some(([key])=>row.properties[key]!=null && !Number.isFinite(row.properties[key])) || (row.properties.shadowShape!=null && !["circle","rectangle"].includes(row.properties.shadowShape)))return false;
    return row.maps.every(map=>map && typeof map.map==="string" && typeof map.name==="string" && typeof map.facing==="string" && Number.isInteger(map.width) && map.width>0 && Number.isInteger(map.height) && map.height>0 && Number.isFinite(map.contentWidth) && map.contentWidth>0);
  });
}

export function validBuildingChange(result,texture,generation,action,properties){
  return Boolean(result && result.saved===true && result.asset===texture && Number.isSafeInteger(result.generation) && result.generation>generation &&
    (action ? result.action===action : result.properties && Object.entries(properties).every(([key,value])=>result.properties[key]===value)));
}

export function invalidBuildingSizeMap(building,properties){
  for(const usage of building.maps){
    const width=usage.tower?building.width*112/207:(usage.width+usage.height)*40*1.04/usage.contentWidth;
    if(width+properties.displayWidthAdjustment<=0 || width*building.height/building.width+properties.displayHeightAdjustment<=0)return usage.map;
  }
  return null;
}

function BuildingProperties({building,generation,busy,setBusy,onSaved,onDirtyChange}){
  const expected={displayWidthAdjustment:0,displayHeightAdjustment:0,...building.properties};
  const original={shadowShape:"circle",shadowOffsetColumn:0,shadowOffsetRow:0,shadowScaleX:1,shadowScaleY:1,...expected};
  const [values,edit]=useState(original),[error,setError]=useState(""),[sizeError,setSizeError]=useState("");
  const sizeErrorId=useId();
  const [placement,selectPlacement]=useState(0);
  const [previewStatus,setPreviewStatus]=useState("loading"),[previewRevision,retryPreview]=useState(0);
  const canvas=useRef(null),previewRetryButton=useRef(null),previewInvalid=useRef(null),restorePreviewFocus=useRef(false),saving=useRef(false);
  useEffect(()=>{
    const url="/management/assistant/building-image/"+encodeURIComponent(building.texture);
    if(fields.some(([key])=>values[key]==="" || !Number.isFinite(Number(values[key])))){
      canvas.current.getContext("2d").clearRect(0,0,canvas.current.width,canvas.current.height);setPreviewStatus("invalid");return;
    }
    return drawBuildingPreview(canvas.current,url,building.maps[placement],values,setPreviewStatus);
  },[building,placement,values,previewRevision]);
  useEffect(()=>{
    if(previewStatus==="loading" || !restorePreviewFocus.current)return;
    restorePreviewFocus.current=false;
    restoreLostFocus(document,(previewStatus==="image-error" ? previewRetryButton : previewStatus==="invalid" ? previewInvalid : canvas).current);
  },[previewStatus]);
  const changed=Object.entries(original).some(([key,value])=>String(values[key])!==String(value));
  useEffect(()=>{onDirtyChange(changed);},[changed,onDirtyChange]);
  async function save(event){
    event.preventDefault();
    if(!changed || busy || saving.current)return;
    const properties={shadowShape:values.shadowShape};
    for(const [key] of fields)properties[key]=Number(values[key]);
    const invalidMap=invalidBuildingSizeMap(building,properties);
    if(invalidMap!==null){setSizeError(invalidMap+"에서 표시 크기가 0 이하입니다.");return;}
    saving.current=true;setBusy(true);setError("");setSizeError("");
    try{
      const result=await managementCommand("map-assets","building-save",{texture:building.texture,generation,expected,properties});
      if(!validBuildingChange(result,building.texture,generation,null,properties))throw new Error("저장 응답의 대상이나 속성을 확인할 수 없습니다.");
      onSaved(building.texture);
    }catch(problem){setError("저장 결과를 확인하지 못했습니다. 다시 저장하기 전에 편집 내용을 기록하고 목록을 다시 읽어 실제 속성을 확인하세요. · "+requestErrorMessage(problem));}
    finally{saving.current=false;setBusy(false);}
  }
  return <form className="building-properties-form" onSubmit={save}><fieldset disabled={busy}><legend>건물 표시 속성</legend>
    {building.maps.length>0 && <label>미리보기 맵 배치<select value={placement} onChange={e=>selectPlacement(Number(e.target.value))}>
      {building.maps.map((item,i)=><option key={i} value={i}>{item.map} · {item.name} · {item.width}×{item.height} · {item.facing}</option>)}</select></label>}
    <canvas ref={canvas} tabIndex={-1} width="480" height="360" aria-label="건물 타일 배치 미리보기" style={{maxWidth:"100%",height:"auto"}}/>
    {previewStatus==="loading" && <p role="status">건물 미리보기를 불러오는 중입니다.</p>}
    {previewStatus==="invalid" && <p ref={previewInvalid} tabIndex={-1} role="status">입력값과 표시 크기를 확인하면 미리보기를 볼 수 있습니다.</p>}
    {previewStatus==="image-error" && <p role="alert">건물 이미지를 불러오지 못했습니다. <button ref={previewRetryButton} type="button" onClick={()=>{restorePreviewFocus.current=document.activeElement===previewRetryButton.current;retryPreview(value=>value+1);}}>미리보기 다시 불러오기</button></p>}
    <p>{building.maps.length?"노란 윤곽은 점유 타일, 빨간 십자는 앵커, 점선은 주변 타일입니다.":"등록된 맵 배치가 없어 원본 이미지를 표시합니다."}</p>
    <div className="building-properties-grid">{fields.map(([key,label,min,max,step])=>{const sizeField=["displayWidthAdjustment","displayHeightAdjustment"].includes(key);return <label key={key}>{label}<input type="number" required min={min} max={max} step={step || "any"} value={values[key]} aria-invalid={sizeField && sizeError ? true : undefined} aria-describedby={sizeField && sizeError ? sizeErrorId : undefined} onChange={e=>{if(sizeField)setSizeError("");edit({...values,[key]:e.target.value});}}/></label>;})}
    <label>그림자 형태<select value={values.shadowShape} onChange={e=>edit({...values,shadowShape:e.target.value})}>
      <option value="circle">원형</option><option value="rectangle">사각형</option></select></label></div>
    {sizeError && <p id={sizeErrorId} role="alert">{sizeError}</p>}
    <button type="button" onClick={()=>{setSizeError("");edit({...values,displayWidthAdjustment:0,displayHeightAdjustment:0});}}>크기 보정 초기화</button>
    {changed && <button type="button" onClick={()=>{edit(original);setError("");setSizeError("");}}>편집 취소</button>}
    <ActionButton type="submit" reasons={[!changed && "변경한 속성이 없습니다."]}>표시 속성 저장</ActionButton>
    {error && <p role="alert">{error}</p>}
  </fieldset></form>;
}

export async function buildingCommand(action,payload,{signal,onDispatch}={}){
  const bytes=new TextEncoder().encode(JSON.stringify(payload));
  const controller=new AbortController();let timedOut=false;
  const abort=()=>controller.abort();
  if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",abort,{once:true});
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  let digest;
  try{digest=new Uint8Array(await untilAborted(crypto.subtle.digest("SHA-256",bytes),controller.signal));}
  catch(error){if(timedOut)throw new Error("건물 요청 준비 시간이 초과됐습니다. 다시 시도하세요.");throw error;}
  finally{clearTimeout(timer);signal?.removeEventListener("abort",abort);}
  if(signal?.aborted)throw new DOMException("등록 준비가 중단됐습니다.","AbortError");
  const requestId="building-"+action+"-"+Array.from(digest,b=>b.toString(16).padStart(2,"0")).join("");
  onDispatch?.();
  return managementCommand("map-assets","building-"+action,{...payload,requestId});
}

export function BuildingRegistration({generation,busy,setBusy,onRegistered}){
  const [error,setError]=useState(""),[fileError,setFileError]=useState("");
  const idHelp=useId(),imageHelp=useId(),fileErrorId=useId(),submitting=useRef(false),prepareRequest=useRef(null);
  useEffect(()=>()=>{prepareRequest.current?.abort();},[]);
  async function submit(event){
    event.preventDefault();
    const form=event.currentTarget,fields=new FormData(form),file=fields.get("image");
    if(busy || submitting.current)return;
    if(!file?.size || file.size>16*1024*1024){setFileError("16MiB 이하의 PNG를 선택하세요.");return;}
    submitting.current=true;
    const controller=new AbortController();prepareRequest.current=controller;
    let requested=false;
    setBusy(true);setError("");setFileError("");
    try{
      const imageBase64=await readLocalImageBase64(file,{signal:controller.signal});
      const texture=fields.get("texture").trim();
      const result=await buildingCommand("register",{texture,generation,imageBase64,properties:{anchorX:Number(fields.get("x")),anchorY:Number(fields.get("y"))}},{signal:controller.signal,onDispatch:()=>{requested=true;}});
      if(!validBuildingChange(result,texture,generation,"register"))throw new Error("등록 응답의 대상을 확인할 수 없습니다.");
      onRegistered(texture);
    }catch(problem){if(problem?.name!=="AbortError")setError((requested ? "등록 결과를 확인하지 못했습니다. 다시 등록하기 전에 건물 목록에서 처리 여부를 확인하세요. · " : "")+requestErrorMessage(problem));}
    finally{if(prepareRequest.current===controller)prepareRequest.current=null;submitting.current=false;setBusy(false);}
  }
  return <details><summary>건물 등록</summary><form className="building-registration-form" onSubmit={submit}><fieldset disabled={busy}>
    <label>건물 ID<input name="texture" required pattern="town-[a-z0-9\x2d]+-v[1-9][0-9]*" placeholder="town-iseulon-house-v1" aria-describedby={idHelp}/></label>
    <small id={idHelp}>town-으로 시작하고 -v1처럼 양의 버전 번호로 끝나는 영문 소문자·숫자·하이픈 ID를 입력하세요.</small>
    <label>투명 PNG<input name="image" required type="file" accept="image/png" aria-invalid={fileError ? true : undefined} aria-describedby={[imageHelp,fileError ? fileErrorId : null].filter(Boolean).join(" ")} onChange={()=>setFileError("")}/></label>
    <small id={imageHelp}>투명 PNG · 최대 16MiB</small>
    {fileError && <p id={fileErrorId} role="alert">{fileError}</p>}
    {[["x","앵커 X",0.5],["y","앵커 Y",1]].map(([name,label,value])=><label key={name}>{label}<input name={name} type="number" required min="0" max="16" step="any" defaultValue={value}/></label>)}
    <button type="submit">건물 등록</button>{error && <p role="alert">{error}</p>}
  </fieldset></form></details>;
}

export function BuildingAssetList({assets,selected,disabled,onSelect,image}){
  return <div className="building-asset-list" role="group" aria-label="건물 목록">{assets.map(item=><button key={item.texture} type="button" disabled={disabled} aria-pressed={item.texture===selected} onClick={()=>onSelect(item.texture)}>
    <img loading="lazy" src={image(item.texture)} width="64" height="64" alt=""/><span>{item.texture}{item.texture===selected && <small> · 선택됨</small>}</span></button>)}</div>;
}

export default function BuildingEditor(){
  const [catalog,setCatalog]=useState(null),[selected,setSelected]=useState("");
  const [error,setError]=useState(""),[revision,reload]=useState(0);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [dirty,setDirty]=useState(false);
  const [loading,setLoading]=useState(true),[checkedAt,setCheckedAt]=useState(null),[catalogVersion,setCatalogVersion]=useState(0);
  const reloadButton=useRef(null),listHeading=useRef(null),catalogError=useRef(null),restoreCatalogFocus=useRef(false),retiring=useRef(false);
  useEffect(()=>{document.title="건물 에셋 관리";},[]);
  function refreshCatalog(restore=false){restoreCatalogFocus.current=restore;setLoading(true);reload(value=>value+1);}
  useEffect(()=>{
    if(loading || !restoreCatalogFocus.current)return;
    restoreCatalogFocus.current=false;
    restoreLostFocus(document,(error ? catalogError : listHeading).current);
  },[loading,error,catalog]);
  useEffect(()=>{
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    untilAborted(managementCommand("map-assets","building-list",{},{signal:controller.signal}),controller.signal).then(result=>{
      if(!validBuildingCatalog(result))throw new Error("건물 목록 응답을 확인할 수 없습니다.");
      if(active){
        setCatalog(result);setCatalogVersion(value=>value+1);setCheckedAt(new Date());
        setSelected(previous=>previous || result.assets[0]?.texture || "");
      }
    }).catch(problem=>{if(active)setError(timedOut ? "건물 목록 조회 시간이 초과됐습니다. 다시 읽어 주세요." : requestErrorMessage(problem));}).finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  const unavailable=loading || Boolean(error);
  const building=catalog?.assets.find(item=>item.texture===selected);
  async function retire(){
    if(busy || retiring.current || dirty || unavailable || !building || building.texture==="ward-tower-v1" || building.maps.length)return;
    if(!window.confirm(building.texture+"을 건물 목록과 공용 속성에서 삭제할까요? 이미지 원본과 등록 이력은 보존됩니다."))return;
    retiring.current=true;
    setBusy(true);setError("");
    try{
      const result=await buildingCommand("retire",{texture:building.texture,generation:catalog.generation});
      if(!validBuildingChange(result,building.texture,catalog.generation,"retire"))throw new Error("삭제 응답의 대상을 확인할 수 없습니다.");
      setNotice(building.texture+" 삭제 완료");refreshCatalog(document.activeElement===document.body);
    }catch(problem){setError("삭제 결과를 확인하지 못했습니다. 다시 요청하기 전에 건물 목록을 다시 읽어 확인하세요. · "+requestErrorMessage(problem));}
    finally{retiring.current=false;setBusy(false);}
  }
  const image=id=>"/management/assistant/building-image/"+encodeURIComponent(id);
  return <article className="building-editor-page"><h1>건물 에셋 관리</h1>
    <button ref={reloadButton} type="button" disabled={busy || dirty || loading} onClick={()=>refreshCatalog(document.activeElement===reloadButton.current)}>{loading ? "건물 목록 조회 중…" : "건물 목록 다시 읽기"}</button>
    {busy && <p role="status">건물 요청을 처리하고 있습니다.</p>}
    {dirty && <p role="status">저장하지 않은 건물 속성이 있습니다. 저장하거나 편집을 취소한 뒤 목록을 다시 읽거나 다른 건물을 선택하세요.</p>}
    {notice && <p role="status">{notice}</p>}
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p ref={catalogError} tabIndex={-1} role="alert">{error}{catalog && " 아래는 마지막 조회 결과이며, 다시 확인하기 전에는 변경할 수 없습니다."}</p>}
    {loading && catalog && <p role="status">목록 조회 중입니다. 아래는 마지막 조회 결과입니다.</p>}
    {catalog ? <><h2 ref={listHeading} tabIndex={-1}>건물 목록</h2><p>건물 {catalog.assets.length}종 · DB 세대 {catalog.generation}</p>
      <BuildingRegistration generation={catalog.generation} busy={busy || dirty || unavailable} setBusy={setBusy} onRegistered={id=>{
        setNotice(id+" 등록 완료");setSelected(id);refreshCatalog(document.activeElement===document.body);
      }}/>
      {!catalog.assets.length && <p>등록된 건물이 없습니다.</p>}
      {selected && !building && <p role="status">선택한 건물을 현재 목록에서 찾지 못했습니다. 다른 건물을 선택하세요.</p>}
      <BuildingAssetList assets={catalog.assets} selected={selected} disabled={busy || dirty || loading} onSelect={setSelected} image={image}/>
    </> : !error && <p role="status">건물 목록을 읽고 있습니다.</p>}
    {building && <section><h2>{building.texture}</h2>
      <RecoverableImage key={selected+":"+catalogVersion} src={image(selected)} name={selected}/>
      <p>{building.width}×{building.height} px · 앵커 X {building.properties.anchorX} · Y {building.properties.anchorY}</p>
      <BuildingProperties key={building.texture+"/"+catalogVersion} building={building} generation={catalog.generation} busy={busy || unavailable} setBusy={setBusy} onDirtyChange={setDirty}
        onSaved={id=>{setDirty(false);setNotice(id+" 표시 속성을 저장했습니다.");refreshCatalog(document.activeElement===document.body);}}/>
      <h3>사용 맵</h3>{building.maps.length ? <ul>{building.maps.map((usage,i)=><li key={i}>{usage.map} · {usage.name} · {usage.width}×{usage.height} · {usage.facing}</li>)}</ul> : <p>사용 맵 없음</p>}
      <ActionButton disabled={busy || dirty || unavailable} reasons={[
        building.texture==="ward-tower-v1" && "보호된 건물은 삭제할 수 없습니다.",
        building.maps.length>0 && "사용 중인 맵의 건물 배치를 먼저 제거하세요."
      ]} onClick={retire}>선택 건물 삭제</ActionButton>
    </section>}
  </article>;
}
