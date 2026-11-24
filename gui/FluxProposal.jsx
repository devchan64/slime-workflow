import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import FluxImagePage from "./FluxImagePage.jsx";
import {useMinimaxReportReceipt,MinimaxReportStatus} from "./useMinimaxReportReceipt.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import {formStateLabel} from './minimaxFormState.mjs';

export default function FluxProposal({job,session,snapshot,offset,onOpenForm}) {
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [open,setOpen]=useState(false),[mounted,setMounted]=useState(false);
  const [prepared,setPrepared]=useState(null);
  const minimaxReceipt=useMinimaxReportReceipt(proposal?.service==="minimax-h3-image" ? {session,job} : null,"minimax-h3-image");
  useEffect(()=>{
    let active=true,timer,attempts=0;const controller=new AbortController();
    async function refresh(){
      attempts++;
      try{
        const listed=await managementCommand('hermes-agent','hermes-minimax-form-list',{session_id:session},{signal:controller.signal});
        if(!Array.isArray(listed?.forms))throw new Error('접수폼 목록을 확인할 수 없습니다.');
        const matches=listed.forms.filter(form=>form.source_job_id===job && form.service==='minimax-h3-image');
        if(matches.length>1)throw new Error('같은 제안에 연결된 접수폼이 여러 개입니다. 목록을 확인하세요.');
        if(matches.length===0)return;
        const checked=await verifyFluxProposal((...args)=>managementCommand(...args.slice(0,3),{signal:controller.signal}),{session,job,snapshot,offset});
        if(!active || checked.service!=="minimax-h3-image")return;
        if(active){setProposal(checked);setPrepared(matches[0]);setError('');}
      }catch(problem){if(active && problem.name!=='AbortError')setError(problem.message || '접수폼 준비 상태를 확인할 수 없습니다.');}
      finally{if(active)timer=setTimeout(refresh,attempts<12?5000:60000);}
    }
    refresh();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,job,snapshot,offset]);
  async function load() {
    setBusy(true);setError("");
    try {
      setProposal(await verifyFluxProposal(managementCommand,{session,job,snapshot,offset}));
    } catch(problem) { setError(problem.message); }
    finally { setBusy(false); }
  }
  if(!proposal)return <section aria-label="이미지 생성 제안"><button type="button" disabled={busy} onClick={load}>이미지 생성 제안 검토</button>{error && <p role="alert">{error}</p>}</section>;
  const {service="flux-image",selection_reason,...inputs}=proposal;
  if(prepared)return <section aria-label="이미지 생성 제안"><p>MiniMax 이미지 접수폼 {prepared.form_id.slice(0,8)} · v{prepared.revision} · {formStateLabel(prepared.state,prepared.receipt_state)}</p>{onOpenForm && <button type="button" onClick={()=>onOpenForm(prepared.form_id)}>접수폼 열기</button>}<MinimaxReportStatus receipt={minimaxReceipt}/>{error && <p role="alert">{error}</p>}</section>;
  if(service==="minimax-h3-image")return <section aria-label="이미지 생성 제안"><p>이 제안에 연결된 MiniMax 이미지 접수폼이 아직 확인되지 않았습니다. 준비된 폼은 이 대화의 우측 패널에서 확인할 수 있습니다.</p><MinimaxReportStatus receipt={minimaxReceipt}/>{error && <p role="alert">{error}</p>}</section>;
  return <section aria-label="이미지 생성 제안"><p>선택 생성기: {service}{selection_reason && " · "+selection_reason}</p>{error && <p role="alert">{error}</p>}{service==="minimax-h3-image" && <MinimaxReportStatus receipt={minimaxReceipt}/>}<p>생성 폼에서 입력과 필요한 참조를 확인한 뒤 접수하세요. 접수와 보고 상태는 이 생성 폼에서 다시 확인할 수 있습니다.</p>
    <button type="button" aria-expanded={open} onClick={()=>{setMounted(true);setOpen(value=>!value);}}>{open?"생성 폼 접기":"생성 폼 검토"}</button>
    {mounted && <div hidden={!open}><FluxImagePage serviceOverride={service} embedded initialInputs={inputs} receiptScope={{session,job,snapshot,offset,proposal}}/></div>}
  </section>;
}
