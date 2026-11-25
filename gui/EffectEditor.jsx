import SnapshotStatus from "./SnapshotStatus.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {validEffectDetail,validWaypointFrames} from "./effectDetailValidation.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {effectAlignmentBoundsIssue} from "./effectAlignmentBounds.mjs";
import RecoverableImage from "./RecoverableImage.jsx";
import {validEffectList} from "./effectListValidation.mjs";
import {initialMotionPlaying} from "./initialMotionPlaying.mjs";
import {validEffectSaveResponse,effectSaveNotice,effectSaveFailure} from "./effectSaveResponse.mjs";
import {choiceLabels} from "./choiceLabels.mjs";

import {drawAlignment} from "./drawAlignment.js";

export function PreviewError({error,retryButton,onRetry}){
  if(!error)return null;
  return <div><p role="alert">{error} 문제가 계속되면 이펙트 상세를 다시 불러오세요. 편집 중인 내용이 있다면 먼저 저장하거나 취소하세요.</p><button ref={retryButton} type="button" onClick={onRetry}>미리보기 다시 불러오기</button></div>;
}

export function AlignmentPreview({detail,values}){
  const canvas=useRef(null),retryButton=useRef(null),restoreFocus=useRef(false);
  const frameHelpId=useId();
  const [play,setPlay]=useState(initialMotionPlaying),[frame,setFrame]=useState(0),[host,setHost]=useState(true),[guides,setGuides]=useState(true);
  const [status,setStatus]=useState(""),[error,setError]=useState(""),[loading,setLoading]=useState(false),[revision,retry]=useState(0);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;restoreLostFocus(document,(error ? retryButton : canvas).current);}},[loading,error]);
  useEffect(()=>{
    const element=canvas.current;
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;element.effectPreviewRevision++;controller.abort();},30000);
    setError("");setLoading(true);setStatus("정렬 미리보기를 불러오는 중입니다.");
    untilAborted(drawAlignment(element,detail,values,play,frame,host,guides),controller.signal)
      .then(message=>{if(active)setStatus(message);})
      .catch(problem=>{if(active){setStatus("");setError(timedOut ? "정렬 미리보기 조회 시간이 초과됐습니다." : problem?.message || "정렬 미리보기를 불러오지 못했습니다.");}})
      .finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();element.effectPreviewRevision++;};
  },[detail,values,play,frame,host,guides,revision]);
  return <fieldset className="effect-preview-controls"><legend>정렬 미리보기</legend>
    <label><input type="checkbox" checked={play} onChange={e=>{if(!e.target.checked)setFrame(canvas.current?.effectDisplayedFrame ?? frame);setPlay(e.target.checked);}}/>애니메이션 재생</label>
    <label>정지 프레임<input type="range" min="0" max={values.frames.length-1} value={frame} disabled={play} aria-valuetext={`${frame+1} / ${values.frames.length} 프레임`} aria-describedby={frameHelpId}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    <small id={frameHelpId}>{play ? "재생을 멈추면 프레임을 선택할 수 있습니다." : `${frame+1} / ${values.frames.length} 프레임`}</small>
    {detail.hostImage && <label><input type="checkbox" checked={host} onChange={e=>setHost(e.target.checked)}/>빌보드 표시</label>}
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역 가이드</label>
    <canvas ref={canvas} tabIndex={-1} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="정렬 미리보기" aria-busy={loading}/>
    <p role="status">{status}</p>
    <PreviewError error={error} retryButton={retryButton} onRetry={()=>{restoreFocus.current=document.activeElement===retryButton.current;retry(value=>value+1);}}/>
  </fieldset>;
}

const sides=["왼쪽","위쪽","오른쪽","아래쪽"];

export function AlignmentRectangleInputs({row,group,helpId,error,errorId,onChange}){
  const invalid=error?.group===group;
  return sides.map((side,index)=><label key={side}>{side}<input type="number" required min="0" max="1" step="any" aria-invalid={invalid || undefined} aria-describedby={[helpId,invalid ? errorId : null].filter(Boolean).join(" ")} value={row[index]}
    onChange={event=>onChange(row.map((value,position)=>index===position ? event.target.value : value))}/></label>);
}

export function WaypointPreview({detail}){
  const canvas=useRef(null),displayedFrame=useRef(0),retryButton=useRef(null),restoreFocus=useRef(false);
  const frameHelpId=useId();
  const [playing,setPlaying]=useState(initialMotionPlaying),[frame,setFrame]=useState(0),[guides,setGuides]=useState(true);
  const [error,setError]=useState(""),[loading,setLoading]=useState(true),[revision,retry]=useState(0);
  const frames=detail.animationMetadata?.frames;
  const validFrames=validWaypointFrames(frames,detail.document.frames);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;restoreLostFocus(document,(error ? retryButton : canvas).current);}},[loading,error]);
  useEffect(()=>{
    if(!validFrames)return;
    const sheet=new Image(),ctx=canvas.current.getContext("2d");
    let active=true,request,expired=false;
    setError("");setLoading(true);ctx.clearRect(0,0,640,640);
    const timeout=setTimeout(()=>{expired=true;if(active){setLoading(false);setError("웨이포인트 시트 조회 시간이 초과됐습니다.");}},30000);
    sheet.onload=()=>{
      if(!active || expired)return;
      clearTimeout(timeout);
      setLoading(false);
      const start=performance.now();
      function draw(time){
        if(!active)return;
        const index=playing?Math.floor((time-start)*6/1000)%frames.length:frame;
        displayedFrame.current=index;
        const {rect,anchor}=frames[index];
        const left=320-anchor.x*420/rect.width,top=440-anchor.y*420/rect.height;
        ctx.fillStyle="#182329";ctx.fillRect(0,0,640,640);
        ctx.drawImage(sheet,rect.x,rect.y,rect.width,rect.height,left,top,420,420);
        if(guides){
          ctx.strokeStyle="#ff70be";ctx.strokeRect(left,top,420,420);
          ctx.strokeStyle="#ff4545";ctx.beginPath();ctx.moveTo(310,440);ctx.lineTo(330,440);
          ctx.moveTo(320,430);ctx.lineTo(320,450);ctx.stroke();
        }
        ctx.fillStyle="white";ctx.fillText(`프레임 ${index+1}/${frames.length}`,16,24);
        if(playing)request=requestAnimationFrame(draw);
      }
      draw(start);
    };
    sheet.onerror=()=>{clearTimeout(timeout);if(active && !expired){setLoading(false);setError("웨이포인트 시트를 읽지 못했습니다.");}};
    sheet.src=detail.sheetImage;
    return ()=>{active=false;clearTimeout(timeout);sheet.onload=null;sheet.onerror=null;cancelAnimationFrame(request);};
  },[detail,frames,playing,frame,guides,revision,validFrames]);
  if(!validFrames)return <p role="alert">프레임 정보를 확인할 수 없습니다. 원본을 확인한 뒤 상세를 다시 불러오세요.</p>;
  return <fieldset className="effect-preview-controls"><legend>웨이포인트 미리보기</legend>
    <label><input type="checkbox" checked={playing} onChange={e=>{if(!e.target.checked)setFrame(displayedFrame.current);setPlaying(e.target.checked);}}/>재생</label>
    <label>프레임<input type="range" min="0" max={frames.length-1} value={frame} disabled={playing} aria-valuetext={`${frame+1} / ${frames.length} 프레임`} aria-describedby={frameHelpId}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    <small id={frameHelpId}>{playing ? "재생을 멈추면 프레임을 선택할 수 있습니다." : `${frame+1} / ${frames.length} 프레임`}</small>
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역과 앵커 표시</label>
    <canvas ref={canvas} tabIndex={-1} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="웨이포인트 애니메이션" aria-busy={loading}/>
    {loading && <p role="status">웨이포인트 시트를 불러오는 중입니다.</p>}
    <PreviewError error={error} retryButton={retryButton} onRetry={()=>{restoreFocus.current=document.activeElement===retryButton.current;retry(value=>value+1);}}/>
  </fieldset>;
}

export function WaypointReplacement({detail,onSaved,onDirtyChange,onBusyChange}){
  const [source,setSource]=useState(JSON.stringify(detail.document,null,2));
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [jsonError,setJsonError]=useState(false),helpId=useId(),errorId=useId();
  const previewRequest=useRef(null),sourceRevision=useRef(0),submitting=useRef(false),details=useRef(null),reviewButton=useRef(null),confirmButton=useRef(null),reviewHeading=useRef(null),errorRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>{const request=previewRequest.current;previewRequest.current=null;request?.abort();},[]);
  useEffect(()=>{onDirtyChange(source!==JSON.stringify(detail.document,null,2));},[source,detail,onDirtyChange]);
  useEffect(()=>{onBusyChange(busy);},[busy,onBusyChange]);
  useEffect(()=>{
    if(busy || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(details.current?.open)restoreLostFocus(document,(error ? errorRef : pending ? reviewHeading : reviewButton).current);
  },[busy,pending,error]);
  async function review(){
    if(busy || previewRequest.current)return;
    restoreFocus.current=document.activeElement===reviewButton.current;
    const controller=new AbortController(),revisionAtStart=sourceRevision.current;previewRequest.current=controller;let timedOut=false,parsed=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setError("");setJsonError(false);setBusy(true);setPending(null);
    try{
      const draft={id:detail.document.id,revision:detail.revision,effect:JSON.parse(source)};
      parsed=true;
      const result=await untilAborted(managementCommand("hermes-agent","hermes-waypoint-preview",{draft},{signal:controller.signal}),controller.signal);
      if(previewRequest.current!==controller)return;
      if(sourceRevision.current!==revisionAtStart)throw new Error("검토 중 입력이 변경되었습니다. 다시 확인하세요.");
      if(!/^[a-f0-9]{64}$/.test(result?.review_sha256 || "") || result.after?.id!==draft.effect.id || [result.after?.image,result.after?.animation,result.note].some(value=>typeof value!=="string"))throw new Error("교체 검토 결과를 확인할 수 없습니다.");
      setPending({draft,result,requestId:crypto.randomUUID()});
    }catch(problem){if(previewRequest.current===controller && (!controller.signal.aborted || timedOut)){const invalidJson=!timedOut && !parsed && problem instanceof SyntaxError;setJsonError(invalidJson);setError(timedOut ? "교체 검토 시간이 초과됐습니다. 다시 시도하세요." : invalidJson?"새 이펙트 JSON 형식을 확인하세요.":requestErrorMessage(problem));}}
    finally{clearTimeout(timeout);if(previewRequest.current===controller){previewRequest.current=null;setBusy(false);}}
  }
  async function confirm(){
    if(submitting.current || busy || !pending)return;
    restoreFocus.current=document.activeElement===confirmButton.current;
    submitting.current=true;
    setError("");setBusy(true);
    try{
      const result=await managementCommand("hermes-agent","hermes-waypoint-replace",{
        request_id:pending.requestId,draft:pending.draft,review_sha256:pending.result.review_sha256
      });
      if(result.state!=="completed" || result.id!==pending.draft.effect.id)throw new Error("교체 결과 확인 필요 · 접수 "+pending.requestId);
      onSaved(result.id);
    }catch(problem){setError("교체 결과를 확인하지 못했습니다. 원본과 접수 기록을 확인하세요 · 접수 "+pending.requestId+" · "+requestErrorMessage(problem));}
    finally{submitting.current=false;setBusy(false);}
  }
  return <details ref={details} className="effect-waypoint-replacement" onToggle={event=>{if(!event.currentTarget.open)restoreFocus.current=false;}}><summary>웨이포인트 이펙트 교체</summary><fieldset disabled={busy}>
    <label>새 이펙트 JSON<textarea rows={10} value={source} aria-invalid={jsonError || undefined} aria-describedby={[helpId,jsonError ? errorId : null].filter(Boolean).join(" ")} onChange={e=>{sourceRevision.current++;setSource(e.target.value);setPending(null);setError("");setJsonError(false);}}/></label>
    <p id={helpId}>JSON 형식으로 편집한 뒤 교체 내용을 확인하세요.</p>
    <button ref={reviewButton} type="button" onClick={review}>교체 내용 확인</button>
    {pending && <section><h3 ref={reviewHeading} tabIndex={-1}>{detail.document.id} → {pending.result.after.id}</h3>
      <p>이미지 · {pending.result.after.image}</p><p>애니메이션 · {pending.result.after.animation}</p>
      <p>{pending.result.note}</p><button ref={confirmButton} type="button" onClick={confirm}>확인 후 교체</button>
      <button type="button" onClick={event=>{const restore=document.activeElement===event.currentTarget;setPending(null);if(restore)requestAnimationFrame(()=>{if(details.current?.open)restoreLostFocus(document,reviewButton.current);});}}>취소</button></section>}
    {error && <p ref={errorRef} tabIndex={-1} id={jsonError ? errorId : undefined} role="alert">{error}</p>}
  </fieldset>{busy && <p role="status">웨이포인트 요청을 처리하고 있습니다.</p>}</details>;
}

export function Alignment({detail,onDirtyChange,onBusyChange}){
  const [values,setValues]=useState(detail.document.alignment);
  const [savedValues,setSavedValues]=useState(detail.document.alignment);
  const [revision,setRevision]=useState(detail.revision),[busy,setBusy]=useState(false),[message,setMessage]=useState(""),[saveError,setSaveError]=useState(false);
  const [inputError,setInputError]=useState(null);
  const submitting=useRef(false),saveButton=useRef(null),messageRef=useRef(null),inputErrorRef=useRef(null),restoreSaveFocus=useRef(false),restoreInputFocus=useRef(false);
  const coordinatesHelpId=useId(),inputErrorId=useId(),alphaErrorId=useId(),busyHelpId=useId();
  useEffect(()=>{onDirtyChange(JSON.stringify(values)!==JSON.stringify(savedValues));},[values,savedValues,onDirtyChange]);
  useEffect(()=>{onBusyChange(busy);},[busy,onBusyChange]);
  useEffect(()=>{if(!busy && message && restoreSaveFocus.current){restoreSaveFocus.current=false;restoreLostFocus(document,messageRef.current);}},[busy,message]);
  useEffect(()=>{if(inputError && restoreInputFocus.current){restoreInputFocus.current=false;if(document.activeElement===saveButton.current || document.activeElement===document.body)inputErrorRef.current?.focus();}},[inputError]);
  function rectangle(key,index){
    const row=key==="target"?values.target:values.frames[index];
    const group=key==="target" ? "target" : `frame:${index}`;
    return <AlignmentRectangleInputs row={row} group={group} helpId={coordinatesHelpId} error={inputError} errorId={inputErrorId} onChange={next=>{
      if(!saveError)setMessage("");setInputError(previous=>previous?.group===group ? null : previous);setValues({...values,[key]:key==="target"?next:values.frames.map((v,j)=>index===j?next:v)});
    }}/>;
  }
  async function save(event){
    event.preventDefault();if(submitting.current)return;
    const alignment={...values,target:values.target.map(Number),alpha:Number(values.alpha),
      frames:values.frames.map(row=>row.map(v=>Math.round(Number(v)*100)/100))};
    const originalIssue=effectAlignmentBoundsIssue(values),roundedIssue=originalIssue ? null : effectAlignmentBoundsIssue(alignment);
    if(originalIssue || roundedIssue){const issue=originalIssue || roundedIssue;if(!saveError)setMessage("");restoreInputFocus.current=document.activeElement===saveButton.current;setInputError({...issue,message:issue.message+(roundedIssue ? " 프레임 좌표는 소수 둘째 자리로 저장됩니다." : "")+" 저장하지 않았습니다."});return;}
    restoreSaveFocus.current=document.activeElement===saveButton.current;
    submitting.current=true;setBusy(true);setMessage("");setSaveError(false);setInputError(null);
    let dispatched=false;
    try{
      const requestId=crypto.randomUUID();dispatched=true;
      const result=await managementCommand("map-assets","effect-save",{id:detail.document.id,expectedRevision:revision,requestId,alignment});
      if(!validEffectSaveResponse(result))throw new Error("저장 응답의 상태·리비전·세대를 확인할 수 없습니다.");
      setRevision(result.revision);setValues(alignment);setSavedValues(alignment);setMessage(effectSaveNotice(result));
    }catch(problem){setSaveError(true);setMessage(effectSaveFailure(problem,dispatched));}
    finally{submitting.current=false;setBusy(false);}
  }
  const alphaInvalid=String(values.alpha).trim()==="" || !Number.isFinite(Number(values.alpha)) || Number(values.alpha)<0 || Number(values.alpha)>1;
  return <form className="effect-alignment-form" onSubmit={save}><fieldset disabled={busy} aria-busy={busy} aria-describedby={[inputError && inputErrorId,busy && busyHelpId].filter(Boolean).join(" ") || undefined}><legend>공용 이펙트 정렬</legend>
    <p id={coordinatesHelpId}>좌표는 0부터 1까지의 비율입니다. 왼쪽은 오른쪽보다, 위쪽은 아래쪽보다 작아야 합니다.</p>
    {inputError && <p ref={inputErrorRef} tabIndex={-1} id={inputErrorId} role="alert">{inputError.message}</p>}
    <fieldset className="effect-rectangle"><legend>대상 영역</legend>{rectangle("target")}</fieldset>
    <div><label>불투명도<input type="number" min="0" max="1" step="any" required aria-invalid={alphaInvalid || undefined} aria-describedby={alphaInvalid ? alphaErrorId : undefined} value={values.alpha} onChange={e=>{if(!saveError)setMessage("");setValues({...values,alpha:e.target.value});}}/></label>{alphaInvalid && <small id={alphaErrorId}>0~1 사이로 입력하세요.</small>}</div>
    {values.frames.map((_,index)=><fieldset className="effect-rectangle" key={index}><legend>{index+1}번 프레임</legend>{rectangle("frames",index)}</fieldset>)}
    <AlignmentPreview detail={detail} values={values}/><button ref={saveButton} type="submit">정렬 저장</button></fieldset>{busy && <p id={busyHelpId} role="status">이펙트 정렬을 저장 중입니다. 완료될 때까지 기다리세요.</p>}{message && <p ref={messageRef} tabIndex={-1} role={saveError ? "alert" : "status"}>{message}</p>}</form>;
}

export default function EffectEditor(){
  const dirtyHelpId=useId(),selectionHelpId=useId();
  const [notice,setNotice]=useState("");
  const [effects,setEffects]=useState([]),[selected,select]=useState(""),[detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[revision,reload]=useState(0);
  const [detailLoading,setDetailLoading]=useState(false);
  const [dirty,setDirty]=useState(false),[editorBusy,setEditorBusy]=useState(false),[editorVersion,setEditorVersion]=useState(0);
  const detailRequest=useRef(null),listPending=useRef(true),selectRef=useRef(null),reloadRef=useRef(null),loadRef=useRef(null),detailHeading=useRef(null),errorRef=useRef(null),restorePickerFocus=useRef("");
  useEffect(()=>{document.title="이펙트 좌표 검수";},[]);
  useEffect(()=>{
    if(busy || !restorePickerFocus.current)return;
    const target=restorePickerFocus.current;restorePickerFocus.current="";
    const element=error ? errorRef.current : target==="detail" && detail ? detailHeading.current : selectRef.current?.disabled ? reloadRef.current : selectRef.current;
    restoreLostFocus(document,element);
  },[busy,error,detail,dirty,editorBusy]);
  useEffect(()=>()=>{const request=detailRequest.current;detailRequest.current=null;request?.abort();},[]);
  useEffect(()=>{
    let active=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
    listPending.current=true;setBusy(true);setError("");
    untilAborted(managementCommand("map-assets","effect-list",{},{signal:controller.signal}),controller.signal).then(result=>{
      if(!validEffectList(result))throw new Error("이펙트 목록 응답을 확인할 수 없습니다.");
      if(active){setEffects(result.effects);select(old=>old || result.effects[0]?.id || "");}
    }).catch(problem=>{if(active)setError(problem?.name==="AbortError" ? "이펙트 목록 조회 시간이 초과됐습니다. 목록을 새로고침하세요." : problem instanceof TypeError ? "이펙트 목록 서버에 연결하지 못했습니다. 목록을 새로고침하세요." : problem?.message || "이펙트 목록을 불러오지 못했습니다. 목록을 새로고침하세요.");}).finally(()=>{clearTimeout(timeout);if(active){listPending.current=false;setBusy(false);}});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  async function load(){
    if(busy || listPending.current || editorBusy || dirty || detailRequest.current || !effects.some(item=>item.id===selected))return;
    if(document.activeElement===loadRef.current)restorePickerFocus.current="detail";
    setBusy(true);setDetailLoading(true);setError("");
    const controller=new AbortController();detailRequest.current=controller;
    const timeout=setTimeout(()=>controller.abort(),30000);
    try{
      const result=await untilAborted(managementCommand("map-assets","effect-load",{id:selected},{signal:controller.signal}),controller.signal);
      if(!validEffectDetail(result,selected))throw new Error("선택한 이펙트의 상세 응답을 확인할 수 없습니다.");
      if(detailRequest.current===controller){setDetail(result);setEditorVersion(value=>value+1);}
    }catch(problem){if(detailRequest.current===controller)setError(problem?.name==="AbortError" ? "이펙트 조회 시간이 초과됐습니다. 다시 불러오세요." : problem instanceof TypeError ? "이펙트 서버에 연결하지 못했습니다. 다시 불러오세요." : problem?.message || "이펙트 상세를 불러오지 못했습니다. 다시 불러오세요.");}
    finally{clearTimeout(timeout);if(detailRequest.current===controller){detailRequest.current=null;setDetailLoading(false);setBusy(false);}}
  }
  const choices=choiceLabels(effects.map(item=>[item.name,item.id]));
  return <article className="effect-editor-page"><h1>이펙트 좌표 검수</h1><fieldset className="effect-editor-picker" disabled={busy || editorBusy}><legend>이펙트 선택</legend>
    <select ref={selectRef} aria-label="이펙트" aria-describedby={dirty ? dirtyHelpId : !effects.length ? selectionHelpId : undefined} disabled={dirty || !effects.length} value={selected} onChange={e=>{select(e.target.value);setDetail(null);}}>
      {selected && !effects.some(item=>item.id===selected) && <option value={selected}>{selected} · 현재 목록에 없음</option>}
      {!effects.length && <option value="">{busy ? "목록 조회 중…" : error ? "이펙트 목록 조회 실패" : "선택할 이펙트가 없습니다"}</option>}
      {choices.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select>
    <button ref={reloadRef} type="button" onClick={()=>{if(listPending.current || detailRequest.current || busy || editorBusy)return;listPending.current=true;setBusy(true);if(document.activeElement===reloadRef.current)restorePickerFocus.current="list";reload(n=>n+1);}}>목록 새로고침</button><button ref={loadRef} type="button" disabled={dirty || !effects.some(item=>item.id===selected)} aria-describedby={dirty ? dirtyHelpId : !effects.some(item=>item.id===selected) ? selectionHelpId : undefined} onClick={load}>선택 이펙트 불러오기</button>{!dirty && !effects.some(item=>item.id===selected) && <p id={selectionHelpId}>목록을 불러온 뒤 이펙트를 선택하세요.</p>}</fieldset>
    {busy && <p role="status">{detailLoading ? "이펙트 상세를 불러오는 중입니다." : "이펙트 목록을 불러오는 중입니다."}</p>}
    {error && <p ref={errorRef} tabIndex={-1} role="alert">{error}</p>}
    {error && effects.length>0 && <p role="status">이전 조회의 목록{detail ? "과 열려 있는 상세를" : "을"} 유지합니다.</p>}
    {selected && !busy && !error && !effects.some(item=>item.id===selected) && <p role="status">선택한 이펙트가 현재 목록에 없습니다. 다른 이펙트를 선택할 수 있습니다.</p>}
    {notice && <p role="status">{notice}</p>}
    {detailLoading && detail && <p role="status">상세를 다시 읽는 중입니다. 아래는 마지막 조회 결과입니다.</p>}
    {dirty && <p id={dirtyHelpId} role="status">저장하지 않은 편집이 있습니다. 다른 이펙트를 선택하려면 저장하거나 편집을 취소하세요. <button type="button" disabled={editorBusy} onClick={event=>{if(document.activeElement===event.currentTarget)restorePickerFocus.current="list";setDirty(false);setEditorVersion(n=>n+1);}}>편집 취소</button></p>}
    {detail && <section><h2 ref={detailHeading} tabIndex={-1}>{detail.document.name}</h2><p>{detail.document.renderer} · {detail.document.frames}프레임</p><fieldset disabled={detailLoading} style={{border:0,padding:0,margin:0}} aria-label="이펙트 상세와 편집">
      <RecoverableImage src={detail.sheetImage} name="이펙트 시트" maxHeight="none"/>
      {detail.hostImage && <RecoverableImage src={detail.hostImage} name="빌보드" maxHeight="none"/>}
      {detail.document.renderer==="waypoint-animation"?<><WaypointPreview detail={detail}/><WaypointReplacement key={editorVersion} detail={detail} onDirtyChange={setDirty} onBusyChange={setEditorBusy} onSaved={id=>{if(document.activeElement===document.body)restorePickerFocus.current="list";setDirty(false);setEditorBusy(false);setBusy(true);setNotice("웨이포인트 교체 완료 · "+id);select(id);setDetail(null);reload(n=>n+1);}}/></>:<Alignment key={editorVersion} detail={detail} onDirtyChange={setDirty} onBusyChange={setEditorBusy}/>}
    </fieldset></section>}
    <SnapshotStatus/>
  </article>;
}
