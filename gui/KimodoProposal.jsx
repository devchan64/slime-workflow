import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {readProposalPreview} from "./readProposalPreview.mjs";
import KimodoGeneration from "./KimodoGeneration.jsx";
import {verifyKimodoProposal} from "./kimodoProposalMembership.mjs";

export default function KimodoProposal({job,session,snapshot,offset,append,openStep}){
  return <KimodoProposalForSelection key={JSON.stringify([session,job])} job={job} session={session} snapshot={snapshot} offset={offset} append={append} openStep={openStep}/>;
}
function KimodoProposalForSelection({job,session,snapshot,offset,append,openStep}){
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [original,setOriginal]=useState(null);
  const [exampleOpen,setExampleOpen]=useState(false),[exampleMounted,setExampleMounted]=useState(false);
  const request=useRef(null);useEffect(()=>()=>request.current?.abort(),[]);
  useEffect(()=>{if(request.current){request.current.abort();request.current=null;setBusy(false);setError("대화 이력이 변경됐습니다. 제안을 다시 확인하세요.");}},[snapshot,offset]);
  async function load(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await readProposalPreview(verifyKimodoProposal,[{job,session,snapshot,offset}],controller.signal);
      setOriginal(result);setProposal(result);
    }catch(problem){if(request.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut ? "Kimodo 제안 조회 시간이 초과됐습니다. 다시 확인하세요." : problem.message);}
    finally{clearTimeout(timeout);if(request.current===controller){request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}}
  }
  if(!proposal)return <section><button type="button" disabled={busy} onClick={load}>Kimodo 생성 제안 검토</button>
    {busy && <p role="status">Kimodo 제안을 조회하고 있습니다.</p>}
    {error && <p role="alert">{error}</p>}</section>;
  if(proposal.example_id)return <section className="conversation-kimodo-proposal" aria-label="Kimodo 예제 제안">
    <p>등록된 예제 {proposal.example_id}의 설정과 참조 이미지를 생성 폼에서 불러옵니다. 아직 접수되지 않았습니다.</p>
    <button type="button" aria-expanded={exampleOpen} onClick={()=>{setExampleMounted(true);setExampleOpen(value=>!value);}}>{exampleOpen?"예제 생성 폼 접기":"예제 생성 폼 검토"}</button>
    {exampleMounted && <div className="conversation-kimodo-form" hidden={!exampleOpen}><KimodoGeneration session={session} receiptScope={job} proposalScope={{job,session,snapshot,offset,proposal:original}} initialInputs={proposal} choose={append}/></div>}
  </section>;
  async function addRequest(event){
    const workflow=event.nativeEvent.submitter?.value==="workflow";
    event.preventDefault();setBusy(true);setError("");
    try{
      await verifyKimodoProposal(managementCommand,{job,session,snapshot,offset},original);
      const inputs={...proposal,frames:Number(proposal.frames),steps:Number(proposal.steps),seed:Number(proposal.seed)};
      const response=await fetch("/management/assistant/kimodo-proposal-review",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(inputs)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "생성 요청을 확인하세요.");
      if(workflow)openStep(inputs);
      else append("Kimodo 생성 요청",JSON.stringify(result.request));
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <form onSubmit={addRequest}><fieldset disabled={busy}><legend>Kimodo 생성 제안</legend>
    <label>동작 설명 <textarea required maxLength={2000} value={proposal.prompt} onChange={e=>setProposal({...proposal,prompt:e.target.value})}/></label>
    {[[ "frames","프레임 수",30,300 ],[ "steps","생성 단계",2,100 ],[ "seed","시드",0,2147483647 ]].map(([key,label,min,max])=>
      <label key={key}>{label} <input type="number" required min={min} max={max} value={proposal[key]}
        onChange={e=>setProposal({...proposal,[key]:e.target.value})}/></label>)}
    <button disabled={!proposal.prompt.trim()}>편집한 요청을 대화 입력에 추가</button>
    <button value="workflow" disabled={!proposal.prompt.trim()}>생성 폼에서 검토</button>
    {error && <p role="alert">{error}</p>}
  </fieldset></form>;
}
