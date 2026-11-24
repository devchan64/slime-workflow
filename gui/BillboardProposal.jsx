import React,{useEffect,useId,useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readProposalPreview,verifyProposalWithDeadline} from './readProposalPreview.mjs';
import ResultTable from './ResultTable.jsx';
import {prepareBillboardProposal,validateBillboardReceipt,verifyBillboardBeforeSave} from './billboardProposalProtocol.mjs';
import {billboardPropertyLabels} from './BillboardProperties.jsx';
import {requestErrorMessage} from './requestError.mjs';
import {restoreLostFocus} from './restoreLostFocus.mjs';

export function BillboardProposalReview({preview,busy,busyId,onSave,onCancel}){
  return <>{preview.changes.map(change=><ResultTable key={change.texture} table={{title:'에셋: '+change.texture,columns:['속성','기존','변경 후'],rows:Object.entries(change.after).filter(([key,value])=>value!==change.before[key]).map(([key,value])=>[billboardPropertyLabels[key] || key,String(change.before[key] ?? ''),String(value)])}}/>)}
    <p>영향 맵: {preview.maps.join(', ') || '없음'}</p>{preview.map_warnings.map((warning,index)=><p key={index}>{warning.map} · {warning.message}</p>)}<p>{preview.note}</p>
    <p>확인하면 빌보드 속성을 저장합니다.</p><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onCancel}>취소</button></>;
}

export default function BillboardProposal({session,job,snapshot,offset}){
  return <BillboardProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function BillboardProposalForSelection({session,job,snapshot,offset}){
  const busyId=useId();
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const sending=useRef(false);
  const request=useRef(null),mounted=useRef(true),inspectRef=useRef(null),inspectFocus=useRef(false),reviewRef=useRef(null),receiptRef=useRef(null),errorRef=useRef(null),focusFrame=useRef(null);
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;const current=request.current;request.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);};},[]);
  useEffect(()=>{if(busy || !inspectFocus.current)return;inspectFocus.current=false;const target=review ? reviewRef : error ? errorRef : receipt ? receiptRef : inspectRef;const frame=requestAnimationFrame(()=>restoreLostFocus(document,target.current));return ()=>cancelAnimationFrame(frame);},[busy,review,receipt,error]);
  async function inspect(){
    if(request.current)return;
    inspectFocus.current=document.activeElement===inspectRef.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError('');setReview(null);
    try{
      const result=await readProposalPreview(prepareBillboardProposal,[session,job,snapshot,offset],controller.signal);
      if(request.current===controller){setReceipt(result.receipt || null);setReview(result.review || null);}
    }catch(problem){if(request.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut ? '빌보드 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;setBusy(false);}}
  }
  async function save(){
    if(!review || sending.current)return;
    sending.current=true;setBusy(true);setError('');let dispatched=false;const controller=new AbortController();request.current=controller;
    try{
      await verifyProposalWithDeadline(verifyBillboardBeforeSave,[session,job,review],controller);if(request.current!==controller || controller.signal.aborted)return;request.current=null;dispatched=true;
      const result=await managementCommand('hermes-agent','hermes-billboard-save',{request_id:review.id,draft:review.draft,token:review.preview.token,review_sha256:review.preview.review_sha256});
      validateBillboardReceipt(result,review.id,review.draft.changes);
      if(result.state!=='completed' || result.saved!==true || !Array.isArray(result.textures))throw new Error('저장 결과를 확인할 수 없습니다.');
      if(mounted.current){setReceipt(result);setReview(null);}
    }catch(problem){if(mounted.current){if(dispatched){setReceipt({state:'unknown',request_id:review.id});setReview(null);setError(requestErrorMessage(problem)+' · 자동 재저장하지 않습니다.');}else if(problem?.name!=='AbortError')setError(requestErrorMessage(problem)+' · 저장 요청은 보내지 않았습니다.');}}
    finally{if(request.current===controller)request.current=null;sending.current=false;if(mounted.current)setBusy(false);}
  }
  return <section aria-label="빌보드 변경 제안"><button ref={inspectRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>{receipt?'접수 상태 다시 확인':'빌보드 변경 제안 검토'}</button>
    {busy && <p id={busyId} role="status">빌보드 제안을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {receipt && <p ref={receiptRef} tabIndex={-1} className="proposal-feedback" role="status">{receipt.state==='completed' && receipt.saved ? (receipt.textures?'빌보드 저장 확인 · '+receipt.textures.join(', '):'저장 기록 확인 · 대상 미확인'):'접수 확인 필요 · 자동 재저장하지 않습니다.'}{receipt.ledger_status_at_save==='pending' && ' · 저장 당시 원장 반영 대기'}{receipt.request_id && <> · 접수 <code>{receipt.request_id}</code></>}</p>}
    {error && <p ref={errorRef} tabIndex={-1} className="proposal-feedback" role="alert">{error}</p>}
    {review && <div ref={reviewRef} tabIndex={-1} className="proposal-feedback" aria-label="빌보드 변경 검토"><BillboardProposalReview preview={review.preview} busy={busy} busyId={busyId} onSave={save} onCancel={()=>{const restore=reviewRef.current?.contains(document.activeElement);setReview(null);if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;restoreLostFocus(document,inspectRef.current);});}}/></div>}
  </section>;
}
