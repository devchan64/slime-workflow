import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {readProposalPreview} from "./readProposalPreview.mjs";
import KimodoGeneration from "./KimodoGeneration.jsx";
import {verifyKimodoProposal} from "./kimodoProposalMembership.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import PromptWordCount from "./PromptWordCount.jsx";
import {kimodoPromptReason} from "./kimodoPromptReason.mjs";

export function KimodoProposalNumericFields({proposal,onChange}){
  return [["frames","프레임 수",30,300],["steps","생성 단계",2,100],["seed","시드",0,2147483647]].map(([key,label,min,max])=>
    <label key={key}>{label} <small>({min.toLocaleString()}~{max.toLocaleString()} 정수)</small> <input type="number" required min={min} max={max} step="1" value={proposal[key]} onChange={e=>onChange(key,e.target.value)}/></label>);
}

export default function KimodoProposal({job,session,snapshot,offset,append,openStep}){
  return <KimodoProposalForSelection key={JSON.stringify([session,job])} job={job} session={session} snapshot={snapshot} offset={offset} append={append} openStep={openStep}/>;
}
function KimodoProposalForSelection({job,session,snapshot,offset,append,openStep}){
  const busyId=useId(),promptReasonId=useId();
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [original,setOriginal]=useState(null);
  const [exampleOpen,setExampleOpen]=useState(false),[exampleMounted,setExampleMounted]=useState(false);
  const selection=useRef(null);selection.current=JSON.stringify([snapshot,offset]);
  const request=useRef(null),focusOnError=useRef(false),loadFocus=useRef(false),errorRef=useRef(null),loadRef=useRef(null),resultRef=useRef(null),exampleRef=useRef(null),exampleToggleRef=useRef(null),focusFrame=useRef(null);useEffect(()=>()=>{const current=request.current;request.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);},[]);
  useEffect(()=>{if(request.current){const current=request.current;request.current=null;current.abort();setBusy(false);setError("대화 이력이 변경됐습니다. 제안을 다시 확인하세요.");}},[snapshot,offset]);
  useEffect(()=>{if(busy || !focusOnError.current)return;focusOnError.current=false;if(!error)return;const frame=requestAnimationFrame(()=>restoreLostFocus(document,errorRef.current));return ()=>cancelAnimationFrame(frame);},[busy,error]);
  useEffect(()=>{if(busy || !loadFocus.current)return;loadFocus.current=false;if(!proposal)return;const frame=requestAnimationFrame(()=>restoreLostFocus(document,resultRef.current));return ()=>cancelAnimationFrame(frame);},[busy,proposal]);
  async function load(){
    if(request.current)return;
    focusOnError.current=document.activeElement===loadRef.current;loadFocus.current=focusOnError.current;
    const selectionAtStart=selection.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await readProposalPreview(verifyKimodoProposal,[{job,session,snapshot,offset}],controller.signal);
      if(request.current===controller){if(selection.current!==selectionAtStart)setError("대화 이력이 변경됐습니다. 제안을 다시 확인하세요.");else{setOriginal(result);setProposal(result);}}
    }catch(problem){if(request.current===controller && (!controller.signal.aborted || timedOut))setError(selection.current!==selectionAtStart ? "대화 이력이 변경됐습니다. 제안을 다시 확인하세요." : timedOut ? "Kimodo 제안 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  if(!proposal)return <section><button ref={loadRef} type="button" disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={load}>Kimodo 생성 제안 검토</button>
    {busy && <p id={busyId} role="status">Kimodo 제안을 조회하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {error && <p ref={errorRef} tabIndex={-1} className="proposal-feedback" role="alert">{error}</p>}</section>;
  if(proposal.example_id)return <section ref={resultRef} tabIndex={-1} className="conversation-kimodo-proposal proposal-feedback" aria-label="Kimodo 예제 제안">
    <p>등록된 예제 {proposal.example_id}의 설정과 참조 이미지를 생성 폼에서 불러옵니다. 아직 접수되지 않았습니다.</p>
    <button ref={exampleToggleRef} type="button" aria-expanded={exampleOpen} onClick={()=>{const restore=exampleOpen && exampleRef.current?.contains(document.activeElement);setExampleMounted(true);setExampleOpen(value=>!value);if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;restoreLostFocus(document,exampleToggleRef.current);});}}>{exampleOpen?"예제 생성 폼 접기":"예제 생성 폼 검토"}</button>
    {exampleMounted && <div ref={exampleRef} className="conversation-kimodo-form" hidden={!exampleOpen}><KimodoGeneration session={session} receiptScope={job} proposalScope={{job,session,snapshot,offset,proposal:original}} initialInputs={proposal} choose={append}/></div>}
  </section>;
  const promptReason=kimodoPromptReason(proposal.prompt);
  async function addRequest(event){
    const workflow=event.nativeEvent.submitter?.value==="workflow";
    event.preventDefault();if(request.current || promptReason)return;
    focusOnError.current=document.activeElement===event.nativeEvent.submitter;
    const selectionAtStart=selection.current;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const command=(service,name,payload)=>{if(controller.signal.aborted)return Promise.reject(new DOMException("조회가 중단됐습니다.","AbortError"));return untilAborted(managementCommand(service,name,payload,{signal:controller.signal}),controller.signal);};
      await untilAborted(verifyKimodoProposal(command,{job,session,snapshot,offset},original),controller.signal);
      if(request.current!==controller || controller.signal.aborted)return;
      if(selection.current!==selectionAtStart){setError("대화 이력이 변경됐습니다. 제안을 다시 확인하세요.");return;}
      const inputs={...proposal,frames:Number(proposal.frames),steps:Number(proposal.steps),seed:Number(proposal.seed)};
      const response=await untilAborted(fetch("/management/assistant/kimodo-proposal-review",{method:"POST",signal:controller.signal,
        headers:{"Content-Type":"application/json"},body:JSON.stringify(inputs)}),controller.signal);
      const result=await untilAborted(response.json(),controller.signal);
      if(!response.ok)throw new Error(typeof result?.detail==="string" && result.detail ? result.detail : "생성 요청을 확인하세요.");
      const checked=result?.request;
      if(!checked || typeof checked!=="object" || Array.isArray(checked) || checked.action!=="generate" || ["prompt","frames","steps","seed"].some(key=>checked[key]!==inputs[key]))throw new Error("확인 결과가 입력과 일치하지 않습니다. 다시 시도하세요.");
      if(request.current!==controller || controller.signal.aborted)return;
      if(selection.current!==selectionAtStart){setError("대화 이력이 변경됐습니다. 제안을 다시 확인하세요.");return;}
      if(workflow)openStep(inputs);
      else append("Kimodo 생성 요청",JSON.stringify(checked));
    }catch(problem){if(request.current===controller && (!controller.signal.aborted || timedOut))setError(selection.current!==selectionAtStart ? "대화 이력이 변경됐습니다. 제안을 다시 확인하세요." : timedOut ? "Kimodo 요청 확인 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;setBusy(false);}}
  }
  return <form ref={resultRef} tabIndex={-1} className="proposal-feedback" onSubmit={addRequest}>{busy && <p id={busyId} role="status">Kimodo 요청을 확인하고 있습니다. 완료될 때까지 기다리세요.</p>}<fieldset disabled={busy} aria-describedby={busy ? busyId : undefined}><legend>Kimodo 생성 제안</legend>
    <label>동작 설명 <textarea required maxLength={2000} aria-invalid={promptReason ? true : undefined} aria-describedby={promptReason ? promptReasonId : undefined} value={proposal.prompt} onChange={e=>setProposal({...proposal,prompt:e.target.value})}/></label><PromptWordCount text={proposal.prompt} label="동작 설명"/>
    <KimodoProposalNumericFields proposal={proposal} onChange={(key,value)=>setProposal({...proposal,[key]:value})}/>
    {promptReason && <p id={promptReasonId}>{promptReason}</p>}
    <button disabled={Boolean(promptReason)} aria-describedby={promptReason ? promptReasonId : undefined}>편집한 요청을 대화 입력에 추가</button>
    <button value="workflow" disabled={Boolean(promptReason)} aria-describedby={promptReason ? promptReasonId : undefined}>생성 폼에서 검토</button>
    {error && <p ref={errorRef} tabIndex={-1} className="proposal-feedback" role="alert">{error}</p>}
  </fieldset></form>;
}
