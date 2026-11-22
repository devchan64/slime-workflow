import React,{useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import ResultTable from './ResultTable.jsx';
import {prepareBillboardProposal,validateBillboardReceipt,verifyBillboardBeforeSave} from './billboardProposalProtocol.mjs';
import {billboardPropertyLabels} from './BillboardProperties.jsx';

export function BillboardProposalReview({preview,busy,onSave,onCancel}){
  return <>{preview.changes.map(change=><ResultTable key={change.texture} table={{title:'에셋: '+change.texture,columns:['속성','기존','변경 후'],rows:Object.entries(change.after).filter(([key,value])=>value!==change.before[key]).map(([key,value])=>[billboardPropertyLabels[key] || key,String(change.before[key] ?? ''),String(value)])}}/>)}
    <p>영향 맵: {preview.maps.join(', ') || '없음'}</p>{preview.map_warnings.map((warning,index)=><p key={index}>{warning.map} · {warning.message}</p>)}<p>{preview.note}</p>
    <p>확인하면 빌보드 속성을 저장합니다.</p><button type="button" disabled={busy} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} onClick={onCancel}>취소</button></>;
}

export default function BillboardProposal({session,job,snapshot,offset}){
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const sending=useRef(false);
  async function inspect(){
    setBusy(true);setError('');setReview(null);
    try{
      const result=await prepareBillboardProposal(managementCommand,session,job,snapshot,offset);
      setReceipt(result.receipt || null);setReview(result.review || null);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function save(){
    if(!review || sending.current)return;
    sending.current=true;setBusy(true);setError('');
    try{
      await verifyBillboardBeforeSave(managementCommand,session,job,review);
      const result=await managementCommand('hermes-agent','hermes-billboard-save',{request_id:review.id,draft:review.draft,token:review.preview.token,review_sha256:review.preview.review_sha256});
      validateBillboardReceipt(result,review.id,review.draft.changes);
      if(result.state!=='completed' || result.saved!==true || !Array.isArray(result.textures))throw new Error('저장 결과를 확인할 수 없습니다.');
      setReceipt(result);setReview(null);
    }catch(problem){setReceipt({state:'unknown',request_id:review.id});setReview(null);setError(problem.message+' · 자동 재저장하지 않습니다.');}
    finally{sending.current=false;setBusy(false);}
  }
  return <section aria-label="빌보드 변경 제안"><button type="button" disabled={busy} onClick={inspect}>{receipt?'접수 상태 다시 확인':'빌보드 변경 제안 검토'}</button>
    {receipt && <p role="status">{receipt.state==='completed' && receipt.saved ? (receipt.textures?'빌보드 저장 확인 · '+receipt.textures.join(', '):'저장 기록 확인 · 대상 미확인'):'접수 확인 필요 · 자동 재저장하지 않습니다.'}{receipt.ledger_status_at_save==='pending' && ' · 저장 당시 원장 반영 대기'}{receipt.request_id && <> · 접수 <code>{receipt.request_id}</code></>}</p>}
    {error && <p role="alert">{error}</p>}
    {review && <BillboardProposalReview preview={review.preview} busy={busy} onSave={save} onCancel={()=>setReview(null)}/>}
  </section>;
}
