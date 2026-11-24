import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {verifyProposalWithDeadline} from "./readProposalPreview.mjs";
import ResultTable from "./ResultTable.jsx";
import {prepareBuildingProposal,verifyBuildingProposalBeforeSave} from "./buildingProposalProtocol.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export function BuildingProposalReceipt({receipt}){
  return <p role="status">{receipt.state==="completed" && receipt.saved ? (receipt.texture ? "건물 앵커 저장 확인 · "+receipt.texture : "저장 기록 확인 · 건물 대상 미확인") : "접수 확인 필요 · 자동 재저장하지 않습니다."}{receipt.ledger_status_at_save==="pending" && <> · 저장 당시 원장 반영 대기{Number.isInteger(receipt.generation) && " · DB 세대 "+receipt.generation} · 현재 원장 동기화 상태는 별도 확인</>}{receipt.request_id && <> · 접수 <code>{receipt.request_id}</code></>}</p>;
}

export function BuildingProposalReview({preview,busy,busyId,onSave,onCancel}){
  return <><p>건물: {preview.texture} · 콘텐츠 세대 {preview.generation}</p>
    <ResultTable table={{title:"앵커 변경",columns:["항목","기존","변경 후"],rows:[["앵커 X",String(preview.before.anchorX),String(preview.after.anchorX)],["앵커 Y",String(preview.before.anchorY),String(preview.after.anchorY)]]}}/>
    <p>영향 맵: {preview.maps.join(", ") || "없음"}</p><p>확인하면 건물 앵커를 저장합니다. GPU 생성 작업은 실행하지 않습니다.</p>
    <button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onSave}>확인 후 저장</button><button type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={onCancel}>취소</button></>;
}

export default function BuildingProposal({session,job,snapshot,offset}){
  return <BuildingProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}

function BuildingProposalForSelection({session,job,snapshot,offset}){
  const busyId=useId();
  const [review,setReview]=useState(null),[receipt,setReceipt]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const sending=useRef(false);
  const inspection=useRef(null),mounted=useRef(true),inspectRef=useRef(null),inspectFocus=useRef(false),reviewRef=useRef(null),receiptRef=useRef(null),noticeRef=useRef(null),focusFrame=useRef(null);
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;const current=inspection.current;inspection.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);};},[]);
  useEffect(()=>{if(busy || !inspectFocus.current)return;inspectFocus.current=false;const target=review ? reviewRef : notice ? noticeRef : receipt ? receiptRef : inspectRef;const frame=requestAnimationFrame(()=>restoreLostFocus(document,target.current));return ()=>cancelAnimationFrame(frame);},[busy,review,receipt,notice]);
  async function inspect(){
    if(inspection.current)return;
    inspectFocus.current=document.activeElement===inspectRef.current;
    const controller=new AbortController();inspection.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice("");setReview(null);
    try{
      const command=(service,name,payload)=>{if(controller.signal.aborted)return Promise.reject(new DOMException("조회가 중단됐습니다.","AbortError"));return untilAborted(managementCommand(service,name,payload,{signal:controller.signal}),controller.signal);};
      const result=await untilAborted(prepareBuildingProposal(command,session,job,snapshot,offset),controller.signal);
      if(inspection.current===controller){setReceipt(result.receipt || null);setReview(result.review || null);}
    }catch(error){if(inspection.current===controller && (!controller.signal.aborted || timedOut))setNotice(timedOut ? "건물 제안 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(error));}
    finally{clearTimeout(timeout);if(inspection.current===controller){inspection.current=null;setBusy(false);}}
  }
  async function save(){
    if(!review || sending.current)return;
    sending.current=true;setBusy(true);setNotice("");let dispatched=false;const controller=new AbortController();inspection.current=controller;
    try{
      await verifyProposalWithDeadline(verifyBuildingProposalBeforeSave,[session,job,review],controller);if(inspection.current!==controller || controller.signal.aborted)return;inspection.current=null;dispatched=true;
      const result=await managementCommand("hermes-agent","hermes-building-save",{request_id:review.id,draft:review.draft,review_sha256:review.preview.review_sha256});
      if(result.request_id!==review.id || result.texture!==review.draft.texture || result.state!=="completed" || result.saved!==true)throw new Error("저장 결과를 확인할 수 없습니다. 접수 상태를 다시 확인하세요.");
      if(mounted.current){setReceipt(result);setReview(null);}
    }catch(error){if(mounted.current){if(dispatched){setReceipt({state:"unknown",request_id:review.id});setReview(null);setNotice(requestErrorMessage(error)+" · 자동 재저장하지 않습니다.");}else if(error?.name!=="AbortError")setNotice(requestErrorMessage(error)+" · 저장 요청은 보내지 않았습니다.");}}
    finally{if(inspection.current===controller)inspection.current=null;sending.current=false;if(mounted.current)setBusy(false);}
  }
  return <section aria-label="건물 앵커 변경 제안">
    <button ref={inspectRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={inspect}>{receipt ? "접수 상태 다시 확인" : "건물 변경 제안 검토"}</button>
    {busy && <p id={busyId} role="status">건물 제안을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {receipt && <div ref={receiptRef} tabIndex={-1} className="effect-proposal-feedback"><BuildingProposalReceipt receipt={receipt}/></div>}
    {notice && <p ref={noticeRef} tabIndex={-1} className="effect-proposal-feedback" role="alert">{notice}</p>}
    {review && <div ref={reviewRef} tabIndex={-1} className="effect-proposal-feedback" aria-label="건물 앵커 변경 검토"><BuildingProposalReview preview={review.preview} busy={busy} busyId={busyId} onSave={save} onCancel={()=>{const restore=reviewRef.current?.contains(document.activeElement);setReview(null);if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;restoreLostFocus(document,inspectRef.current);});}}/></div>}
  </section>;
}
