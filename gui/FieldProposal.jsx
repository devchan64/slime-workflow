import React,{useEffect,useId,useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readProposalPreview,verifyProposalWithDeadline} from './readProposalPreview.mjs';
import ResultTable from './ResultTable.jsx';
import {prepareFieldProposal,verifyFieldBeforeSave,fieldBlockReason} from './fieldProposalProtocol.mjs';
import {requestErrorMessage} from './requestError.mjs';
import {restoreLostFocus} from './restoreLostFocus.mjs';
function cellBefore(source,cell){
  const tile=source.tiles?.rows?.[cell.row]?.[cell.column],height=source.terrain?.elevations?.[cell.row]?.[cell.column],blocked=source.terrain?.blocked?.[cell.row]?.[cell.column];
  return [typeof tile==='string'?tile:'확인 불가',Number.isInteger(height)?String(height):'확인 불가',typeof blocked==='boolean'?String(blocked):blocked===0?'false':blocked===1?'true':'확인 불가'].join(' / ');
}
export function FieldProposalReview({review,busy,busyId,onSave,onCancel}){
  const reasonId=useId();
  const {proposal,source,preview}=review,reason=fieldBlockReason(preview);
  return <><p>야외 맵: {proposal.map} · 리비전 {proposal.revision}</p>
    <ResultTable table={{title:'셀 변경 · 타일 / 높이 / 통행 차단',columns:['좌표','기존','변경 후'],rows:proposal.cells.map(cell=>[`${cell.column}, ${cell.row}`,cellBefore(source,cell),[cell.tile,cell.height,String(cell.blocked)].join(' / ')])}}/>
    {preview.source_alignment && <p>등록 원본 비교: {preview.source_alignment.status} · {preview.source_alignment.note}</p>}
    <p id={reasonId}>주변 배치와 실제 맵을 확인하세요. {reason || '확인하면 야외 맵에 변경을 저장합니다.'}</p>
    <button type="button" disabled={busy || Boolean(reason)} aria-describedby={[reason && reasonId,busy && busyId].filter(Boolean).join(' ') || undefined} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onCancel}>취소</button></>;
}
export default function FieldProposal({session,job,snapshot,offset}){
  return <FieldProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function FieldProposalForSelection({session,job,snapshot,offset}){
  const busyId=useId();
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');const sending=useRef(false);
  const request=useRef(null),mounted=useRef(true),inspectRef=useRef(null),inspectFocus=useRef(false),reviewRef=useRef(null),receiptRef=useRef(null),noticeRef=useRef(null),focusFrame=useRef(null);
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;const current=request.current;request.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);};},[]);
  useEffect(()=>{if(busy || !inspectFocus.current)return;inspectFocus.current=false;const target=review ? reviewRef : notice ? noticeRef : receipt ? receiptRef : inspectRef;const frame=requestAnimationFrame(()=>restoreLostFocus(document,target.current));return ()=>cancelAnimationFrame(frame);},[busy,review,receipt,notice]);
  async function inspect(){
    if(request.current)return;
    inspectFocus.current=document.activeElement===inspectRef.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice('');setReview(null);
    try{const result=await readProposalPreview(prepareFieldProposal,[session,job,snapshot,offset],controller.signal);if(request.current===controller){setReceipt(result.receipt || null);setReview(result.review || null);}}
    catch(error){if(request.current===controller && (!controller.signal.aborted || timedOut))setNotice(timedOut ? '야외 맵 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : requestErrorMessage(error));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;setBusy(false);}}
  }
  async function save(){if(!review || sending.current || review.preview.save_available!==true)return;sending.current=true;setBusy(true);setNotice('');let dispatched=false;
    const controller=new AbortController();request.current=controller;
    try{
    await verifyProposalWithDeadline(verifyFieldBeforeSave,[session,job,review],controller);
    if(request.current!==controller || controller.signal.aborted)return;
    request.current=null;dispatched=true;
    const result=await managementCommand('hermes-agent','hermes-field-save',{request_id:review.id,draft:review.draft,token:review.preview.token});
    if(result.request_id!==review.id || result.map!==review.draft.map || result.state!=='completed' || result.saved!==true)throw new Error('저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.');
    if(mounted.current){setReceipt(result);setReview(null);}
  }catch(error){if(mounted.current){if(dispatched){setReceipt({state:'unknown',request_id:review.id});setReview(null);setNotice(requestErrorMessage(error)+' · 자동 재저장하지 않습니다.');}else if(error?.name!=='AbortError')setNotice(requestErrorMessage(error)+' · 저장 요청은 보내지 않았습니다.');}}finally{if(request.current===controller)request.current=null;sending.current=false;if(mounted.current)setBusy(false);}}
  return <section aria-label="야외 맵 변경 제안"><button ref={inspectRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>{receipt ? '접수 상태 다시 확인' : '야외 맵 변경 제안 검토'}</button>
    {busy && <p id={busyId} role="status">야외 맵 제안을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {receipt && <p ref={receiptRef} tabIndex={-1} className="proposal-feedback" role="status">{receipt.state==='completed' && receipt.saved ? '야외 맵 저장 확인 · '+receipt.map : '접수 확인 필요 · 자동 재저장하지 않습니다.'} · 접수 <code>{receipt.request_id}</code></p>}
    {notice && <p ref={noticeRef} tabIndex={-1} className="proposal-feedback" role="alert">{notice}</p>}{review && <div ref={reviewRef} tabIndex={-1} className="proposal-feedback" aria-label="야외 맵 변경 검토"><FieldProposalReview review={review} busy={busy} busyId={busyId} onSave={save} onCancel={()=>{const restore=reviewRef.current?.contains(document.activeElement);setReview(null);if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;restoreLostFocus(document,inspectRef.current);});}}/></div>}</section>;
}
