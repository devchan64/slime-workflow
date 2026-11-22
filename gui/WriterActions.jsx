import React, {useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import {createConfirmationGate} from "./confirmationGate.mjs";
import {writerProposalId,readGenerationProposal} from "./generationProposal.mjs";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";

export function WriterUncertainReceipt({onClear}){
  return <section role="status"><p>이전 작가 작업의 접수 여부가 확인되지 않았습니다. 아래 실행 이력에서 해당 작업을 먼저 확인하세요.</p>
    <button type="button" onClick={onClear}>실행 이력을 확인했고 새 요청을 작성합니다</button></section>;
}

export default function WriterActions({session="",onAccepted,onWorkspace,initialPrompt="",proposedMode="",proposalScope=null}) {
  const [workspace,setWorkspace]=useState(null);
  const [revision,refresh]=useState(0);
  const [prompt,setPrompt]=useState(initialPrompt);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [stateError,setStateError]=useState("");
  const [review,setReview]=useState(null);
  const [proposalId,setProposalId]=useState(''),[proposalReceipt,setProposalReceipt]=useState(proposalScope?'checking':'editing');
  const uncertaintyKey="writer-submit-uncertain:"+(session || "standalone");
  const [uncertain,setUncertain]=useState(()=>sessionStorage.getItem(uncertaintyKey)==="1");
  const sending=useRef(false);
  const confirmation=useRef(null);
  if(!confirmation.current)confirmation.current=createConfirmationGate();
  const handoff=useGpuHandoff(session,"writer-agent",onAccepted,setError);
  async function checkProposalReceipt(id){
    const [receipt,handoffValue]=await Promise.all([
      managementCommand('hermes-agent','hermes-writer-proposal-receipt',{session_id:session,request_id:id,job_id:proposalScope.job}),
      managementCommand('hermes-agent','hermes-gpu-handoff-status',{session_id:session,request_id:id})]);
    if(receipt.request_id!==id || receipt.service!=='writer-agent')throw new Error('작가 접수 기록이 일치하지 않습니다.');
    validateGpuHandoffStatus(handoffValue,session,id,'writer-agent');
    if(receipt.state==='not_found' && handoffValue.state==='not_found'){setProposalReceipt('editing');return;}
    if(receipt.state==='accepted' && /^\d{8}-\d{6}-[a-f0-9]{8}$/.test(receipt.job_id || '')){setProposalReceipt('accepted');onAccepted(receipt.job_id);return;}
    setProposalReceipt('unknown');
  }
  useEffect(()=>{
    if(!proposalScope)return;
    let active=true;
    (async()=>{try{const id=await writerProposalId(session,proposalScope.job);if(!active)return;setProposalId(id);await checkProposalReceipt(id);}catch(problem){if(active){setProposalReceipt('unknown');setError(problem.message);}}})();
    return()=>{active=false;};
  },[]);
  useEffect(()=>{
    let active=true,timer;
    function read(){
    managementCommand("writer-agent","writer-state").then(record=>{
      if(active){setStateError("");setWorkspace(record);onWorkspace?.(record.jobs || []);if(record.active_job)timer=setTimeout(read,3000); }
    }).catch(problem=>{if(active)setStateError(problem.message);});
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[revision,onWorkspace]);
  function reload() {
    setWorkspace(null);setStateError("");
    refresh(value=>value+1);
  }
  async function submit(mode) {
    if(sending.current || uncertain || (proposalScope && (proposalReceipt!=='editing' || mode!==proposedMode)))return;
    sending.current=true;
    setBusy(true);setError("");
    try {
      if(proposalScope){const latest=await readGenerationProposal(managementCommand,proposalScope);if(JSON.stringify(latest)!==JSON.stringify(proposalScope.proposal))throw new Error('대화 제안이 변경되었습니다. 다시 조회하세요.');}
      const payload={mode,prompt:["prepare","learn"].includes(mode)?"":prompt.trim()};
      let bound=null;
      if(session && mode!=="prepare"){
        const context=await managementCommand("hermes-agent","hermes-gpu-handoff-writer-context",{session_id:session});
        if(context.session_id!==session || !/^[a-f0-9]{64}$/.test(context.fingerprint || "") || typeof context.document_root!=="string" || typeof context.state_root!=="string")throw new Error("작가 작업공간을 확인할 수 없습니다.");
        bound={request:payload,workspace_fingerprint:context.fingerprint};
        if(await handoff.preview(bound)){setReview({bound,documentRoot:context.document_root,stateRoot:context.state_root,handoff:true,confirmation:confirmation.current.open()});return;}
      }
      setReview({bound:bound || {request:payload},documentRoot:workspace?.document_root,stateRoot:workspace?.state_root,handoff:false,confirmation:confirmation.current.open()});
    } catch(problem) {setError(problem.message);}
    finally {sending.current=false;reload();setBusy(false);}
  }
  async function confirmHandoff(){
    if(!review || sending.current)return;
    if(!confirmation.current.claim(review.confirmation))return;
    sending.current=true;setBusy(true);setError("");
    try{
      if(proposalScope){const latest=await readGenerationProposal(managementCommand,proposalScope);if(JSON.stringify(latest)!==JSON.stringify(proposalScope.proposal))throw new Error('대화 제안이 변경되었습니다. 다시 조회하세요.');setProposalReceipt('checking');}
      if(review.handoff){await handoff.approve(review.bound,proposalScope ? proposalId : undefined);if(proposalScope)await checkProposalReceipt(proposalId);}
      else if(proposalScope){
        const record=await managementCommand('hermes-agent','hermes-writer-proposal-submit',{session_id:session,request_id:proposalId,job_id:proposalScope.job,snapshot:proposalScope.snapshot,offset:proposalScope.offset,request:review.bound,confirmed:true});
        if(record.state!=='accepted' || !/^\d{8}-\d{6}-[a-f0-9]{8}$/.test(record.job_id || ''))throw new Error('작가 제안 접수 상태를 확인하세요.');
        setProposalReceipt('accepted');onAccepted(record.job_id);
      }
      else{
        sessionStorage.setItem(uncertaintyKey,"1");setUncertain(true);
        const record=await managementCommand("writer-agent","writer-submit",review.bound.request);
        if(!/^\d{8}-\d{6}-[a-f0-9]{8}$/.test(record?.id || ""))throw new Error("접수 ID를 확인할 수 없습니다.");
        sessionStorage.removeItem(uncertaintyKey);setUncertain(false);
        onAccepted(record.id);
      }
    }
    catch(problem){if(proposalScope)setProposalReceipt('unknown');setError(problem.message+(review.handoff?" · GPU 양도 상태를 확인하세요.":" · 다시 요청하기 전에 실행 이력을 확인하세요."));}
    finally{handoff.clearReview();setReview(null);sending.current=false;setBusy(false);reload();}
  }
  const prepare=Boolean(!stateError && workspace?.configured && !workspace.active_job);
  const learn=prepare && workspace.ready;
  const trained=learn && workspace.trained;
  return <>{handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="writer-agent" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
  {uncertain && <WriterUncertainReceipt onClear={()=>{sessionStorage.removeItem(uncertaintyKey);setUncertain(false);}}/>}
  {proposalScope && proposalReceipt!=='editing' && <section role="status"><p>제안 접수 상태: {proposalReceipt==='checking'?'확인 중':proposalReceipt==='accepted'?'접수 확인됨':'확인 필요'}. 같은 제안은 다시 접수하지 않습니다.</p><button type="button" disabled={!proposalId || busy} onClick={()=>checkProposalReceipt(proposalId).catch(problem=>{setProposalReceipt('unknown');setError(problem.message);})}>접수 상태 다시 확인</button></section>}
  <fieldset disabled={busy || uncertain || Boolean(review) || Boolean(handoff.id) || Boolean(proposalScope && proposalReceipt!=='editing')}><legend>작가 작업 요청</legend>
    <button onClick={()=>{setError("");reload();}}>준비 상태 새로고침</button>
    {!workspace && !stateError && <p role="status">작업 준비 상태를 확인하고 있습니다.</p>}
    {stateError && <p role="alert">작업 준비 상태를 확인하지 못했습니다 · {stateError}{workspace && " · 표시된 상태는 마지막으로 확인한 정보입니다."}</p>}
    {workspace?.configured && <details><summary>문서·색인·기록 경로</summary><pre>{[workspace.document_root,workspace.index_path,workspace.state_root].join("\n")}</pre></details>}
    {workspace && <p role="status">{workspace.active_job?"진행 중인 작업 "+workspace.active_job:
      !workspace.configured?"먼저 문서 폴더를 연결하세요.":!workspace.ready?"실행 환경을 준비하세요.":
      !workspace.trained?"문서를 학습해 검색 색인을 만드세요.":"작성과 중복 검토를 요청할 수 있습니다."}</p>}
    <button disabled={!prepare || Boolean(proposalScope)} onClick={()=>submit("prepare")}>환경 준비</button>
    <button disabled={!learn || Boolean(proposalScope && proposedMode!=='learn')} onClick={()=>submit("learn")}>학습 · 색인 갱신</button>
    <label>작성 지시 또는 중복 검토 범위<textarea maxLength={6000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
    {proposedMode && <p>대화에서 제안한 작업: {({write:"작성 제안",deduplicate:"중복 검토",learn:"학습 · 색인 갱신",prepare:"환경 준비"})[proposedMode] || proposedMode}. 내용을 확인하고 해당 버튼을 선택하세요.</p>}
    <button disabled={!trained || !prompt.trim() || Boolean(proposalScope && proposedMode!=='write')} onClick={()=>submit("write")}>작성 제안 요청</button>
    <button disabled={!trained || Boolean(proposalScope && proposedMode!=='deduplicate')} onClick={()=>submit("deduplicate")}>중복 검토 요청</button>
    <p>중복 검토 범위를 비우면 전체 색인을 검사합니다.</p>
    {error && <p role="alert">{error}</p>}
  </fieldset>
  {review && <section aria-label="작가 작업 확인"><h2>{review.handoff?"작가 작업과 GPU 양도 확인":"작가 작업 확인"}</h2>
    <p>문서 작업공간 · {review.documentRoot || "확인 불가"}</p><p>색인·작업 기록 · {review.stateRoot || "확인 불가"}</p><p>작업 · {({prepare:"환경 준비",learn:"문서 색인 갱신",write:"작성 제안",deduplicate:"중복 검토"})[review.bound.request.mode]}</p>
    {review.bound.request.prompt && <><h3>요청 내용</h3><p>{review.bound.request.prompt}</p></>}
    <p>{review.handoff && "동의하면 현재 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 위 작업을 실행합니다. 작업 종료 후 Qwen 3.8을 다시 적재합니다. "}작성 제안은 문서에 자동 적용하지 않습니다.</p>
    <GenerationReviewActions busy={busy} onCancel={()=>{confirmation.current.cancel();setReview(null);handoff.clearReview();}} onConfirm={confirmHandoff} confirmLabel={review.handoff?"해제·작업·재적재에 동의":"확인 후 작업 요청"}/>
  </section>}</>;
}
