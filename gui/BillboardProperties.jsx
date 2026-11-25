import BillboardGroundPreview from "./BillboardGroundPreview.jsx";
import ActionButton from "./ActionButton.jsx";
import BillboardCrop from "./BillboardCrop.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import {billboardSaveNotice} from "./billboardSaveNotice.mjs";

export const billboardPropertyLabels={anchorX:"앵커 X",anchorY:"앵커 Y",displayHeight:"표시 높이",groundFootprintColumns:"점유 열",groundFootprintRows:"점유 행",
  shadowOffsetColumn:"그림자 열 이동",shadowOffsetRow:"그림자 행 이동",shadowScaleX:"그림자 가로 배율",shadowScaleY:"그림자 세로 배율",
  billboardPlacementAnchor:"배치 기준",billboardBlocksMovement:"통행 차단"};
const labels=billboardPropertyLabels;
export function invalidDisplayHeight(value){return value!=="" && (!Number.isFinite(Number(value)) || Number(value)<0.005 || Number(value)>1024);}
export function invalidFootprint(value){return value!=="" && (!Number.isInteger(Number(value)) || Number(value)<1 || Number(value)>8);}
export function invalidShadowOffset(value){return value!=="" && (!Number.isFinite(Number(value)) || Number(value)<-4 || Number(value)>4);}
export function shadowScaleMinimum(key,version){return version===2 ? 0.001 : key==="shadowScaleY" ? 0.05 : 0.1;}
export function invalidShadowScale(value,key,version){return value!=="" && (!Number.isFinite(Number(value)) || Number(value)<shadowScaleMinimum(key,version) || Number(value)>4);}
export function invalidBillboardAnchor(value,automatic){return value!=="" && (!Number.isFinite(Number(value)) || Number(value)<(automatic ? -16 : 0) || Number(value)>(automatic ? 16 : 1));}
export function billboardPreviewError(problem){const message=requestErrorMessage(problem);return message.includes("변경 없는 에셋은 제외하세요") ? "반올림 후 기존 값과 같아 변경할 내용이 없습니다. 다른 값을 입력하거나 편집을 취소하세요." : message;}

export function validBillboardReview(result,texture){
  const object=value=>value && typeof value==="object" && !Array.isArray(value);
  return Boolean(result && typeof result.token==="string" && result.token && /^[a-f0-9]{64}$/.test(result.review_sha256 || "") && Array.isArray(result.changes) && result.changes.length===1 && result.changes[0]?.texture===texture && object(result.changes[0].before) && object(result.changes[0].after) && Array.isArray(result.maps) && result.maps.every(map=>typeof map==="string") && Array.isArray(result.map_warnings) && result.map_warnings.every(warning=>warning && typeof warning.map==="string" && typeof warning.message==="string") && typeof result.note==="string");
}

export function BillboardReviewSummary({result}){
  const change=result.changes[0];
  return <><p>에셋: {change.texture}</p><ResultTable table={{title:"공용 속성 변경",summary:result.note,columns:["속성","기존","변경 후"],
    rows:Object.entries(change.after).filter(([key,value])=>value!==change.before[key])
      .map(([key,value])=>[labels[key] || key,String(change.before[key] ?? ""),String(value)])}}/>
    <p>영향 맵 · {result.maps.join(", ") || "없음"}</p>
    {result.map_warnings.map((warning,index)=><p key={index}>{warning.map} · {warning.message}</p>)}
  </>;
}

export function BillboardNumericField({label,value,required,error,onChange}){
  return <div><label>{label}<input type="number" step="any" required={required} aria-invalid={error ? true : undefined} aria-describedby={error?.[0]} value={value ?? ""} onChange={event=>onChange(event.target.value)}/></label>{error && <span id={error[0]}>{error[1]}</span>}</div>;
}

export default function BillboardProperties({texture,onCrop,onDirtyChange=()=>{}}){
  const [source,setSource]=useState(null),[edits,setEdits]=useState({}),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const readRequest=useRef(null),saving=useRef(false),reviewRef=useRef(null),reviewTrigger=useRef(null),loadButton=useRef(null),restoreLoadFocus=useRef(false),restoreReviewFocus=useRef(false);
  const placementReasonId=useId(),reloadReasonId=useId(),busyReasonId=useId(),heightErrorId=useId(),columnsErrorId=useId(),rowsErrorId=useId(),shadowColumnErrorId=useId(),shadowRowErrorId=useId(),scaleXErrorId=useId(),scaleYErrorId=useId(),anchorXErrorId=useId(),anchorYErrorId=useId(),emptyErrorId=useId();
  useEffect(()=>{if(review && (document.activeElement===reviewTrigger.current || document.activeElement===document.body))reviewRef.current?.focus({preventScroll:true});},[review]);
  useEffect(()=>{if(!busy && restoreLoadFocus.current){restoreLoadFocus.current=false;if(document.activeElement===document.body && loadButton.current && !loadButton.current.disabled)loadButton.current.focus({preventScroll:true});}},[busy,source,notice,edits]);
  useEffect(()=>{if(!busy && restoreReviewFocus.current){restoreReviewFocus.current=false;if(notice && document.activeElement===document.body && reviewTrigger.current?.isConnected && !reviewTrigger.current.disabled)reviewTrigger.current.focus({preventScroll:true});}},[busy,notice,review]);
  useEffect(()=>()=>readRequest.current?.abort(),[]);
  async function read(command,payload){
    const controller=new AbortController();readRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{return await untilAborted(managementCommand("hermes-agent",command,payload,{signal:controller.signal}),controller.signal);}
    catch(problem){if(timedOut)throw new Error("조회 시간이 초과됐습니다. 다시 시도하세요.");throw problem;}
    finally{clearTimeout(timeout);if(readRequest.current===controller)readRequest.current=null;}
  }
  async function load(){
    if(busy || readRequest.current)return;
    restoreLoadFocus.current=document.activeElement===loadButton.current;
    setBusy(true);setNotice("");setReview(null);
    try{
      const result=await read("hermes-billboard-load",{texture});
      if(result.texture!==texture || !result.properties || !result.revision)throw new Error("선택한 에셋 속성을 확인할 수 없습니다.");
      setSource(result);setEdits({});onDirtyChange(false);
    }catch(problem){if(problem?.name!=="AbortError")setNotice(requestErrorMessage(problem));}
    finally{setBusy(false);}
  }
  function edit(key,value){
    const next={...edits},original=source?.properties?.[key];
    const numeric=!key.startsWith("billboard");
    const unchanged=numeric ? String(value).trim()!=="" && original!=null && Number.isFinite(Number(value)) && Number(value)===original : value===(key==="billboardBlocksMovement" ? original ?? false : original ?? "");
    if(unchanged)delete next[key];else next[key]=value;
    setEdits(next);onDirtyChange(Object.keys(next).length>0);setReview(null);setNotice("");
  }
  async function preview(event){
    event.preventDefault();if(busy)return;reviewTrigger.current=document.activeElement;restoreReviewFocus.current=true;setBusy(true);setNotice("");setReview(null);
    try{
      if(Object.entries(edits).some(([key,value])=>!key.startsWith("billboard") && String(value).trim()===""))throw new Error("비어 있는 숫자 속성을 입력하세요.");
      if(Object.hasOwn(edits,"displayHeight") && invalidDisplayHeight(edits.displayHeight))throw new Error("표시 높이는 0.005부터 1024까지 입력하세요. 저장 시 소수 둘째 자리로 반올림됩니다.");
      if(["groundFootprintColumns","groundFootprintRows"].some(key=>Object.hasOwn(edits,key) && invalidFootprint(edits[key])))throw new Error("점유 열과 행은 각각 1부터 8까지의 정수여야 합니다.");
      if(["shadowOffsetColumn","shadowOffsetRow"].some(key=>Object.hasOwn(edits,key) && invalidShadowOffset(edits[key])))throw new Error("그림자 열과 행 이동은 각각 -4부터 4까지여야 합니다.");
      if(["shadowScaleX","shadowScaleY"].some(key=>Object.hasOwn(edits,key) && invalidShadowScale(edits[key],key,source.initial ? 2 : source.properties.shadowSizeVersion)))throw new Error("그림자 배율의 입력 범위를 확인하세요.");
      if(["anchorX","anchorY"].some(key=>Object.hasOwn(edits,key) && invalidBillboardAnchor(edits[key],source.initial || ["tile-intersection","tile-bottom-center"].includes(source.properties.billboardAnchorMode))))throw new Error("앵커 좌표의 입력 범위를 확인하세요.");
      const values=source.initial?{...source.properties}:{};
      for(const [key,raw] of Object.entries(edits)){
        const value=key==="billboardPlacementAnchor" || key==="billboardBlocksMovement"?raw:Number(raw);
        if(value!==source.properties[key])values[key]=value;
      }
      if(!Object.keys(values).length)throw new Error("변경할 속성을 입력하세요.");
      const draft={revision:source.revision,changes:[{texture,values}]};
      const result=await read("hermes-billboard-preview",{draft});
      if(!validBillboardReview(result,texture))throw new Error("검토 결과가 선택한 에셋과 다르거나 형식이 올바르지 않습니다.");
      setReview({result,draft,id:crypto.randomUUID().replaceAll("-","")});
    }catch(problem){if(problem?.name!=="AbortError")setNotice(billboardPreviewError(problem));}
    finally{setBusy(false);}
  }
  async function save(){
    if(saving.current || !review)return;
    saving.current=true;
    setBusy(true);setNotice("");
    try{
      const record=await managementCommand("hermes-agent","hermes-billboard-save",{request_id:review.id,draft:review.draft,
        token:review.result.token,review_sha256:review.result.review_sha256});
      if(record.state!=="completed" || !record.saved)throw new Error("저장 결과 확인 필요 · 접수 "+review.id);
      setReview(null);setSource(null);setEdits({});onDirtyChange(false);setNotice(billboardSaveNotice(record,review.id));
    }catch(problem){setNotice(problem.message);}
    finally{saving.current=false;setBusy(false);}
  }
  const hasEdits=Object.keys(edits).length>0;
  const properties=source?{...source.properties,...edits}:{};
  const heightInvalid=Object.hasOwn(edits,"displayHeight") && invalidDisplayHeight(edits.displayHeight);
  const automaticPlacement=source?.initial || ["tile-intersection","tile-bottom-center"].includes(properties.billboardAnchorMode);
  const shadowVersion=source?.initial ? 2 : properties.shadowSizeVersion;
  const fieldError=key=>Object.hasOwn(edits,key) && String(edits[key]).trim()==="" ? [`${emptyErrorId}-${key}`,"값을 입력하세요."] : key==="displayHeight" && heightInvalid ? [heightErrorId,"0.005부터 1024까지 입력하세요. 소수 둘째 자리로 반올림됩니다."] : key==="groundFootprintColumns" && Object.hasOwn(edits,key) && invalidFootprint(edits[key]) ? [columnsErrorId,"1부터 8까지의 정수여야 합니다."] : key==="groundFootprintRows" && Object.hasOwn(edits,key) && invalidFootprint(edits[key]) ? [rowsErrorId,"1부터 8까지의 정수여야 합니다."] : key==="shadowOffsetColumn" && Object.hasOwn(edits,key) && invalidShadowOffset(edits[key]) ? [shadowColumnErrorId,"-4부터 4까지 입력하세요."] : key==="shadowOffsetRow" && Object.hasOwn(edits,key) && invalidShadowOffset(edits[key]) ? [shadowRowErrorId,"-4부터 4까지 입력하세요."] : ["shadowScaleX","shadowScaleY"].includes(key) && Object.hasOwn(edits,key) && invalidShadowScale(edits[key],key,shadowVersion) ? [key==="shadowScaleX" ? scaleXErrorId : scaleYErrorId,`${shadowScaleMinimum(key,shadowVersion)}부터 4까지 입력하세요.`] : ["anchorX","anchorY"].includes(key) && Object.hasOwn(edits,key) && invalidBillboardAnchor(edits[key],automaticPlacement) ? [key==="anchorX" ? anchorXErrorId : anchorYErrorId,automaticPlacement ? "-16부터 16까지 입력하세요." : "0부터 1까지 입력하세요."] : null;
  return <section><button ref={loadButton} type="button" disabled={busy || hasEdits} aria-describedby={[busy && busyReasonId,hasEdits && reloadReasonId].filter(Boolean).join(" ") || undefined} onClick={load}>{source?"공용 속성 다시 불러오기":"공용 속성 불러오기"}</button>
    {busy && <p id={busyReasonId} role="status">빌보드 요청을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {hasEdits && <p id={reloadReasonId} role="status">변경 사항이 있습니다. 다시 불러오려면 편집을 취소하거나 저장하세요. <button type="button" disabled={busy} onClick={event=>{restoreLoadFocus.current=document.activeElement===event.currentTarget;setEdits({});onDirtyChange(false);setReview(null);setNotice("");}}>편집 취소</button></p>}
    {source && <form className="billboard-properties-form" onSubmit={preview}><fieldset disabled={busy} aria-describedby={busy ? busyReasonId : undefined}><legend>빌보드 공용 속성</legend>
      {source.initial && <p>최초 설정 초안 · 기본 점유 1×1, 표시 높이 128px입니다. 원본을 확인한 뒤 검토하세요.</p>}
      <p>앵커·높이·그림자 이동은 소수 둘째 자리로 반올림됩니다. {shadowVersion===2 ? "그림자 배율은 소수 여섯째 자리로 반올림됩니다." : "그림자 배율도 소수 둘째 자리로 반올림됩니다."}</p>
      <div className="billboard-properties-grid">{Object.keys(labels).filter(key=>!key.startsWith("billboard")).map(key=><BillboardNumericField key={key} label={labels[key]} value={properties[key]} required={key in edits} error={fieldError(key)} onChange={value=>edit(key,value)}/>)}
      <label>배치 기준<select disabled={automaticPlacement} aria-describedby={automaticPlacement ? placementReasonId : undefined} value={automaticPlacement?(Number(properties.anchorY)<0.5?"top":"bottom"):(properties.billboardPlacementAnchor ?? "")} onChange={e=>edit("billboardPlacementAnchor",e.target.value)}>
        <option value="" disabled>미지정</option><option value="top">위쪽</option><option value="bottom">아래쪽</option></select></label>
      {automaticPlacement && <p id={placementReasonId}>현재 앵커 설정에 따라 배치 기준이 자동으로 결정됩니다.</p>}
      <label className="billboard-checkbox"><input type="checkbox" checked={properties.billboardBlocksMovement ?? false} onChange={e=>edit("billboardBlocksMovement",e.target.checked)}/>통행 차단</label></div>
      <BillboardGroundPreview source={source} edits={edits}/>
      <ActionButton type="submit" reasons={[!source.initial && !hasEdits && "변경한 속성이 없습니다.",Object.keys(labels).filter(key=>!key.startsWith("billboard")).some(key=>fieldError(key)) && "숫자 속성의 입력을 확인하세요."]}>변경 검토</ActionButton>
      {review && <section ref={reviewRef} tabIndex={-1} aria-label="빌보드 속성 변경 확인"><BillboardReviewSummary result={review.result}/>
        <button type="button" onClick={save}>검토한 속성 저장</button><button type="button" onClick={()=>{const focused=document.activeElement;setReview(null);requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===focused) && reviewTrigger.current?.isConnected)reviewTrigger.current.focus();});}}>취소</button></section>}
    </fieldset></form>}
    {source && !source.initial && !hasEdits && <BillboardCrop key={source.revision} source={source} busy={busy} setBusy={setBusy}
      onSaved={({restoreFocus}={})=>{restoreLoadFocus.current=Boolean(restoreFocus);setSource(null);setReview(null);setNotice("원본 크롭 저장 완료");onCrop();}}/>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
