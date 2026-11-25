import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import {validKeyframeCatalogPage} from "./keyframeCatalogPage.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import RecoverableImage from "./RecoverableImage.jsx";
import {duplicateKeyframeFrames} from "./duplicateKeyframeFrames.mjs";
import {validKeyframeBatchResult} from "./keyframeBatchValidation.mjs";
import ActionButton from "./ActionButton.jsx";

export function KeyframePagination({page,loading,error,reasonId,onMove}){
  if(!(page.offset>0 || page.next_offset!=null))return null;
  const disabled=loading || Boolean(error);
  return <nav className="keyframe-catalog-pagination" aria-label="키프레임 목록 페이지">
    {disabled && <p id={reasonId}>{loading ? "목록 조회가 끝나면 페이지를 이동할 수 있습니다." : "목록을 다시 조회한 뒤 페이지를 이동하세요."}</p>}
    {page.offset>0 && <button type="button" disabled={disabled} aria-describedby={disabled ? reasonId : undefined} onClick={event=>onMove({offset:Math.max(0,page.offset-20),snapshot:page.snapshot},event)}>이전 키프레임</button>}
    {page.next_offset!=null && <button type="button" disabled={disabled} aria-describedby={disabled ? reasonId : undefined} onClick={event=>onMove({offset:page.next_offset,snapshot:page.snapshot},event)}>다음 키프레임</button>}
  </nav>;
}

export function KeyframeActions({row,selected,loading,loadingReasonId,disabled,disabledReasonId,choose,add,onPreview}){
  return <div className="keyframe-actions"><button type="button" disabled={loading} aria-describedby={loading ? loadingReasonId : undefined} aria-expanded={selected===row.id} aria-label={row.id+(selected===row.id?" 미리보기 닫기":" 미리보기 열기")} onClick={onPreview}>{selected===row.id?"미리보기 닫기":"미리보기"}</button>{choose && <button type="button" disabled={loading} aria-describedby={loading ? loadingReasonId : undefined} aria-label={row.id+" 입력에 추가"} onClick={()=>choose("Kimodo 키프레임",row.id)}>입력에 추가</button>}
    <button type="button" aria-label={row.id+" 배치에 추가"} aria-describedby={[disabledReasonId,loading && loadingReasonId].filter(Boolean).join(" ") || undefined} disabled={disabled || loading} onClick={event=>add(row.id,row.tag,event.currentTarget)}>배치에 추가</button></div>;
}

function Preview({id}){
  const [result,setResult]=useState(null),[error,setError]=useState(""),[attempt,setAttempt]=useState(0);
  const retryRef=useRef(null),resultRef=useRef(null),restoreFocus=useRef(false),retryPending=useRef(true);
  useEffect(()=>{if(restoreFocus.current && (error || result)){restoreFocus.current=false;restoreLostFocus(document,(error ? retryRef : resultRef).current);}},[error,result]);
  useEffect(()=>{
    let active=true,timedOut=false;
    const controller=new AbortController(),timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    retryPending.current=true;setError("");setResult(null);
    untilAborted(managementCommand("hermes-agent","hermes-kimodo-keyframe-preview",{keyframe_id:id},{signal:controller.signal}),controller.signal).then(value=>{
      if(value?.id!==id || typeof value.image_base64!=="string" || !value.image_base64 || typeof value.sha256!=="string" || !/^[a-f0-9]{64}$/.test(value.sha256))throw new Error("선택한 키프레임을 확인할 수 없습니다.");
      if(active)setResult(value);
    }).catch(problem=>{if(active)setError(timedOut ? "원본 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}).finally(()=>{clearTimeout(timeout);if(active)retryPending.current=false;});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[id,attempt]);
  if(error)return <div><p role="alert">{error}</p><button ref={retryRef} type="button" onClick={()=>{if(retryPending.current)return;retryPending.current=true;restoreFocus.current=document.activeElement===retryRef.current;setError("");setAttempt(value=>value+1);}}>원본 다시 불러오기</button></div>;
  if(!result)return <p role="status">원본 확인 중…</p>;
  return <figure ref={resultRef} tabIndex={-1}><RecoverableImage src={"data:image/png;base64,"+result.image_base64} name={id+" 키프레임"} maxHeight="none"/>
    <figcaption>{id} · PNG SHA-256 <code>{result.sha256}</code></figcaption></figure>;
}

function SearchResults({query,choose,add,disabled,disabledReason,sectionRef}){
  const [cursor,setCursor]=useState({}),[page,setPage]=useState(null);
  const [error,setError]=useState(""),[selected,select]=useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const disabledReasonId=useId(),pageReasonId=useId(),loadingReasonId=useId();
  const previewRef=useRef(null),triggerRef=useRef(null),previewFocusFrame=useRef(null),listHeading=useRef(null),errorRef=useRef(null),pageOrigin=useRef(null),restorePageFocus=useRef(false),pageTransition=useRef(true);
  useEffect(()=>()=>{if(previewFocusFrame.current!==null)cancelAnimationFrame(previewFocusFrame.current);},[]);
  useEffect(()=>{if(selected && triggerRef.current && (document.activeElement===triggerRef.current || document.activeElement===document.body)){previewRef.current?.focus({preventScroll:true});previewRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[selected]);
  useEffect(()=>{if(!loading && restorePageFocus.current){restorePageFocus.current=false;if(document.activeElement===document.body || document.activeElement===pageOrigin.current)(error ? errorRef : listHeading).current?.focus();}},[loading,error,page]);
  function closePreview(){const restore=previewRef.current?.contains(document.activeElement);select("");if(previewFocusFrame.current!==null)cancelAnimationFrame(previewFocusFrame.current);if(restore)previewFocusFrame.current=requestAnimationFrame(()=>{previewFocusFrame.current=null;restoreLostFocus(document,triggerRef.current);});}
  function changePage(next,event){if(pageTransition.current)return;pageTransition.current=true;setLoading(true);pageOrigin.current=event.currentTarget;restorePageFocus.current=document.activeElement===event.currentTarget;setCursor(next);}
  useEffect(()=>{
    let active=true,deadline,timedOut=false;
    const controller=new AbortController();
    pageTransition.current=true;setLoading(true);setError("");
    const timer=setTimeout(()=>{
      deadline=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      untilAborted(managementCommand("hermes-agent","hermes-kimodo-keyframes",{query,limit:20,...cursor},{signal:controller.signal}),controller.signal)
        .then(result=>{
          if(!validKeyframeCatalogPage(result,cursor))throw new Error("키프레임 목록을 확인할 수 없습니다.");
          if(active){pageTransition.current=false;setPage(result);setReceivedAt(new Date());select("");setLoading(false);}
        })
        .catch(problem=>{if(active){pageTransition.current=false;setError(timedOut ? "키프레임 목록 조회 시간이 초과됐습니다." : requestErrorMessage(problem));setLoading(false);}}).finally(()=>clearTimeout(deadline));
    },200);
    return ()=>{active=false;clearTimeout(timer);clearTimeout(deadline);controller.abort();};
  },[query,cursor]);
  return <section ref={sectionRef} tabIndex={-1} className="keyframe-catalog-search" aria-label="Kimodo 키프레임 검색">
    {disabledReason && <p id={disabledReasonId}>{disabledReason}</p>}
    {error && <div><p ref={errorRef} tabIndex={-1} role="alert">{error}{page && " 이전 조회 결과를 유지합니다."}</p><button type="button" onClick={event=>changePage({},event)}>처음부터 다시 조회</button></div>}
    {loading && page && <p id={loadingReasonId} role="status">새 목록 조회 중 · 아래는 이전 결과이며 조회가 끝나면 선택할 수 있습니다.</p>}
    {!error && !page && <p role="status">키프레임 조회 중…</p>}
    {page && <><p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p><h3 ref={listHeading} tabIndex={-1}>등록 키프레임</h3><p>검색 결과 {page.total}개{page.items.length>0 && ` · ${page.offset+1}–${page.offset+page.items.length}번째`}</p>
      {page.items.length===0 && <p>검색 조건에 맞는 키프레임이 없습니다.</p>}
      <ul className="keyframe-catalog-list">{page.items.map(row=><li key={row.id}>
        <strong>{row.tag || "키프레임"}</strong><p>원본 프레임 · {row.source_frame}</p>
        <p className="keyframe-id">ID · <code>{row.id}</code></p>
        <KeyframeActions row={row} selected={selected} loading={loading} loadingReasonId={loadingReasonId} disabled={disabled} disabledReasonId={disabledReason ? disabledReasonId : undefined} choose={choose} add={add} onPreview={event=>{triggerRef.current=event.currentTarget;if(selected===row.id)closePreview();else select(row.id);}}/>
      </li>)}</ul>
      {page.note && <p>{page.note}</p>}
      <KeyframePagination page={page} loading={loading} error={error} reasonId={pageReasonId} onMove={changePage}/>
      {selected && <section ref={previewRef} tabIndex={-1} aria-label="선택한 키프레임 미리보기"><button type="button" onClick={closePreview}>미리보기 닫기</button><Preview key={selected} id={selected}/></section>}</>}
  </section>;
}

export default function KeyframeCatalog({query,choose,apply,initialFrames="",initialRows=[]}){
  const [rows,setRows]=useState(initialRows),[frames,setFrames]=useState(initialFrames);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[review,setReview]=useState(null);
  const duplicateErrorId=useId(),validationBusyId=useId(),duplicateFrames=duplicateKeyframeFrames(rows);
  const placementRef=useRef(null),searchRef=useRef(null),focusPlacement=useRef(null),focusRemoval=useRef(null),validationRequest=useRef(null),inputRevision=useRef(0),validateButton=useRef(null),validationError=useRef(null),validationResult=useRef(null),restoreValidationFocus=useRef(false);
  useEffect(()=>()=>{const request=validationRequest.current;validationRequest.current=null;request?.abort();},[]);
  useEffect(()=>{if(rows.length && focusPlacement.current){const origin=focusPlacement.current;focusPlacement.current=null;if(document.activeElement===document.body || document.activeElement===origin){placementRef.current?.focus({preventScroll:true});placementRef.current?.scrollIntoView({block:"start",inline:"nearest"});}}},[rows]);
  useEffect(()=>{if(focusRemoval.current){const origin=focusRemoval.current;focusRemoval.current=null;if(document.activeElement===document.body || document.activeElement===origin)(rows.length ? placementRef : searchRef).current?.focus();}},[rows]);
  useEffect(()=>{if(!busy && restoreValidationFocus.current && (error || review)){restoreValidationFocus.current=false;restoreLostFocus(document,(error ? validationError : validationResult).current);}},[busy,error,review]);
  function edit(next){
    inputRevision.current++;setRows(next);setReview(null);setError("");
  }
  async function validate(event){
    event.preventDefault();if(validationRequest.current || duplicateFrames.size)return;
    restoreValidationFocus.current=document.activeElement===validateButton.current;
    const controller=new AbortController(),revisionAtStart=inputRevision.current;validationRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const expected=rows.map(row=>({id:row.id,frame:Number(row.frame)})).sort((a,b)=>a.frame-b.frame);
    setBusy(true);setError("");setReview(null);
    try{
      const result=await untilAborted(managementCommand("hermes-agent","hermes-kimodo-keyframe-validate",{
        frames:Number(frames),keyframes:rows.map(row=>({id:row.id,frame:Number(row.frame)}))
      },{signal:controller.signal}),controller.signal);
      if(validationRequest.current!==controller)return;
      if(inputRevision.current!==revisionAtStart)throw new Error("검증 중 배치가 변경되었습니다. 다시 검증하세요.");
      if(!validKeyframeBatchResult(result,expected)){
        throw new Error("배치 검증 결과를 확인할 수 없습니다.");
      }
      if(!controller.signal.aborted)setReview(result);
    }catch(problem){if(validationRequest.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut ? "배치 검증 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(validationRequest.current===controller){validationRequest.current=null;setBusy(false);}}
  }
  return <>
    <SearchResults key={query} sectionRef={searchRef} query={query} choose={choose} disabled={busy || rows.length>=20} disabledReason={busy ? "배치 검증이 끝나면 키프레임을 추가할 수 있습니다." : rows.length>=20 ? "키프레임은 최대 20개까지 배치할 수 있습니다." : ""}
      add={(id,tag,origin)=>{focusPlacement.current=document.activeElement===origin ? origin : null;edit([...rows,{id,tag,frame:""}]);}}/>
    {apply && <ActionButton reasons={[busy && "배치 검증이 끝날 때까지 기다리세요.",rows.length>0 && "기본 자세를 배치하려면 기존 배치를 모두 삭제하세요."]} onClick={event=>{
      const standingPose="b0000000000000000000000000000004";
      focusPlacement.current=document.activeElement===event.currentTarget ? event.currentTarget : null;
      edit([{id:standingPose,frame:1},{id:standingPose,frame:frames}]);
    }}>첫 프레임과 마지막 프레임에 기본 서기 자세 배치</ActionButton>}
    {rows.length>0 && <form ref={placementRef} className="keyframe-placement-form" tabIndex={-1} aria-label="출력 프레임 배치" onSubmit={validate}><fieldset disabled={busy} aria-describedby={busy ? validationBusyId : undefined}><legend>출력 프레임 배치</legend>
      <label>총 출력 프레임 수 (30~300)<input type="number" required min="30" max="300" value={frames}
        onChange={e=>{inputRevision.current++;setFrames(e.target.value);setReview(null);setError("");}}/></label>
      {rows.map((row,index)=><div key={index} className="keyframe-placement-row"><strong>{row.tag || "키프레임"}</strong><p>ID · <code>{row.id}</code></p><label>출력 프레임
        <input type="number" required min="1" max={frames || undefined} value={row.frame} aria-label={`${index+1}번째 ${row.tag || "키프레임"} ${row.id} 출력 프레임`} aria-invalid={duplicateFrames.has(Number(row.frame)) || undefined} aria-describedby={duplicateFrames.has(Number(row.frame)) ? duplicateErrorId : undefined}
          onChange={e=>edit(rows.map((item,i)=>i===index?{...item,frame:e.target.value}:item))}/></label>
        <button type="button" aria-label={`${row.tag || "키프레임"} ${row.id} · 출력 프레임 ${row.frame || "미입력"} · 배치 삭제`} onClick={event=>{focusRemoval.current=document.activeElement===event.currentTarget ? event.currentTarget : null;edit(rows.filter((_,i)=>i!==index));}}>삭제</button></div>)}
      {duplicateFrames.size>0 && <p id={duplicateErrorId} role="alert">출력 프레임은 중복할 수 없습니다. 각 키프레임에 서로 다른 프레임을 지정하세요.</p>}
      <button ref={validateButton} type="submit" disabled={duplicateFrames.size>0} aria-describedby={[duplicateFrames.size>0 && duplicateErrorId,busy && validationBusyId].filter(Boolean).join(" ") || undefined}>원본과 배치 검증</button>
      {error && <p ref={validationError} tabIndex={-1} role="alert">{error}</p>}
      {review && <><p ref={validationResult} tabIndex={-1} role="status">{review.placements.length}개 배치 검증 완료 · {review.note}</p>
        <ResultTable table={{title:"검증된 키프레임 배치",columns:["출력 프레임","키프레임 ID"],
          rows:review.placements.map(row=>[row.frame,row.id])}}/>
        <button type="button" onClick={()=>apply ? apply(Number(frames),review) :
          choose("Kimodo 키프레임 배치",JSON.stringify({frames:Number(frames),keyframes:review.placements}))}>
          {apply?"생성 폼에 배치 적용":"검증한 배치를 대화 입력에 추가"}</button></>}
    </fieldset>{busy && <p id={validationBusyId} role="status">키프레임 원본과 배치를 확인하고 있습니다.</p>}</form>}
  </>;
}
