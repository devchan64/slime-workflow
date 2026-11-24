import React,{useEffect,useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readProposalPreview} from './readProposalPreview.mjs';
import ResultTable from './ResultTable.jsx';
import {prepareFieldProposal,verifyFieldBeforeSave,fieldBlockReason} from './fieldProposalProtocol.mjs';
function cellBefore(source,cell){
  const tile=source.tiles?.rows?.[cell.row]?.[cell.column],height=source.terrain?.elevations?.[cell.row]?.[cell.column],blocked=source.terrain?.blocked?.[cell.row]?.[cell.column];
  return [typeof tile==='string'?tile:'확인 불가',Number.isInteger(height)?String(height):'확인 불가',typeof blocked==='boolean'?String(blocked):blocked===0?'false':blocked===1?'true':'확인 불가'].join(' / ');
}
export function FieldProposalReview({review,busy,onSave,onCancel}){
  const {proposal,source,preview}=review,reason=fieldBlockReason(preview);
  return <><p>야외 맵: {proposal.map} · 리비전 {proposal.revision}</p>
    <ResultTable table={{title:'셀 변경 · 타일 / 높이 / 통행 차단',columns:['좌표','기존','변경 후'],rows:proposal.cells.map(cell=>[`${cell.column}, ${cell.row}`,cellBefore(source,cell),[cell.tile,cell.height,String(cell.blocked)].join(' / ')])}}/>
    {preview.source_alignment && <p>등록 원본 비교: {preview.source_alignment.status} · {preview.source_alignment.note}</p>}
    <p>주변 배치와 실제 맵을 확인하세요. {reason || '확인하면 야외 맵에 변경을 저장합니다.'}</p>
    <button type="button" disabled={busy || Boolean(reason)} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} onClick={onCancel}>취소</button></>;
}
export default function FieldProposal({session,job,snapshot,offset}){
  return <FieldProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function FieldProposalForSelection({session,job,snapshot,offset}){
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');const sending=useRef(false);
  const request=useRef(null);useEffect(()=>()=>request.current?.abort(),[]);
  async function inspect(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice('');setReview(null);
    try{const result=await readProposalPreview(prepareFieldProposal,[session,job,snapshot,offset],controller.signal);setReceipt(result.receipt || null);setReview(result.review || null);}
    catch(error){if(!controller.signal.aborted || timedOut)setNotice(timedOut ? '야외 맵 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : error.message);}
    finally{clearTimeout(timeout);if(request.current===controller)request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function save(){if(!review || sending.current || review.preview.save_available!==true)return;sending.current=true;setBusy(true);setNotice('');let dispatched=false,timedOut=false;
    const controller=new AbortController();request.current=controller;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
    await readProposalPreview(verifyFieldBeforeSave,[session,job,review],controller.signal);
    if(controller.signal.aborted)throw new DOMException('조회가 중단됐습니다.','AbortError');
    clearTimeout(timeout);request.current=null;dispatched=true;
    const result=await managementCommand('hermes-agent','hermes-field-save',{request_id:review.id,draft:review.draft,token:review.preview.token});
    if(result.request_id!==review.id || result.map!==review.draft.map || result.state!=='completed' || result.saved!==true)throw new Error('저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.');
    setReceipt(result);setReview(null);
  }catch(error){if(dispatched){setReceipt({state:'unknown',request_id:review.id});setReview(null);setNotice(error.message+' · 자동 재저장하지 않습니다.');}else if(!controller.signal.aborted || timedOut)setNotice((timedOut ? '저장 전 확인 시간이 초과됐습니다. 다시 확인하세요.' : error.message)+' · 저장 요청은 보내지 않았습니다.');}finally{clearTimeout(timeout);if(request.current===controller)request.current=null;sending.current=false;if(!controller.signal.aborted || timedOut || dispatched)setBusy(false);}}
  return <section aria-label="야외 맵 변경 제안"><button type="button" disabled={busy} onClick={inspect}>{receipt ? '접수 상태 다시 확인' : '야외 맵 변경 제안 검토'}</button>
    {busy && <p role="status">야외 맵 제안을 처리하고 있습니다.</p>}
    {receipt && <p role="status">{receipt.state==='completed' && receipt.saved ? '야외 맵 저장 확인 · '+receipt.map : '접수 확인 필요 · 자동 재저장하지 않습니다.'} · 접수 <code>{receipt.request_id}</code></p>}
    {notice && <p role="alert">{notice}</p>}{review && <FieldProposalReview review={review} busy={busy} onSave={save} onCancel={()=>setReview(null)}/>}</section>;
}
