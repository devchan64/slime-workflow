import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {useMinimaxReportReceipt,MinimaxReportStatus,PreparedMinimaxForm} from "./useMinimaxReportReceipt.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import HermesQuestionForm from "./HermesQuestionForm.jsx";

const imageApprovalQuestions=[{title:'이 저장된 이미지 폼으로 생성 절차를 진행할까요?',options:['승인','거절']}];

export default function FluxProposal({job,session,snapshot,offset,onOpenForm,onOpenFluxForm,onQuestionDraft,hasQuestionForm=false}) {
  const busyId=useId();
  const pendingFocus=useRef(false),resultRef=useRef(null);
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [prepared,setPrepared]=useState(null);
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
        if(matches.length===0)return;
        const checked=await verifyFluxProposal((...args)=>managementCommand(...args.slice(0,3),{signal:controller.signal}),{session,job,snapshot,offset});
        if(!active || checked.service!=="minimax-h3-image")return;
        if(active){setProposal(checked);setPrepared(matches[0]);setError('');}
      }catch(problem){if(active && problem?.name!=='AbortError')setError(problem?.message || '접수폼 준비 상태를 확인할 수 없습니다.');}
      finally{if(active)timer=setTimeout(refresh,attempts<12?5000:60000);}
    }
    refresh();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,job,snapshot,offset]);
  async function load(event) {
    if(busy)return;
    pendingFocus.current=event.currentTarget===document.activeElement;
    setBusy(true);setError("");
    try {
      setProposal(await verifyFluxProposal(managementCommand,{session,job,snapshot,offset}));
    } catch(problem) { setError(problem?.message || '이미지 생성 제안을 확인할 수 없습니다. 다시 검토하세요.'); }
    finally { setBusy(false); }
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
    } catch(problem) { setError(problem?.message || '접수폼을 준비하지 못했습니다. 다시 확인하세요.'); }
    finally { setBusy(false); }
  }
  if(!proposal)return <section aria-label="이미지 생성 제안"><button type="button" aria-disabled={busy} aria-describedby={busy?busyId:undefined} onClick={load}>이미지 생성 제안 검토</button>{busy && <p id={busyId} role="status">이미지 생성 제안을 확인하고 있습니다.</p>}{error && <p role="alert">{error}</p>}</section>;
  const {service="flux-image",selection_reason,...inputs}=proposal;
  if(prepared)return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><PreparedMinimaxForm form={prepared} label="이미지" onOpenForm={onOpenForm} receipt={minimaxReceipt}/>{prepared.state==='editing' && prepared.revision===1 && <button type="button" disabled={busy} onClick={prepare}>{busy?'참조 확인 중':'요청한 참조 확인·복원'}</button>}{!hasQuestionForm && prepared.state==='editing' && onQuestionDraft && <HermesQuestionForm key={prepared.form_id+':'+prepared.revision} job={job} session={session} questions={imageApprovalQuestions} target={{type:'minimax-form',form_id:prepared.form_id,revision:prepared.revision}} onDraft={onQuestionDraft}/>}{error && <p role="alert">{error}</p>}</section>;
  if(service==="minimax-h3-image")return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><p>이 제안에 연결된 MiniMax 이미지 접수폼이 아직 확인되지 않았습니다.</p><button type="button" disabled={busy} onClick={prepare}>{busy?'접수폼 준비 중':'접수폼 준비'}</button><MinimaxReportStatus receipt={minimaxReceipt}/>{error && <p role="alert">{error}</p>}</section>;
  return <section ref={resultRef} tabIndex={-1} className="ui-focus-target" aria-label="이미지 생성 제안"><p>선택 생성기: {service}{selection_reason && " · "+selection_reason}</p>{error && <p role="alert">{error}</p>}{service==="minimax-h3-image" && <MinimaxReportStatus receipt={minimaxReceipt}/>}<p>생성 폼에서 입력과 필요한 참조를 확인한 뒤 접수하세요. 접수와 보고 상태는 이 생성 폼에서 다시 확인할 수 있습니다.</p>
    <button type="button" aria-controls="hermes-side-panel" onClick={()=>onOpenFluxForm({service,inputs,receiptScope:{session,job,snapshot,offset,proposal}})}>생성 폼 보기</button>
  </section>;
}
