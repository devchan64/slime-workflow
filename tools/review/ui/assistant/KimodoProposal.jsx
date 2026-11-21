import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function KimodoProposal({job,append}){
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  async function load(){
    setBusy(true);setError("");
    try{
      const result=await managementCommand("hermes-agent","hermes-kimodo-proposal",{id:job});
      if(result.job_id!==job || !result.proposal)throw new Error("작업의 생성 제안을 확인할 수 없습니다.");
      setProposal(result.proposal);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  if(!proposal)return <section><button type="button" disabled={busy} onClick={load}>Kimodo 생성 제안 검토</button>
    {error && <p role="alert">{error}</p>}</section>;
  return <form onSubmit={event=>{
    event.preventDefault();
    append("Kimodo 생성 요청",JSON.stringify({...proposal,frames:Number(proposal.frames),steps:Number(proposal.steps),seed:Number(proposal.seed)}));
  }}><fieldset><legend>Kimodo 생성 제안</legend>
    <label>동작 설명 <textarea required value={proposal.prompt} onChange={e=>setProposal({...proposal,prompt:e.target.value})}/></label>
    {[[ "frames","프레임 수",30,300 ],[ "steps","생성 단계",2,100 ],[ "seed","시드",0,2147483647 ]].map(([key,label,min,max])=>
      <label key={key}>{label} <input type="number" required min={min} max={max} value={proposal[key]}
        onChange={e=>setProposal({...proposal,[key]:e.target.value})}/></label>)}
    <button disabled={!proposal.prompt.trim()}>편집한 요청을 대화 입력에 추가</button>
  </fieldset></form>;
}
