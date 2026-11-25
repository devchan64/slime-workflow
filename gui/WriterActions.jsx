import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import {createConfirmationGate} from "./confirmationGate.mjs";
import {writerProposalId,readGenerationProposal} from "./generationProposal.mjs";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import JobIdentifier from "./JobIdentifier.jsx";
import ActionButton from "./ActionButton.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export function WriterUncertainReceipt({onClear,onHistory}){
  return <section><p role="status">이전 작가 작업의 접수 여부가 확인되지 않았습니다. 아래 실행 이력에서 해당 작업을 먼저 확인하세요.</p>
    <div className="choice-buttons">
    {onHistory && <button type="button" onClick={onHistory}>실행 이력 검색으로 이동</button>}
    <button type="button" onClick={onClear}>실행 이력을 확인했고 새 요청을 작성합니다</button></div></section>;
}

export function writerProposalModeLabel(mode){
  const labels={write:"작성 제안",deduplicate:"중복 검토",learn:"학습 · 색인 갱신",prepare:"환경 준비"};
  return typeof mode!=="string" || !mode.trim() ? "작업 종류 확인 불가" : Object.hasOwn(labels,mode) ? labels[mode] : mode;
}

export function WriterWorkspaceState({workspace,stale}){
  if(!workspace)return null;
  if(workspace.active_job)return <div role="status"><p>{stale ? "마지막 조회에서 진행 중인 작업" : "진행 중인 작업"}</p><JobIdentifier id={workspace.active_job} compact/></div>;
  if(stale)return <p role="status">새 준비 상태를 확인할 때까지 작업을 요청할 수 없습니다.</p>;
  return <p role="status">{!workspace.configured?"먼저 문서 폴더를 연결하세요.":!workspace.ready?"실행 환경을 준비하세요.":!workspace.trained?"문서를 학습해 검색 색인을 만드세요.":"작성과 중복 검토를 요청할 수 있습니다."}</p>;
}

export default function WriterActions({session="",onAccepted,onWorkspace,onHistory,onState,initialPrompt="",proposedMode="",proposalScope=null,hideLegend=false}) {
  const [workspace,setWorkspace]=useState(null);
  const [revision,refresh]=useState(0);
  const [prompt,setPrompt]=useState(initialPrompt);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [stateError,setStateError]=useState("");
  const [stateChecking,setStateChecking]=useState(true);
  const [stateCheckedAt,setStateCheckedAt]=useState(null);
  useEffect(()=>{onState?.({workspace,checking:stateChecking,error:stateError,checkedAt:stateCheckedAt});},[onState,workspace,stateChecking,stateError,stateCheckedAt]);
  const [review,setReview]=useState(null);
  const [proposalId,setProposalId]=useState(''),[proposalReceipt,setProposalReceipt]=useState(proposalScope?'checking':'editing');
  const [receiptChecking,setReceiptChecking]=useState(false);
  const lockId=useId(),stateCheckId=useId();
  const uncertaintyKey="writer-submit-uncertain:"+(session || "standalone");
  const [uncertain,setUncertain]=useState(()=>sessionStorage.getItem(uncertaintyKey)==="1");
  const sending=useRef(false),receiptRequest=useRef(null),reviewRequest=useRef(null),submitRequest=useRef(null),reviewEpoch=useRef(0),reviewFocusFrame=useRef(null),mounted=useRef(true),statePending=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;const current=receiptRequest.current;receiptRequest.current=null;current?.abort();const review=reviewRequest.current;reviewRequest.current=null;review?.abort();submitRequest.current?.abort();if(reviewFocusFrame.current!==null)cancelAnimationFrame(reviewFocusFrame.current);};},[]);
  const reviewRef=useRef(null),reviewTrigger=useRef(null);
  useEffect(()=>{if(review && (document.activeElement===reviewTrigger.current || document.activeElement===document.body))reviewRef.current?.focus();},[review]);
  const confirmation=useRef(null);
  if(!confirmation.current)confirmation.current=createConfirmationGate();
  const handoff=useGpuHandoff(session,"writer-agent",onAccepted,setError);
  async function checkProposalReceipt(id){
    if(receiptRequest.current)return;
    const controller=new AbortController();receiptRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);setReceiptChecking(true);
    try{
      const [receipt,handoffValue]=await untilAborted(Promise.all([
        managementCommand('hermes-agent','hermes-writer-proposal-receipt',{session_id:session,request_id:id,job_id:proposalScope.job},{signal:controller.signal}),
        managementCommand('hermes-agent','hermes-gpu-handoff-status',{session_id:session,request_id:id},{signal:controller.signal})]),controller.signal);
      if(receiptRequest.current!==controller)return;
      if(receipt.request_id!==id || receipt.service!=='writer-agent')throw new Error('작가 접수 기록이 일치하지 않습니다.');
      validateGpuHandoffStatus(handoffValue,session,id,'writer-agent');
      setError('');
      if(receipt.state==='not_found' && handoffValue.state==='not_found'){setProposalReceipt('editing');return;}
      if(receipt.state==='accepted' && /^\d{8}-\d{6}-[a-f0-9]{8}$/.test(receipt.job_id || '')){setProposalReceipt('accepted');onAccepted(receipt.job_id);return;}
      setProposalReceipt('unknown');
    }catch(problem){if(timedOut)throw new Error('접수 상태 조회 시간이 초과됐습니다. 다시 확인하세요.');throw problem;}
    finally{clearTimeout(timeout);controller.abort();if(receiptRequest.current===controller){receiptRequest.current=null;setReceiptChecking(false);}}
  }
  useEffect(()=>{
    if(!proposalScope)return;
    let active=true;
    (async()=>{try{const id=await writerProposalId(session,proposalScope.job);if(!active)return;setProposalId(id);await checkProposalReceipt(id);}catch(problem){if(active){setProposalReceipt('unknown');setError(requestErrorMessage(problem));}}})();
    return()=>{active=false;};
  },[]);
  useEffect(()=>{
    let active=true,timer,controller;
    function read(){
    statePending.current=true;setStateChecking(true);
    controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    untilAborted(managementCommand("writer-agent","writer-state",{},{signal:controller.signal}),controller.signal).then(record=>{
      if(!record || typeof record.configured!=="boolean" || typeof record.ready!=="boolean" || !Array.isArray(record.jobs) || record.jobs.some(job=>!job || typeof job.id!=="string" || typeof job.mode!=="string" || typeof job.stage!=="string" || [job.summary,job.error].some(value=>value!=null && typeof value!=="string")) || (record.active_job!=null && typeof record.active_job!=="string") || (record.configured && (typeof record.trained!=="boolean" || [record.document_root,record.index_path,record.state_root].some(value=>typeof value!=="string"))))throw new Error("작업 준비 상태 응답 형식을 확인할 수 없습니다.");
      if(active){setStateError("");setWorkspace(record);setStateCheckedAt(new Date());onWorkspace?.(record.jobs || []);if(record.active_job)timer=setTimeout(read,3000); }
    }).catch(problem=>{if(active)setStateError(timedOut ? "작업 준비 상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}).finally(()=>{clearTimeout(timeout);if(active){statePending.current=false;setStateChecking(false);}});
    }
    read();
    return ()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[revision,onWorkspace]);
  function reload() {
    statePending.current=true;setStateChecking(true);setStateError("");
    refresh(value=>value+1);
  }
  async function submit(mode) {
    if(statePending.current || sending.current || uncertain || (proposalScope && (proposalReceipt!=='editing' || mode!==proposedMode)))return;
    reviewEpoch.current++;if(reviewFocusFrame.current!==null){cancelAnimationFrame(reviewFocusFrame.current);reviewFocusFrame.current=null;}
    const controller=new AbortController();reviewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    sending.current=true;
    reviewTrigger.current=document.activeElement;
    setBusy(true);setError("");
    try {
      if(proposalScope){const latest=await readGenerationProposal(managementCommand,proposalScope,{signal:controller.signal});if(JSON.stringify(latest)!==JSON.stringify(proposalScope.proposal))throw new Error('대화 제안이 변경되었습니다. 다시 조회하세요.');}
      const payload={mode,prompt:["prepare","learn"].includes(mode)?"":prompt.trim()};
      let bound=null;
      if(session && mode!=="prepare"){
        const context=await untilAborted(managementCommand("hermes-agent","hermes-gpu-handoff-writer-context",{session_id:session},{signal:controller.signal}),controller.signal);
        if(context.session_id!==session || !/^[a-f0-9]{64}$/.test(context.fingerprint || "") || typeof context.document_root!=="string" || typeof context.state_root!=="string")throw new Error("작가 작업공간을 확인할 수 없습니다.");
        bound={request:payload,workspace_fingerprint:context.fingerprint};
        if(await untilAborted(handoff.preview(bound,{signal:controller.signal}),controller.signal)){if(reviewRequest.current===controller)setReview({bound,documentRoot:context.document_root,stateRoot:context.state_root,handoff:true,confirmation:confirmation.current.open()});return;}
      }
      if(reviewRequest.current!==controller)return;
      setReview({bound:bound || {request:payload},documentRoot:workspace?.document_root,stateRoot:workspace?.state_root,handoff:false,confirmation:confirmation.current.open()});
    } catch(problem) {if(reviewRequest.current===controller)setError(timedOut ? "작업 검토 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}
    finally {clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;sending.current=false;reload();setBusy(false);}}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement),origin=reviewTrigger.current,epoch=reviewEpoch.current;
    confirmation.current.cancel();setReview(null);handoff.clearReview();
    if(reviewFocusFrame.current!==null)cancelAnimationFrame(reviewFocusFrame.current);
    if(restore)reviewFocusFrame.current=requestAnimationFrame(()=>{reviewFocusFrame.current=null;if(epoch===reviewEpoch.current && !reviewRequest.current && origin?.isConnected && !origin.matches(":disabled"))restoreLostFocus(document,origin);});
  }
  async function confirmHandoff(){
    if(!review || sending.current)return;
    if(!confirmation.current.claim(review.confirmation))return;
    sending.current=true;setBusy(true);setError("");
    try{
      if(proposalScope){
        const controller=new AbortController();submitRequest.current=controller;let latest;
        try{latest=await untilAborted(readGenerationProposal(managementCommand,proposalScope,{signal:controller.signal}),controller.signal);}
        finally{if(submitRequest.current===controller)submitRequest.current=null;}
        if(!mounted.current || controller.signal.aborted)return;
        if(JSON.stringify(latest)!==JSON.stringify(proposalScope.proposal))throw new Error('대화 제안이 변경되었습니다. 다시 조회하세요.');setProposalReceipt('checking');
      }
      if(review.handoff){await handoff.approve(review.bound,proposalScope ? proposalId : undefined);if(proposalScope)await checkProposalReceipt(proposalId);}
      else if(proposalScope){
        const record=await managementCommand('hermes-agent','hermes-writer-proposal-submit',{session_id:session,request_id:proposalId,job_id:proposalScope.job,snapshot:proposalScope.snapshot,offset:proposalScope.offset,request:review.bound,confirmed:true});
        if(record.state!=='accepted' || !/^\d{8}-\d{6}-[a-f0-9]{8}$/.test(record.job_id || ''))throw new Error('작가 제안 접수 상태를 확인하세요.');
        setProposalReceipt('accepted');onAccepted(record.job_id);
      }
      else{
        sessionStorage.setItem(uncertaintyKey,"1");setUncertain(true);
        const controller=new AbortController();submitRequest.current=controller;let timedOut=false;
        const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);let record;
        try{record=await untilAborted(managementCommand("writer-agent","writer-submit",review.bound.request,{signal:controller.signal}),controller.signal);}
        catch(problem){if(timedOut)throw new Error("작업 접수 응답 시간이 초과됐습니다.");throw problem;}
        finally{clearTimeout(timeout);if(submitRequest.current===controller)submitRequest.current=null;}
        if(!/^\d{8}-\d{6}-[a-f0-9]{8}$/.test(record?.id || ""))throw new Error("접수 ID를 확인할 수 없습니다.");
        sessionStorage.removeItem(uncertaintyKey);setUncertain(false);
        onAccepted(record.id);
      }
    }
    catch(problem){if(mounted.current){if(proposalScope)setProposalReceipt('unknown');setError(requestErrorMessage(problem)+(review.handoff?" · GPU 양도 상태를 확인하세요.":" · 다시 요청하기 전에 실행 이력을 확인하세요."));}}
    finally{if(mounted.current){handoff.clearReview();setReview(null);sending.current=false;setBusy(false);reload();}}
  }
  const prepare=Boolean(!stateChecking && !stateError && workspace?.configured && !workspace.active_job);
  const learn=prepare && workspace.ready;
  const trained=learn && workspace.trained;
  const readinessReason=stateChecking ? "작업 준비 상태를 확인하고 있습니다." : stateError ? "작업 준비 상태를 다시 확인하세요." : !workspace ? "작업 준비 상태를 확인하고 있습니다." : !workspace.configured ? "문서 폴더 설정과 접근 권한을 확인하세요." : workspace.active_job ? "진행 중인 작업이 끝날 때까지 기다리세요." : "";
  const learnReason=readinessReason || (!workspace?.ready ? "먼저 실행 환경을 준비하세요." : "");
  const trainedReason=learnReason || (!workspace?.trained ? "먼저 문서를 학습해 검색 색인을 만드세요." : "");
  const lockReason=busy ? "작가 요청을 확인하고 있습니다. 처리가 끝날 때까지 기다리세요." : uncertain ? "아래 실행 이력에서 이전 요청의 접수 여부를 확인한 뒤 새 요청을 작성하세요." : review ? "아래 작업 확인에서 요청을 확인하거나 입력 수정을 선택하세요." : handoff.id ? "GPU 양도 상태를 확인하고 상태 창을 닫은 뒤 입력을 수정하세요." : proposalScope && proposalReceipt!=='editing' ? "대화 제안의 접수 상태를 확인하세요." : "";
  return <>{handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="writer-agent" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
  {uncertain && <WriterUncertainReceipt onHistory={onHistory} onClear={()=>{sessionStorage.removeItem(uncertaintyKey);setUncertain(false);}}/>}
  {proposalScope && proposalReceipt!=='editing' && <section role="status"><p>제안 접수 상태: {receiptChecking || proposalReceipt==='checking'?'확인 중':proposalReceipt==='accepted'?'접수 확인됨':'확인 필요'}. 같은 제안은 다시 접수하지 않습니다.</p><button type="button" disabled={!proposalId || busy || receiptChecking} onClick={()=>checkProposalReceipt(proposalId).catch(problem=>{if(mounted.current){setProposalReceipt('unknown');setError(requestErrorMessage(problem));}})}>접수 상태 다시 확인</button></section>}
  {lockReason && <p id={lockId} role="status">{lockReason}</p>}
  <fieldset disabled={Boolean(lockReason)} aria-describedby={lockReason ? lockId : undefined}><legend className={hideLegend ? "generator-visually-hidden" : undefined}>작가 작업 요청</legend>
    <button type="button" aria-disabled={stateChecking} aria-describedby={stateChecking ? stateCheckId : undefined} onClick={()=>{if(statePending.current)return;setError("");reload();}}>준비 상태 새로고침</button>
    {stateChecking && <p id={stateCheckId} role="status">작업 준비 상태를 확인하고 있습니다.{workspace && " 아래는 마지막 조회 결과입니다."}</p>}
    {stateError && <p role="alert">작업 준비 상태를 확인하지 못했습니다 · {stateError}{workspace && " · 표시된 상태는 마지막으로 확인한 정보입니다."}</p>}
    {stateCheckedAt && <p>마지막 준비 상태 확인 · <time dateTime={stateCheckedAt.toISOString()}>{stateCheckedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time>{(stateChecking || stateError) && " · 이전 관측"}</p>}
    {(stateError.includes("문서 폴더") || (workspace && !workspace.configured)) && <p>운영자에게 <code>.local/writer-agent/workspace.yaml</code>의 문서 폴더 설정과 접근 권한 확인을 요청하세요.</p>}
    {workspace?.configured && <details><summary>문서·색인·기록 경로</summary><pre>{[workspace.document_root,workspace.index_path,workspace.state_root].join("\n")}</pre></details>}
    <WriterWorkspaceState workspace={workspace} stale={Boolean(stateChecking || stateError)}/>
    <div className="writer-action-row"><ActionButton reasons={[!prepare && readinessReason,proposalScope && "대화 제안에서는 환경 준비를 요청할 수 없습니다."]} onClick={()=>submit("prepare")}>환경 준비</ActionButton>
    <ActionButton reasons={[!learn && learnReason,proposalScope && proposedMode!=='learn' && "대화에서 제안한 작업을 선택하세요."]} onClick={()=>submit("learn")}>학습 · 색인 갱신</ActionButton></div>
    <label>작성 지시 또는 중복 검토 범위<textarea maxLength={6000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
    {proposedMode && <p>대화에서 제안한 작업: {writerProposalModeLabel(proposedMode)}. 내용을 확인하고 해당 버튼을 선택하세요.</p>}
    <div className="writer-action-row"><ActionButton reasons={[!trained && trainedReason,!prompt.trim() && "작성 지시를 입력하세요.",proposalScope && proposedMode!=='write' && "대화에서 제안한 작업을 선택하세요."]} onClick={()=>submit("write")}>작성 제안 요청</ActionButton>
    <ActionButton reasons={[!trained && trainedReason,proposalScope && proposedMode!=='deduplicate' && "대화에서 제안한 작업을 선택하세요."]} onClick={()=>submit("deduplicate")}>중복 검토 요청</ActionButton></div>
    <p>중복 검토 범위를 비우면 전체 색인을 검사합니다.</p>
    {error && <p role="alert">{error}</p>}
  </fieldset>
  {review && <section ref={reviewRef} tabIndex={-1} className="fun-request-review writer-request-review" aria-label="작가 작업 확인"><h2>{review.handoff?"작가 작업과 GPU 양도 확인":"작가 작업 확인"}</h2>
    <p>문서 작업공간 · {review.documentRoot || "확인 불가"}</p><p>색인·작업 기록 · {review.stateRoot || "확인 불가"}</p><p>작업 · {({prepare:"환경 준비",learn:"문서 색인 갱신",write:"작성 제안",deduplicate:"중복 검토"})[review.bound.request.mode]}</p>
    {review.bound.request.prompt && <ReviewPrompt label="요청 내용" text={review.bound.request.prompt}/>}
    <p>{review.handoff && "동의하면 현재 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 위 작업을 실행합니다. 작업 종료 후 Qwen 3.8을 다시 적재합니다. "}작성 제안은 문서에 자동 적용하지 않습니다.</p>
    <GenerationReviewActions busy={busy} onCancel={cancelReview} onConfirm={confirmHandoff} confirmLabel={review.handoff?"해제·작업·재적재에 동의":"확인 후 작업 요청"}/>
  </section>}</>;
}
