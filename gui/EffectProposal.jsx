import React,{useEffect,useId,useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readProposalPreview,verifyProposalWithDeadline} from './readProposalPreview.mjs';
import ResultTable from './ResultTable.jsx';
import {prepareEffectProposal,verifyEffectBeforeSave} from './effectProposalProtocol.mjs';
import {restoreLostFocus} from './restoreLostFocus.mjs';
import {requestErrorMessage} from './requestError.mjs';
export function EffectProposalReview({preview,busy,busyId,onSave,onCancel}){
  const before=preview.before,after=preview.after;
  const rows=[['불투명도',String(before.alpha),String(after.alpha)],['대상 좌표',JSON.stringify(before.target),JSON.stringify(after.target)],...after.frames.map((frame,index)=>['프레임 '+index,JSON.stringify(before.frames[index]),JSON.stringify(frame)])];
  return <><p>이펙트: {preview.id}</p><ResultTable table={{title:'공용 좌표 변경',columns:['항목','기존','변경 후'],rows}}/><p>{preview.note}</p><p>확인하면 이펙트 도구에 공용 좌표를 저장합니다.</p><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onCancel}>취소</button></>;
}
export default function EffectProposal({session,job,snapshot,offset}){
  return <EffectProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function EffectProposalForSelection({session,job,snapshot,offset}){
  const busyId=useId();
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');const sending=useRef(false);
  const request=useRef(null),mounted=useRef(true),inspectRef=useRef(null),inspectFocus=useRef(false),reviewRef=useRef(null),receiptRef=useRef(null),noticeRef=useRef(null),focusFrame=useRef(null);useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;const current=request.current;request.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);};},[]);
  useEffect(()=>{if(busy || !inspectFocus.current)return;inspectFocus.current=false;const target=review ? reviewRef : notice ? noticeRef : receipt ? receiptRef : inspectRef;const frame=requestAnimationFrame(()=>restoreLostFocus(document,target.current));return ()=>cancelAnimationFrame(frame);},[busy,review,receipt,notice]);
  async function inspect(){
    if(request.current)return;
    inspectFocus.current=document.activeElement===inspectRef.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice('');setReview(null);
    try{const result=await readProposalPreview(prepareEffectProposal,[session,job,snapshot,offset],controller.signal);if(request.current===controller){setReceipt(result.receipt || null);setReview(result.review || null);}}
    catch(error){if(request.current===controller && (!controller.signal.aborted || timedOut))setNotice(timedOut ? '이펙트 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : error?.message || '이펙트 제안을 확인하지 못했습니다. 다시 시도하세요.');}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;setBusy(false);}}
  }
  async function save(){if(!review || sending.current)return;sending.current=true;setBusy(true);setNotice('');let dispatched=false;const controller=new AbortController();request.current=controller;try{
    await verifyProposalWithDeadline(verifyEffectBeforeSave,[session,job,review],controller);if(request.current!==controller || controller.signal.aborted)return;request.current=null;dispatched=true;
    const result=await managementCommand('hermes-agent','hermes-effect-save',{request_id:review.id,draft:review.draft,token:review.preview.token});
    if(result.request_id!==review.id || result.effect_id!==review.draft.id || result.state!=='completed' || result.saved!==true)throw new Error('저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.');
    if(mounted.current){setReceipt(result);setReview(null);}
  }catch(error){if(mounted.current){if(dispatched){setReceipt({state:'unknown',request_id:review.id});setReview(null);setNotice(requestErrorMessage(error)+' · 자동 재저장하지 않습니다.');}else if(error?.name!=='AbortError')setNotice(requestErrorMessage(error)+' · 저장 요청은 보내지 않았습니다.');}}finally{if(request.current===controller)request.current=null;sending.current=false;if(mounted.current)setBusy(false);}}
  return <section aria-label="이펙트 변경 제안"><button ref={inspectRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>{receipt ? '접수 상태 다시 확인' : '이펙트 변경 제안 검토'}</button>
    {busy && <p id={busyId} role="status">이펙트 제안을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {receipt && <p ref={receiptRef} tabIndex={-1} className="effect-proposal-feedback" role="status">{receipt.state==='completed' && receipt.saved ? (receipt.effect_id ? '이펙트 저장 확인 · '+receipt.effect_id : '저장 기록 확인 · 대상 미확인') : '접수 확인 필요 · 자동 재저장하지 않습니다.'}{receipt.ledger_status_at_save==='pending' && ' · 저장 당시 원장 반영 대기 · 현재 동기화 상태는 별도 확인'} · 접수 <code>{receipt.request_id}</code></p>}
    {notice && <p ref={noticeRef} tabIndex={-1} className="effect-proposal-feedback" role="alert">{notice}</p>}{review && <div ref={reviewRef} tabIndex={-1} aria-label="이펙트 변경 검토"><EffectProposalReview preview={review.preview} busy={busy} busyId={busyId} onSave={save} onCancel={()=>{const restore=reviewRef.current?.contains(document.activeElement);setReview(null);if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;restoreLostFocus(document,inspectRef.current);});}}/></div>}</section>;
}
