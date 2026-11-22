import React,{useState} from 'react';
import {managementCommand} from './managementCommand.js';
import ResultTable from './ResultTable.jsx';
import {prepareCityProposal} from './cityProposalProtocol.mjs';
export function CityProposalReview({proposal,preview}){
  const plan=preview.source_plan,alignment=preview.source_alignment;
  return <><p>도시 맵: {proposal.map} · 세대 {proposal.generation} · 리비전 {proposal.revision}</p>
    <ResultTable table={{title:'변경 사항',columns:['경로','기존','변경 후'],rows:proposal.changes.map(change=>[change.path.join(' / '),JSON.stringify(change.before),JSON.stringify(change.after)])}}/>
    <p>원본 비교: {alignment?.status || '확인 불가'}{alignment?.note && ' · '+alignment.note}</p>
    {plan?.status==='available' ? <p>원본 변경 계획 해시 · 이전 <code>{plan.before_sha256}</code> · 이후 <code>{plan.after_sha256}</code></p> : <p>원본 변경 계획을 확인할 수 없습니다.</p>}
    <p>신규 저장은 현재 지원되지 않습니다. 변경 계획은 저장 또는 복구 준비 완료를 뜻하지 않습니다.</p></>;
}
export default function CityProposal({session,job,snapshot,offset}){
  const [value,setValue]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function inspect(){setBusy(true);setError('');setValue(null);try{setValue(await prepareCityProposal(managementCommand,session,job,snapshot,offset));}catch(problem){setError(problem.message);}finally{setBusy(false);}}
  return <section aria-label="도시 맵 변경 제안"><button type="button" disabled={busy} onClick={inspect}>도시 맵 변경 제안 검토</button>{error && <p role="alert">{error}</p>}
    {value?.receipt && <p role="status">{value.receipt.state==='completed' && value.receipt.saved ? '도시 DB 저장 기록 · '+value.receipt.map+' · 원본 동기화 상태는 별도 확인' : '접수 확인 필요'} · 접수 <code>{value.receipt.request_id}</code></p>}
    {value?.proposal && <CityProposalReview proposal={value.proposal} preview={value.preview}/>}</section>;
}
