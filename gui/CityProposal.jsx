import React,{useEffect,useId,useRef,useState} from 'react';
import {readProposalPreview} from './readProposalPreview.mjs';
import ResultTable from './ResultTable.jsx';
import {prepareCityProposal} from './cityProposalProtocol.mjs';
import {requestErrorMessage} from './requestError.mjs';
import {restoreLostFocus} from './restoreLostFocus.mjs';
export function CityProposalReview({proposal,preview}){
  const plan=preview.source_plan,alignment=preview.source_alignment;
  return <><p>도시 맵: {proposal.map} · 세대 {proposal.generation} · 리비전 {proposal.revision}</p>
    <ResultTable table={{title:'변경 사항',columns:['경로','기존','변경 후'],rows:proposal.changes.map(change=>[change.path.join(' / '),JSON.stringify(change.before),JSON.stringify(change.after)])}}/>
    <p>원본 비교: {alignment?.status || '확인 불가'}{alignment?.note && ' · '+alignment.note}</p>
    {plan?.status==='available' ? <p>원본 변경 계획 해시 · 이전 <code>{plan.before_sha256}</code> · 이후 <code>{plan.after_sha256}</code></p> : <p>원본 변경 계획을 확인할 수 없습니다.</p>}
    <p>신규 저장은 현재 지원되지 않습니다. 변경 계획은 저장 또는 복구 준비 완료를 뜻하지 않습니다.</p></>;
}
export default function CityProposal({session,job,snapshot,offset}){
  return <CityProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function CityProposalForSelection({session,job,snapshot,offset}){
  const busyId=useId();
  const [value,setValue]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const request=useRef(null),inspectRef=useRef(null),inspectFocus=useRef(false),resultRef=useRef(null),errorRef=useRef(null);
  useEffect(()=>()=>{const current=request.current;request.current=null;current?.abort();},[]);
  useEffect(()=>{if(busy || !inspectFocus.current)return;inspectFocus.current=false;const target=error ? errorRef : value ? resultRef : inspectRef;const frame=requestAnimationFrame(()=>restoreLostFocus(document,target.current));return ()=>cancelAnimationFrame(frame);},[busy,value,error]);
  async function inspect(){
    if(request.current)return;
    inspectFocus.current=document.activeElement===inspectRef.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError('');setValue(null);
    try{const result=await readProposalPreview(prepareCityProposal,[session,job,snapshot,offset],controller.signal);if(request.current===controller)setValue(result);}
    catch(problem){if(request.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut ? '도시 맵 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;setBusy(false);}}
  }
  return <section aria-label="도시 맵 변경 제안"><button ref={inspectRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>도시 맵 변경 제안 검토</button>{error && <p ref={errorRef} tabIndex={-1} className="proposal-feedback" role="alert">{error}</p>}
    {busy && <p id={busyId} role="status">도시 맵 제안을 조회하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {value && <div ref={resultRef} tabIndex={-1} className="proposal-feedback" aria-label="도시 맵 제안 결과">{value.receipt && <p role="status">{value.receipt.state==='completed' && value.receipt.saved ? '도시 DB 저장 기록 · '+value.receipt.map+' · 원본 동기화 상태는 별도 확인' : '접수 확인 필요'} · 접수 <code>{value.receipt.request_id}</code></p>}
    {value.proposal && <CityProposalReview proposal={value.proposal} preview={value.preview}/>}</div>}</section>;
}
