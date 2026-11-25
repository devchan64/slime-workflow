import {formStateLabel} from './minimaxFormState.mjs';
import React,{useCallback,useEffect,useRef,useState} from 'react';
import {managementCommand,untilAborted} from './managementCommand.js';
import {fluxProposalRequestId} from './fluxProposalReceipt.mjs';

export function useMinimaxReportReceipt(scope, service) {
  const session=scope?.session, job=scope?.job;
  const scopeKey=session && job ? JSON.stringify([session,job,service]) : '';
  const [value,setValue]=useState({state:scopeKey?'checking':'direct',scopeKey});
  const [revision,setRevision]=useState(0), generation=useRef(0), previousScope=useRef(scopeKey);
  const [retryState,setRetryState]=useState({busy:false,error:''}), retryController=useRef(null), retryBusy=useRef(false);
  const current=value.scopeKey===scopeKey ? value : {state:scopeKey?'checking':'direct',scopeKey};
  useEffect(()=>{
    const version=++generation.current;
    if(previousScope.current!==scopeKey){previousScope.current=scopeKey;retryBusy.current=false;setRetryState({busy:false,error:''});}
    if(!session || !job){setValue({state:'direct',scopeKey});return;}
    let stopped=false,timer=null,controller=null;
    async function check(){
      controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),30000);
      try{
        const id=await fluxProposalRequestId(session,job,service);
        const result=await untilAborted(managementCommand('hermes-agent','hermes-minimax-report-status',{
          session_id:session,proposal_job_id:job,request_id:id,service
        },{signal:controller.signal}),controller.signal);
        if(stopped || version!==generation.current)return;
        const receipt=result?.receipt;
        if(receipt?.request_id!==id || receipt?.service!==service)throw new Error('접수 기록이 일치하지 않습니다.');
        if(receipt.state==='not_found')setValue({state:'editing',id,scopeKey});
        else if(receipt.state==='accepted' && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(receipt.job_id || '')){
          setValue({state:'accepted',id,job:receipt.job_id,service,report:result.report,scopeKey});
          if(!['completed','failed'].includes(result.report?.state))timer=setTimeout(check,5000);
        }else {setValue({state:'unknown',id,scopeKey});timer=setTimeout(check,5000);}
      }catch(error){if(!stopped && version===generation.current){setValue({state:'unknown',error:error?.message,scopeKey});timer=setTimeout(check,5000);}}
      finally{clearTimeout(timeout);}
    }
    setValue({state:'checking',scopeKey});check();
    return ()=>{stopped=true;clearTimeout(timer);controller?.abort();retryController.current?.abort();if(generation.current===version)generation.current++;};
  },[session,job,service,revision,scopeKey]);
  const refresh=useCallback(()=>{setValue({state:scopeKey?'checking':'direct',scopeKey});setRevision(n=>n+1);},[scopeKey]);
  const unknown=useCallback(()=>setValue({state:'unknown',scopeKey}),[scopeKey]);
  const retry=useCallback(async()=>{
    if(retryBusy.current || !session || !job || !current.id || current.report?.retry_available!==true)return;
    const version=generation.current, controller=new AbortController();
    retryBusy.current=true;retryController.current=controller;setRetryState({busy:true,error:''});
    const timer=setTimeout(()=>controller.abort(),30000);
    try{
      const expected=current.report.retry_revision;
      const result=await untilAborted(managementCommand('hermes-agent','hermes-minimax-report-retry',{
        session_id:session,proposal_job_id:job,request_id:current.id,service,expected_revision:expected
      },{signal:controller.signal}),controller.signal);
      if(version!==generation.current)return;
      if(result?.state!=='waiting' || result?.retry_revision!==expected+1)throw new Error('재분석 접수 상태를 확인할 수 없습니다.');
      setRetryState({busy:false,error:''});refresh();
    }catch(error){
      if(version===generation.current){setRetryState({busy:false,error:(error?.message || '재분석 요청 결과를 확인할 수 없습니다.')+' · 상태를 다시 확인하세요.'});refresh();}
    }finally{clearTimeout(timer);if(retryController.current===controller){retryController.current=null;retryBusy.current=false;}}
  },[session,job,service,current,refresh]);
  return {...current,refresh,unknown,retry,retryState};
}

export function minimaxReceiptText(receipt){
  if(receipt.state==='checking')return '기존 접수 및 보고 상태를 확인하고 있습니다.';
  if(receipt.state==='unknown')return '접수 여부를 확인할 수 없습니다. 이력과 접수 기록을 확인하세요.';
  if(receipt.state!=='accepted')return '';
  const names={waiting:'생성 중 또는 분석 대기',analyzing:'결과 분석 중',report_queued:'보고서 작성 대기',writing:'보고서 작성 중',completed:'대화에 보고 완료',failed:'보고 실패'};
  const report=receipt.report;
  const label=report?.generation_state==='failed' ? '생성 실패' : ['cancelled','canceled'].includes(report?.generation_state) ? '생성 취소' : report?.state==='writing' && report?.writer_status==='queued' ? '보고서 작성 대기' : report?.state==='writing' && report?.writer_status!=='running' ? '보고서 작성 상태 확인 중' : names[report?.state];
  return `생성 대기열에 등록했습니다. 작업 ID ${receipt.job} · ${label || '보고 상태 확인 중'}${report?.error || report?.last_error ? ' · '+(report.error || report.last_error) : ''}`;
}


export function PreparedMinimaxForm({form,label,onOpenForm,receipt}){
  return <div className="prepared-minimax-form">
    <div className="prepared-minimax-heading">
      <div><strong>MiniMax {label} 접수폼</strong>
        <small>버전 {form.revision} · {formStateLabel(form.state,form.receipt_state)}</small></div>
      {onOpenForm && <button type="button" onClick={()=>onOpenForm(form.form_id)}>접수폼 열기</button>}
    </div>
    <MinimaxReportStatus receipt={receipt} formId={form.form_id}/>
  </div>;
}

export function MinimaxReportStatus({receipt,formId}){
  const retryAvailable=receipt?.state==='accepted' && receipt.report?.retry_available===true;
  const message=minimaxReceiptText(receipt);
  const linked=receipt.state==='accepted' && receipt.service==='minimax-h3-image';
  const offset=linked ? message.indexOf(receipt.job) : -1;
  const refreshButton=<button type="button" onClick={receipt.refresh} disabled={receipt.retryState?.busy}>접수·보고 상태 새로고침</button>;
  return <div>{message && <p role="status">{offset>=0 ? <>{message.slice(0,offset)}<a href={'/management/frame/minimax-h3-image-generator/?job='+encodeURIComponent(receipt.job)+'#job-result'}>{receipt.job}</a>{message.slice(offset+receipt.job.length)}</> : message}{retryAvailable && ' · 재분석 가능'}{receipt.report?.retry_unavailable_reason && ' · 재분석 불가: '+receipt.report.retry_unavailable_reason}</p>}
    {formId ? <details><summary>접수 상세</summary><p>폼 ID · {formId}</p>{refreshButton}</details> : refreshButton}
    {retryAvailable && <button type="button" onClick={receipt.retry} disabled={receipt.retryState?.busy}>{receipt.retryState?.busy ? '재분석 요청 중' : '보고서 재분석'}</button>}
    {receipt.retryState?.error && <p role="alert">{receipt.retryState.error}</p>}</div>;
}
