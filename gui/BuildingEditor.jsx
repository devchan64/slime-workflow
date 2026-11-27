import React,{useEffect,useId,useRef,useState} from "react";
import BuildingReviewCandidate from "./BuildingReviewCandidate.jsx";
import ConversationLink from "./ConversationLink.jsx";
import {drawBuildingPreview} from "./drawBuildingPreview.js";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ActionButton from "./ActionButton.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import RecoverableImage from "./RecoverableImage.jsx";
import {readLocalImageBase64} from "./readLocalImage.mjs";
import {imageRetryUrl} from "./imageRetryUrl.mjs";
import CardGallery from "./CardGallery.jsx";

export function buildingCatalogError(problem){
  const message=requestErrorMessage(problem);
  return message.includes("SLIME_CONTENT_SERVICE_ORIGIN") ? "콘텐츠 서비스 주소가 설정되지 않았거나 유효하지 않습니다. 서비스 설정을 확인하세요." : message;
}

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
    return row.maps.every(map=>map && typeof map.map==="string" && typeof map.name==="string" && typeof map.facing==="string" && Number.isInteger(map.width) && map.width>0 && Number.isInteger(map.height) && map.height>0 && Number.isFinite(map.contentWidth) && map.contentWidth>0 && map.contentWidth<=1);
  });
}

export function validBuildingChange(result,texture,generation,action,properties){
  return Boolean(result && result.saved===true && result.asset===texture && Number.isSafeInteger(result.generation) && result.generation>generation &&
    (action ? result.action===action : result.properties && Object.entries(properties).every(([key,value])=>result.properties[key]===value)));
}

export function invalidBuildingSizeMap(building,properties){
  for(const usage of building.maps){
    const width=usage.tower?building.width*112/207:(usage.width+usage.height)*40*1.04/usage.contentWidth;
    if(width+Number(properties.displayWidthAdjustment)<=0 || width*building.height/building.width+Number(properties.displayHeightAdjustment)<=0)return usage.map;
  }
  return null;
}

export function invalidBuildingSizeFields(building,properties){
  const invalid={width:null,height:null};
  for(const usage of building.maps){
    const width=usage.tower?building.width*112/207:(usage.width+usage.height)*40*1.04/usage.contentWidth;
    if(invalid.width===null && width+Number(properties.displayWidthAdjustment)<=0)invalid.width=usage.map;
    if(invalid.height===null && width*building.height/building.width+Number(properties.displayHeightAdjustment)<=0)invalid.height=usage.map;
  }
  return invalid;
}

export function buildingPropertiesChanged(original,values){
  return Object.entries(original).some(([key,value])=>{
    const current=values[key];
    if(typeof value!=="number")return current!==value;
    return current==null || String(current).trim()==="" || !Number.isFinite(Number(current)) || Number(current)!==value;
  });
}

export function BuildingProperties({building,generation,busy,disabledReason,setBusy,onSaved,onDirtyChange,onSaveUncertain}){
  const expected={displayWidthAdjustment:0,displayHeightAdjustment:0,...building.properties};
  const original={shadowShape:"circle",shadowOffsetColumn:0,shadowOffsetRow:0,shadowScaleX:1,shadowScaleY:1,...expected};
  const [values,edit]=useState(original),[error,setError]=useState("");
  const sizeErrorId=useId(),fieldErrorId=useId(),disabledHelp=useId();
  const fieldMinimum=(key,min)=>building.texture==="ward-tower-v1" && ["displayWidthAdjustment","displayHeightAdjustment"].includes(key) ? -138 : min;
  const fieldIssues=Object.fromEntries(fields.map(([key,,min,max,step])=>{const raw=values[key],n=Number(raw);return [key,raw==null || String(raw).trim()==="" || !Number.isFinite(n) || n<fieldMinimum(key,min) || n>max || (step===1 && !Number.isInteger(n))];}));
  const invalidSizes=invalidBuildingSizeFields(building,{displayWidthAdjustment:Number(values.displayWidthAdjustment),displayHeightAdjustment:Number(values.displayHeightAdjustment)});
  const widthSizeError=!fieldIssues.displayWidthAdjustment && invalidSizes.width!==null ? invalidSizes.width+"에서 표시 너비가 0 이하입니다." : "";
  const heightSizeError=!fieldIssues.displayHeightAdjustment && invalidSizes.height!==null ? invalidSizes.height+"에서 표시 높이가 0 이하입니다." : "";
  const sizeError=widthSizeError || heightSizeError;
  const [placement,selectPlacement]=useState(0),[tileOverlay,setTileOverlay]=useState(true);
  const [previewStatus,setPreviewStatus]=useState("loading"),[previewRevision,retryPreview]=useState(0);
  const canvas=useRef(null),previewRetryButton=useRef(null),previewInvalid=useRef(null),restorePreviewFocus=useRef(false),firstField=useRef(null),restoreCancelFocus=useRef(false),saving=useRef(null),saveButton=useRef(null),saveErrorRef=useRef(null),restoreSaveFocus=useRef(false);
  useEffect(()=>()=>{const request=saving.current;saving.current=null;request?.abort();},[]);
  useEffect(()=>{if(!busy && error && restoreSaveFocus.current){restoreSaveFocus.current=false;restoreLostFocus(document,saveErrorRef.current);}},[busy,error]);
  useEffect(()=>{
    const url="/management/assistant/building-image/"+encodeURIComponent(building.texture);
    if(Object.values(fieldIssues).some(Boolean) || sizeError){
      canvas.current.getContext("2d").clearRect(0,0,canvas.current.width,canvas.current.height);setPreviewStatus("invalid");return;
    }
    return drawBuildingPreview(canvas.current,previewRevision ? imageRetryUrl(url,previewRevision) : url,building.maps[placement],values,setPreviewStatus,{showTileOverlay:tileOverlay});
  },[building,placement,values,previewRevision,tileOverlay]);
  useEffect(()=>{
    if(previewStatus==="loading" || !restorePreviewFocus.current)return;
    restorePreviewFocus.current=false;
    restoreLostFocus(document,(previewStatus==="image-error" ? previewRetryButton : previewStatus==="invalid" ? previewInvalid : canvas).current);
  },[previewStatus]);
  const changed=buildingPropertiesChanged(original,values);
  useEffect(()=>{onDirtyChange(changed);},[changed,onDirtyChange]);
  useEffect(()=>{
    if(changed || !restoreCancelFocus.current)return;
    restoreCancelFocus.current=false;
    restoreLostFocus(document,firstField.current);
  },[changed]);
  async function save(event){
    event.preventDefault();
    if(!changed || busy || saving.current || Object.values(fieldIssues).some(Boolean) || sizeError)return;
    const properties={shadowShape:values.shadowShape};
    for(const [key] of fields)properties[key]=Number(values[key]);
    restoreSaveFocus.current=document.activeElement===saveButton.current;
    const controller=new AbortController();saving.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await untilAborted(managementCommand("map-assets","building-save",{texture:building.texture,generation,expected,properties},{signal:controller.signal}),controller.signal);
      if(saving.current!==controller)return;
      if(!validBuildingChange(result,building.texture,generation,null,properties))throw new Error("저장 응답의 대상이나 속성을 확인할 수 없습니다.");
      onSaved(building.texture);
    }catch(problem){if(saving.current===controller && (!controller.signal.aborted || timedOut)){setError("저장 결과를 확인하지 못했습니다. 다시 저장하기 전에 편집 내용을 기록하고 목록을 다시 읽어 실제 속성을 확인하세요. · "+(timedOut ? "응답 시간이 초과됐습니다." : requestErrorMessage(problem)));onSaveUncertain?.(building.texture);}}
    finally{clearTimeout(timeout);if(saving.current===controller){saving.current=null;setBusy(false);}}
  }
  return <form className="building-properties-form" onSubmit={save}>{busy && disabledReason && <p id={disabledHelp}>{disabledReason}</p>}<fieldset disabled={busy} aria-describedby={busy && disabledReason ? disabledHelp : undefined}><legend>건물 표시 속성</legend>
    {building.maps.length>0 && <label>미리보기 맵 배치<select value={placement} onChange={e=>selectPlacement(Number(e.target.value))}>
      {building.maps.map((item,i)=><option key={i} value={i}>{item.map} · {item.name} · {item.width}×{item.height} · {item.facing}</option>)}</select></label>}
    <label><input type="checkbox" checked={tileOverlay} onChange={event=>setTileOverlay(event.target.checked)}/> 바닥 타일 격자 오버레이</label>
    <canvas ref={canvas} tabIndex={-1} width="480" height="360" aria-label="건물 타일 배치 미리보기" style={{maxWidth:"100%",height:"auto"}}/>
    {previewStatus==="loading" && <p role="status">건물 미리보기를 불러오는 중입니다.</p>}
    {previewStatus==="invalid" && <p ref={previewInvalid} tabIndex={-1} role="status">입력값과 표시 크기를 확인하면 미리보기를 볼 수 있습니다.</p>}
    {previewStatus==="image-error" && <p role="alert">건물 이미지를 불러오지 못했습니다. <button ref={previewRetryButton} type="button" onClick={()=>{restorePreviewFocus.current=document.activeElement===previewRetryButton.current;retryPreview(value=>value+1);}}>미리보기 다시 불러오기</button></p>}
    <p>{building.maps.length?"노란 윤곽은 점유 타일, 빨간 십자는 앵커, 점선은 주변 타일입니다.":"등록된 맵 배치가 없어 원본 이미지를 표시합니다."}</p>
    <div className="building-properties-grid">{fields.map(([key,label,min,max,step])=>{const sizeFieldError=key==="displayWidthAdjustment" ? widthSizeError : key==="displayHeightAdjustment" ? heightSizeError : "";return <div key={key}><label>{label}<input ref={key==="anchorX" ? firstField : undefined} type="number" required min={fieldMinimum(key,min)} max={max} step={step || "any"} value={values[key]} aria-invalid={Boolean(fieldIssues[key] || sizeFieldError) || undefined} aria-describedby={[fieldIssues[key] && `${fieldErrorId}-${key}`,sizeFieldError && `${sizeErrorId}-${key}`].filter(Boolean).join(" ") || undefined} onChange={e=>edit({...values,[key]:e.target.value})}/></label>{fieldIssues[key] && <small id={`${fieldErrorId}-${key}`}>{fieldMinimum(key,min)}~{max}{step===1 ? "의 정수" : " 사이"}로 입력하세요.</small>}</div>;})}
    <label>그림자 형태<select value={values.shadowShape} onChange={e=>edit({...values,shadowShape:e.target.value})}>
      <option value="circle">원형</option><option value="rectangle">사각형</option></select></label></div>
    {widthSizeError && <p id={`${sizeErrorId}-displayWidthAdjustment`} role="alert">{widthSizeError}</p>}
    {heightSizeError && <p id={`${sizeErrorId}-displayHeightAdjustment`} role="alert">{heightSizeError}</p>}
    <button type="button" onClick={()=>edit({...values,displayWidthAdjustment:0,displayHeightAdjustment:0})}>크기 보정 초기화</button>
    {changed && <button type="button" onClick={event=>{restoreCancelFocus.current=document.activeElement===event.currentTarget;edit(original);}}>편집 취소</button>}
    <ActionButton type="submit" buttonRef={saveButton} reasons={[!changed && "변경한 속성이 없습니다.",Object.values(fieldIssues).some(Boolean) && "범위를 벗어난 속성을 수정하세요.",sizeError && "표시 크기 보정을 수정하세요."]}>표시 속성 저장</ActionButton>
    {error && <p ref={saveErrorRef} tabIndex={-1} role="alert">{error}</p>}
  </fieldset></form>;
}

export async function buildingCommand(action,payload,{signal,onDispatch}={}){
  const bytes=new TextEncoder().encode(JSON.stringify(payload));
  const controller=new AbortController();let timedOut=false;
  const abort=()=>controller.abort();
  if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",abort,{once:true});
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  let dispatched=false;
  try{
    const digest=new Uint8Array(await untilAborted(crypto.subtle.digest("SHA-256",bytes),controller.signal));
    if(controller.signal.aborted)throw new DOMException("건물 요청이 중단됐습니다.","AbortError");
    const requestId="building-"+action+"-"+Array.from(digest,b=>b.toString(16).padStart(2,"0")).join("");
    dispatched=true;onDispatch?.();
    return await untilAborted(managementCommand("map-assets","building-"+action,{...payload,requestId},{signal:controller.signal}),controller.signal);
  }catch(error){if(timedOut)throw new Error(dispatched ? "건물 요청 응답 시간이 초과됐습니다." : "건물 요청 준비 시간이 초과됐습니다. 다시 시도하세요.");throw error;}
  finally{clearTimeout(timer);signal?.removeEventListener("abort",abort);}
}

export function BuildingRegistration({generation,busy,disabledReason,setBusy,onRegistered}){
  const [error,setError]=useState(""),[fileError,setFileError]=useState("");
  const idHelp=useId(),imageHelp=useId(),fileErrorId=useId(),disabledHelp=useId(),submitting=useRef(false),prepareRequest=useRef(null);
  const submitButton=useRef(null),errorRef=useRef(null),restoreSubmitFocus=useRef(false);
  useEffect(()=>()=>{prepareRequest.current?.abort();},[]);
  useEffect(()=>{if(!busy && error && restoreSubmitFocus.current){restoreSubmitFocus.current=false;restoreLostFocus(document,errorRef.current);}},[busy,error]);
  async function submit(event){
    event.preventDefault();
    const form=event.currentTarget,fields=new FormData(form),file=fields.get("image");
    if(busy || submitting.current)return;
    if(!file?.size || file.size>16*1024*1024){setFileError("16MiB 이하의 PNG를 선택하세요.");return;}
    submitting.current=true;
    restoreSubmitFocus.current=document.activeElement===submitButton.current;
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
  return <details onToggle={event=>{if(!event.currentTarget.open)restoreSubmitFocus.current=false;}}><summary>건물 등록{error || fileError ? " · 확인 필요" : submitting.current && busy ? " · 처리 중" : ""}</summary>{busy && disabledReason && <p id={disabledHelp}>{disabledReason}</p>}<form className="building-registration-form" onSubmit={submit}><fieldset disabled={busy} aria-describedby={busy && disabledReason ? disabledHelp : undefined}>
    <label>건물 ID<input name="texture" required pattern="town-[a-z0-9\x2d]+-v[1-9][0-9]*" placeholder="town-iseulon-house-v1" aria-describedby={idHelp}/></label>
    <small id={idHelp}>town-으로 시작하고 -v1처럼 양의 버전 번호로 끝나는 영문 소문자·숫자·하이픈 ID를 입력하세요.</small>
    <label>투명 PNG<input name="image" required type="file" accept="image/png" aria-invalid={fileError ? true : undefined} aria-describedby={[imageHelp,fileError ? fileErrorId : null].filter(Boolean).join(" ")} onChange={()=>setFileError("")}/></label>
    <small id={imageHelp}>투명 PNG · 최대 16MiB</small>
    {fileError && <p id={fileErrorId} role="alert">{fileError}</p>}
    {[["x","앵커 X",0.5],["y","앵커 Y",1]].map(([name,label,value])=><label key={name}>{label}<input name={name} type="number" required min="0" max="16" step="any" defaultValue={value}/></label>)}
    <button ref={submitButton} type="submit">건물 등록</button>{error && <p ref={errorRef} tabIndex={-1} role="alert">{error}</p>}
  </fieldset></form></details>;
}

export function BuildingAssetList({assets,selected,disabled,disabledReason,onSelect,image,revealSelection}){
  return <CardGallery items={assets.map(item=>({id:item.texture,label:item.texture}))} selected={selected} onSelect={onSelect} imageUrl={item=>image(item.id)} matches={(item,query)=>item.id.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())} label="건물" pageSize={10} pageSizeOptions={[10,20,40]} placeholder="건물 ID 검색" disabled={disabled} disabledReason={disabledReason} revealSelection={revealSelection}/>;
}

export default function BuildingEditor(){
  const busyId=useId(),dirtyId=useId(),loadingId=useId();
  const [catalog,setCatalog]=useState(null),[selected,setSelected]=useState("");
  const [revealSelection,setRevealSelection]=useState("");
  const registeredSelection=useRef("");
  const [error,setError]=useState(""),[revision,reload]=useState(0);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [uncertainSaves,setUncertainSaves]=useState([]);
  const [uncertainRetirements,setUncertainRetirements]=useState([]);
  const [dirty,setDirty]=useState(false);
  const [loading,setLoading]=useState(true),[checkedAt,setCheckedAt]=useState(null),[catalogVersion,setCatalogVersion]=useState(0);
  const reloadButton=useRef(null),listHeading=useRef(null),catalogError=useRef(null),restoreCatalogFocus=useRef(false),retiring=useRef(null),retireButton=useRef(null),restoreRetireFocus=useRef(false);
  useEffect(()=>{document.title="건물 에셋 관리";},[]);
  useEffect(()=>()=>{const request=retiring.current;retiring.current=null;request?.abort();},[]);
  useEffect(()=>{if(!busy && error && restoreRetireFocus.current){restoreRetireFocus.current=false;restoreLostFocus(document,catalogError.current);}},[busy,error]);
  function dismissUncertainty(event,setItems,id){
    if(document.activeElement===event.currentTarget)listHeading.current?.focus();
    setItems(items=>items.filter(item=>item!==id));
  }
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
        if(registeredSelection.current){if(result.assets.some(item=>item.texture===registeredSelection.current))setRevealSelection(registeredSelection.current);registeredSelection.current="";}
        setSelected(previous=>previous || result.assets[0]?.texture || "");
      }
    }).catch(problem=>{if(active)setError(timedOut ? "건물 목록 조회 시간이 초과됐습니다. 다시 읽어 주세요." : buildingCatalogError(problem));}).finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  const unavailable=loading || Boolean(error);
  const building=catalog?.assets.find(item=>item.texture===selected);
  async function retire(){
    if(busy || retiring.current || dirty || unavailable || !building || building.texture==="ward-tower-v1" || building.maps.length)return;
    const wasFocused=document.activeElement===retireButton.current;
    if(!window.confirm(building.texture+"을 건물 목록과 공용 속성에서 삭제할까요? 이미지 원본과 등록 이력은 보존됩니다."))return;
    restoreRetireFocus.current=wasFocused;
    const controller=new AbortController();retiring.current=controller;
    setBusy(true);setError("");
    try{
      const result=await buildingCommand("retire",{texture:building.texture,generation:catalog.generation},{signal:controller.signal});
      if(retiring.current!==controller)return;
      if(!validBuildingChange(result,building.texture,catalog.generation,"retire"))throw new Error("삭제 응답의 대상을 확인할 수 없습니다.");
      restoreRetireFocus.current=false;setNotice(building.texture+" 삭제 완료");refreshCatalog(document.activeElement===document.body);
    }catch(problem){if(retiring.current===controller && !controller.signal.aborted){setUncertainRetirements(items=>items.includes(building.texture) ? items : [...items,building.texture]);setError("삭제 결과를 확인하지 못했습니다. 다시 요청하기 전에 건물 목록을 다시 읽어 확인하세요. · "+requestErrorMessage(problem));}}
    finally{if(retiring.current===controller){retiring.current=null;setBusy(false);}}
  }
  const image=id=>"/management/assistant/building-image/"+encodeURIComponent(id);
  return <article className="building-editor-page"><ConversationLink/><h1>건물 에셋 관리</h1><BuildingReviewCandidate/>
    <button ref={reloadButton} type="button" disabled={busy || dirty || loading} aria-describedby={[busy && busyId,dirty && dirtyId,loading && loadingId].filter(Boolean).join(" ") || undefined} onClick={()=>refreshCatalog(document.activeElement===reloadButton.current)}>{loading ? "건물 목록 조회 중…" : "건물 목록 다시 읽기"}</button>
    {busy && <p id={busyId} role="status">건물 요청을 처리하고 있습니다.</p>}
    {dirty && <p id={dirtyId} role="status">저장하지 않은 건물 속성이 있습니다. 저장하거나 편집을 취소한 뒤 목록을 다시 읽거나 다른 건물을 선택하세요.</p>}
    {notice && <p role="status">{notice}</p>}
    {uncertainSaves.map(id=><div key={id}><p role="status">{id} 표시 속성의 저장 결과를 확인하지 못했습니다. 목록을 다시 읽고 실제 속성을 확인하세요.</p><button type="button" onClick={event=>dismissUncertainty(event,setUncertainSaves,id)}>{id} 확인 안내 닫기</button></div>)}
    {uncertainRetirements.map(id=><div key={id}><p role="status">{id} 삭제 결과를 확인하지 못했습니다. 목록을 다시 읽고 해당 건물의 삭제 여부를 확인하세요.</p><button type="button" onClick={event=>dismissUncertainty(event,setUncertainRetirements,id)}>{id} 삭제 확인 안내 닫기</button></div>)}
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p ref={catalogError} tabIndex={-1} role="alert">{error}{catalog && (catalog.assets.length ? " 아래는 마지막 조회 결과이며, 다시 확인하기 전에는 변경할 수 없습니다." : " 마지막 조회에서 등록된 건물이 없었습니다. 다시 확인하기 전에는 변경할 수 없습니다.")}</p>}
    {loading && <p id={loadingId} role="status">{catalog ? (catalog.assets.length ? "목록 조회 중입니다. 아래는 마지막 조회 결과입니다." : "목록 조회 중입니다. 마지막 조회에서 등록된 건물이 없었습니다.") : "건물 목록을 읽고 있습니다."}</p>}
    {catalog ? <><h2 ref={listHeading} tabIndex={-1}>건물 목록</h2><p>건물 {catalog.assets.length}종 · DB 세대 {catalog.generation}</p>
      <BuildingRegistration generation={catalog.generation} busy={busy || dirty || unavailable} disabledReason={busy ? "건물 요청이 끝날 때까지 기다리세요." : dirty ? "변경한 건물 속성을 저장하거나 편집을 취소하세요." : loading ? "건물 목록 확인이 끝날 때까지 기다리세요." : error ? "건물 목록을 다시 확인한 뒤 등록하세요." : ""} setBusy={setBusy} onRegistered={id=>{
        setNotice(id+" 등록 완료");setSelected(id);registeredSelection.current=id;refreshCatalog(document.activeElement===document.body);
      }}/>
      {!catalog.assets.length && !unavailable && <p>등록된 건물이 없습니다.</p>}
      {selected && !building && <p role="status">선택한 건물을 현재 목록에서 찾지 못했습니다. 다른 건물을 선택하세요.</p>}
      <BuildingAssetList assets={catalog.assets} selected={selected} disabled={busy || dirty || loading} disabledReason={busy ? "건물 요청이 끝날 때까지 기다리세요." : dirty ? "변경한 건물 속성을 저장하거나 편집을 취소하세요." : loading ? "건물 목록 확인이 끝날 때까지 기다리세요." : ""} onSelect={setSelected} image={image} revealSelection={revealSelection}/>
    </> : null}
    {building && <section><h2>{building.texture}</h2>
      <RecoverableImage key={selected+":"+catalogVersion} src={image(selected)} name={selected}/>
      <p>{building.width}×{building.height} px · 앵커 X {building.properties.anchorX} · Y {building.properties.anchorY}</p>
      <BuildingProperties key={building.texture+"/"+catalogVersion} building={building} generation={catalog.generation} busy={busy || unavailable} disabledReason={busy ? "건물 요청이 끝날 때까지 기다리세요." : loading ? "건물 목록 확인이 끝날 때까지 기다리세요." : error ? "건물 목록을 다시 확인한 뒤 속성을 편집하세요." : ""} setBusy={setBusy} onDirtyChange={setDirty}
        onSaveUncertain={id=>setUncertainSaves(items=>items.includes(id) ? items : [...items,id])}
        onSaved={id=>{setDirty(false);setNotice(id+" 표시 속성을 저장했습니다.");refreshCatalog(document.activeElement===document.body);}}/>
      <h3>사용 맵</h3>{building.maps.length ? <ul>{building.maps.map((usage,i)=><li key={i}>{usage.map} · {usage.name} · {usage.width}×{usage.height} · {usage.facing}</li>)}</ul> : <p>사용 맵 없음</p>}
      <ActionButton buttonRef={retireButton} reasons={[
        busy && "건물 요청이 끝날 때까지 기다리세요.",
        dirty && "저장하지 않은 건물 속성을 저장하거나 편집을 취소하세요.",
        loading && "건물 목록 확인이 끝날 때까지 기다리세요.",
        error && "건물 목록을 다시 확인한 후 삭제할 수 있습니다.",
        building.texture==="ward-tower-v1" && "보호된 건물은 삭제할 수 없습니다.",
        building.maps.length>0 && "사용 중인 맵의 건물 배치를 먼저 제거하세요."
      ]} onClick={retire}>선택 건물 삭제</ActionButton>
    </section>}
  </article>;
}
