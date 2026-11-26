import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {useMinimaxReportReceipt,MinimaxReportStatus,PreparedMinimaxForm} from "./useMinimaxReportReceipt.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import HermesQuestionForm from "./HermesQuestionForm.jsx";
import {readProposalPreview} from "./readProposalPreview.mjs";
import {requestErrorMessage} from "./requestError.mjs";

const imageApprovalQuestions=[{title:'이 저장된 이미지 폼으로 생성 절차를 진행할까요?',options:['승인','거절']}];

export default function FluxProposal(props) {
  return <FluxProposalForSelection key={JSON.stringify([props.session,props.job,props.snapshot,props.offset])} {...props}/>;
}
function FluxProposalForSelection({job,session,snapshot,offset,onOpenForm,onOpenFluxForm,onQuestionDraft,hasQuestionForm=false}) {
  const busyId=useId();
  const pendingFocus=useRef(false),resultRef=useRef(null),loadRequest=useRef(null);
  useEffect(()=>()=>{const current=loadRequest.current;loadRequest.current=null;current?.abort();},[session,job,snapshot,offset]);
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [prepared,setPrepared]=useState(null),[pollError,setPollError]=useState("");
  const minimaxReceipt=useMinimaxReportReceipt(proposal?.service==="minimax-h3-image" ? {session,job} : null,"minimax-h3-image");
  useEffect(()=>{if(!busy && pendingFocus.current){pendingFocus.current=false;if(proposal)restoreLostFocus(document,resultRef.current);}},[busy,proposal]);
  useEffect(()=>{
    let active=true,timer,attempts=0;const controller=new AbortController();
    async function refresh(){
      attempts++;
      try{
        const listed=await managementCommand('hermes-agent','hermes-minimax-form-list',{session_id:session},{signal:controller.signal});
        if(!Array.isArray(listed?.forms))throw new Error('접수폼 목록을 확인할 수 없습니다.');
        const matches=listed.forms.filter(form=>form.source_job_id===job && form.service==='minimax-h3-image');
        if(matches.length>1)throw new Error('같은 제안에 연결된 접수폼이 여러 개입니다. 목록을 확인하세요.');
        if(matches.length===0){if(active)setPollError('');return;}
        const checked=await verifyFluxProposal((...args)=>managementCommand(...args.slice(0,3),{signal:controller.signal}),{session,job,snapshot,offset});
        if(!active || checked.service!=="minimax-h3-image")return;
        if(active){setProposal(checked);setPrepared(matches[0]);setPollError('');}
      }catch(problem){if(active && problem?.name!=='AbortError')setPollError(problem?.message ? requestErrorMessage(problem) : '접수폼 준비 상태를 확인할 수 없습니다.');}
      finally{if(active)timer=setTimeout(refresh,attempts<12?5000:60000);}
    }
    refresh();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,job,snapshot,offset]);
  async function load(event) {
    if(busy || loadRequest.current)return;
    const controller=new AbortController();loadRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    pendingFocus.current=event.currentTarget===document.activeElement;
    setBusy(true);setError("");
    try {
      const result=await readProposalPreview(verifyFluxProposal,[{session,job,snapshot,offset}],controller.signal);
      if(loadRequest.current===controller)setProposal(result);
    } catch(problem) { if(loadRequest.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut ? '이미지 생성 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : problem?.message ? requestErrorMessage(problem) : '이미지 생성 제안을 확인할 수 없습니다. 다시 검토하세요.'); }
    finally { clearTimeout(timeout);if(loadRequest.current===controller){loadRequest.current=null;setBusy(false);} }
  }
  async function prepare(event) {
    if(busy)return;
    pendingFocus.current=event.currentTarget===document.activeElement;
    setBusy(true);setError('');
    try {
      const checked=await verifyFluxProposal(managementCommand,{session,job,snapshot,offset},proposal);
      if(checked.service!=='minimax-h3-image')throw new Error('이미지 생성기를 다시 확인하세요.');
      const form=await managementCommand('hermes-agent','hermes-minimax-form-prepare',{session_id:session,proposal_job_id:job,service:checked.service});
      if(form.source_job_id!==job || form.service!==checked.service)throw new Error('준비된 접수폼이 제안과 일치하지 않습니다.');
      setPrepared(form);
    } catch(problem) { setError(problem?.message ? requestErrorMessage(problem) : '접수폼을 준비하지 못했습니다. 다시 확인하세요.'); }
    finally { setBusy(false); }
  }
  const notices=<>{error && <p role="alert">{error}</p>}{pollError && <p role="alert">접수폼 상태 확인: {pollError}</p>}</>;
  if(!proposal)return <section aria-label="이미지 생성 제안"><button type="button" aria-disabled={busy} aria-describedby={busy?busyId:undefined} onClick={load}>이미지 생성 제안 검토</button>{busy && <p id={busyId} role="status">이미지 생성 제안을 확인하고 있습니다.</p>}{notices}</section>;
  const {service="flux-image",selection_reason,...inputs}=proposal;
  if(prepared)return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><PreparedMinimaxForm form={prepared} label="이미지" onOpenForm={onOpenForm} receipt={minimaxReceipt}/>{prepared.state==='editing' && prepared.revision===1 && <button type="button" disabled={busy} onClick={prepare}>{busy?'참조 확인 중':'요청한 참조 확인·복원'}</button>}{!hasQuestionForm && prepared.state==='editing' && onQuestionDraft && <HermesQuestionForm key={prepared.form_id+':'+prepared.revision} job={job} session={session} questions={imageApprovalQuestions} target={{type:'minimax-form',form_id:prepared.form_id,revision:prepared.revision}} onDraft={onQuestionDraft}/>}{notices}</section>;
  if(service==="minimax-h3-image")return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><p>이 제안에 연결된 MiniMax 이미지 접수폼이 아직 확인되지 않았습니다.</p><button type="button" disabled={busy} onClick={prepare}>{busy?'접수폼 준비 중':'접수폼 준비'}</button><MinimaxReportStatus receipt={minimaxReceipt}/>{notices}</section>;
  return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><p>선택 생성기: {service}{selection_reason && " · "+selection_reason}</p>{notices}{service==="minimax-h3-image" && <MinimaxReportStatus receipt={minimaxReceipt}/>}<p>생성 폼에서 입력과 필요한 참조를 확인한 뒤 접수하세요. 접수와 보고 상태는 이 생성 폼에서 다시 확인할 수 있습니다.</p>
    <button type="button" aria-controls="hermes-side-panel" onClick={()=>onOpenFluxForm({service,inputs,receiptScope:{session,job,snapshot,offset,proposal}})}>생성 폼 보기</button>
  </section>;
}
