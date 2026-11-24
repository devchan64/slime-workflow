import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {verifyProposalWithDeadline} from "./readProposalPreview.mjs";
import ResultTable from "./ResultTable.jsx";
import {prepareBuildingProposal,verifyBuildingProposalBeforeSave} from "./buildingProposalProtocol.mjs";

export function BuildingProposalReceipt({receipt}){
  return <p role="status">{receipt.state==="completed" && receipt.saved ? (receipt.texture ? "건물 앵커 저장 확인 · "+receipt.texture : "저장 기록 확인 · 건물 대상 미확인") : "접수 확인 필요 · 자동 재저장하지 않습니다."}{receipt.ledger_status_at_save==="pending" && <> · 저장 당시 원장 반영 대기{Number.isInteger(receipt.generation) && " · DB 세대 "+receipt.generation} · 현재 원장 동기화 상태는 별도 확인</>}{receipt.request_id && <> · 접수 <code>{receipt.request_id}</code></>}</p>;
}

export function BuildingProposalReview({preview,busy,onSave,onCancel}){
  return <><p>건물: {preview.texture} · 콘텐츠 세대 {preview.generation}</p>
    <ResultTable table={{title:"앵커 변경",columns:["항목","기존","변경 후"],rows:[["앵커 X",String(preview.before.anchorX),String(preview.after.anchorX)],["앵커 Y",String(preview.before.anchorY),String(preview.after.anchorY)]]}}/>
    <p>영향 맵: {preview.maps.join(", ") || "없음"}</p><p>확인하면 건물 앵커를 저장합니다. GPU 생성 작업은 실행하지 않습니다.</p>
    <button type="button" disabled={busy} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} onClick={onCancel}>취소</button></>;
}

export default function BuildingProposal({session,job,snapshot,offset}){
  return <BuildingProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}

function BuildingProposalForSelection({session,job,snapshot,offset}){
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const sending=useRef(false);
  const inspection=useRef(null);
  useEffect(()=>()=>inspection.current?.abort(),[]);
  async function inspect(){
    if(inspection.current)return;
    const controller=new AbortController();inspection.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice("");setReview(null);
    try{
      const command=(service,name,payload)=>{if(controller.signal.aborted)return Promise.reject(new DOMException("조회가 중단됐습니다.","AbortError"));return untilAborted(managementCommand(service,name,payload,{signal:controller.signal}),controller.signal);};
      const result=await untilAborted(prepareBuildingProposal(command,session,job,snapshot,offset),controller.signal);
      setReceipt(result.receipt || null);setReview(result.review || null);
    }catch(error){if(!controller.signal.aborted || timedOut)setNotice(timedOut ? "건물 제안 조회 시간이 초과됐습니다. 다시 확인하세요." : error.message);}
    finally{clearTimeout(timeout);if(inspection.current===controller)inspection.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function save(){
    if(!review || sending.current)return;
    sending.current=true;setBusy(true);setNotice("");let dispatched=false;const controller=new AbortController();inspection.current=controller;
    try{
      await verifyProposalWithDeadline(verifyBuildingProposalBeforeSave,[session,job,review],controller);inspection.current=null;dispatched=true;
      const result=await managementCommand("hermes-agent","hermes-building-save",{request_id:review.id,draft:review.draft,review_sha256:review.preview.review_sha256});
      if(result.request_id!==review.id || result.texture!==review.draft.texture || result.state!=="completed" || result.saved!==true)throw new Error("저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.");
      setReceipt(result);setReview(null);
    }catch(error){if(dispatched){setReceipt({state:"unknown",request_id:review.id});setReview(null);setNotice(error.message+" · 자동 재저장하지 않습니다.");}else if(error.name!=="AbortError")setNotice(error.message+" · 저장 요청은 보내지 않았습니다.");}
    finally{if(inspection.current===controller)inspection.current=null;sending.current=false;setBusy(false);}
  }
  return <section aria-label="건물 앵커 변경 제안">
    <button type="button" disabled={busy} onClick={inspect}>{receipt ? "접수 상태 다시 확인" : "건물 변경 제안 검토"}</button>
    {busy && <p role="status">건물 제안을 처리하고 있습니다.</p>}
    {receipt && <BuildingProposalReceipt receipt={receipt}/>}
    {notice && <p role="alert">{notice}</p>}
    {review && <BuildingProposalReview preview={review.preview} busy={busy} onSave={save} onCancel={()=>setReview(null)}/>}
  </section>;
}
