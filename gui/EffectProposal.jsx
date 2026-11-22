import React,{useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import ResultTable from './ResultTable.jsx';
import {prepareEffectProposal,verifyEffectBeforeSave} from './effectProposalProtocol.mjs';
export function EffectProposalReview({preview,busy,onSave,onCancel}){
  const before=preview.before,after=preview.after;
  const rows=[['불투명도',String(before.alpha),String(after.alpha)],['대상 좌표',JSON.stringify(before.target),JSON.stringify(after.target)],...after.frames.map((frame,index)=>['프레임 '+index,JSON.stringify(before.frames[index]),JSON.stringify(frame)])];
  return <><p>이펙트: {preview.id}</p><ResultTable table={{title:'공용 좌표 변경',columns:['항목','기존','변경 후'],rows}}/><p>{preview.note}</p><p>확인하면 이펙트 도구에 공용 좌표를 저장합니다.</p><button type="button" disabled={busy} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} onClick={onCancel}>취소</button></>;
}
export default function EffectProposal({session,job,snapshot,offset}){
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');const sending=useRef(false);
  async function inspect(){setBusy(true);setNotice('');setReview(null);try{const result=await prepareEffectProposal(managementCommand,session,job,snapshot,offset);setReceipt(result.receipt || null);setReview(result.review || null);}catch(error){setNotice(error.message);}finally{setBusy(false);}}
  async function save(){if(!review || sending.current)return;sending.current=true;setBusy(true);setNotice('');try{
    await verifyEffectBeforeSave(managementCommand,session,job,review);
    const result=await managementCommand('hermes-agent','hermes-effect-save',{request_id:review.id,draft:review.draft,token:review.preview.token});
    if(result.request_id!==review.id || result.effect_id!==review.draft.id || result.state!=='completed' || result.saved!==true)throw new Error('저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.');
    setReceipt(result);setReview(null);
  }catch(error){setReceipt({state:'unknown',request_id:review.id});setReview(null);setNotice(error.message+' · 자동 재저장하지 않습니다.');}finally{sending.current=false;setBusy(false);}}
  return <section aria-label="이펙트 변경 제안"><button type="button" disabled={busy} onClick={inspect}>{receipt ? '접수 상태 다시 확인' : '이펙트 변경 제안 검토'}</button>
    {receipt && <p role="status">{receipt.state==='completed' && receipt.saved ? (receipt.effect_id ? '이펙트 저장 확인 · '+receipt.effect_id : '저장 기록 확인 · 대상 미확인') : '접수 확인 필요 · 자동 재저장하지 않습니다.'}{receipt.ledger_status_at_save==='pending' && ' · 저장 당시 원장 반영 대기 · 현재 동기화 상태는 별도 확인'} · 접수 <code>{receipt.request_id}</code></p>}
    {notice && <p role="alert">{notice}</p>}{review && <EffectProposalReview preview={review.preview} busy={busy} onSave={save} onCancel={()=>setReview(null)}/>}</section>;
}
