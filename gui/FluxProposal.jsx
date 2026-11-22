import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import FluxImagePage from "./FluxImagePage.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";

export default function FluxProposal({job,session,snapshot,offset}) {
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [open,setOpen]=useState(false),[mounted,setMounted]=useState(false);
  async function load() {
    setBusy(true);setError("");
    try {
      setProposal(await verifyFluxProposal(managementCommand,{session,job,snapshot,offset}));
    } catch(problem) { setError(problem.message); }
    finally { setBusy(false); }
  }
  if(!proposal)return <section aria-label="FLUX 생성 제안"><button type="button" disabled={busy} onClick={load}>FLUX 생성 제안 검토</button>{error && <p role="alert">{error}</p>}</section>;
  const {service="flux-image",...inputs}=proposal;
  return <section aria-label="FLUX 생성 제안"><p>생성 폼에서 입력과 필요한 참조를 확인한 뒤 접수하세요. 접수 상태는 이 제안과 세션 작업 목록에서 다시 확인할 수 있습니다.</p>
    <button type="button" aria-expanded={open} onClick={()=>{setMounted(true);setOpen(value=>!value);}}>{open?"생성 폼 접기":"생성 폼 검토"}</button>
    {mounted && <div hidden={!open}><FluxImagePage serviceOverride={service} embedded initialInputs={inputs} receiptScope={{session,job,snapshot,offset,proposal}}/></div>}
  </section>;
}
