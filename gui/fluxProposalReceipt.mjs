// A proposal has one receipt across tabs; the gateway also locks this ID.
export async function fluxProposalRequestId(session,job,service) {
  if(!/^[a-f0-9]{32}$/.test(session || "") || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || "") || !/^(?:flux-[a-z]+|minimax-h3-image|minimax-h3-i2v)$/.test(service || "")) throw new Error("대화 또는 제안의 식별자를 확인할 수 없습니다.");
  if(!globalThis.crypto?.subtle) throw new Error("안전한 접수 확인을 사용할 수 없습니다. localhost 또는 HTTPS 주소로 관리 화면을 열어 주세요.");
  const bytes=new TextEncoder().encode(JSON.stringify([session,job,service]));
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  return "flux_"+Array.from(new Uint8Array(digest),value=>value.toString(16).padStart(2,"0")).join("");
}

export function classifyFluxProposalReceipt(value,requestId,service) {
  if(!value || value.request_id!==requestId || value.service!==service) throw new Error("접수 기록이 일치하지 않습니다.");
  if(value.state==="not_found")return {state:"editing"};
  if(value.state==="rejected")return {state:"rejected"};
  if(value.state==="accepted" && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(value.job_id || ""))return {state:"accepted",job:value.job_id};
  return {state:"unknown"};
}

export async function verifyFluxProposal(command,scope,proposal){
  const {session,job,snapshot,offset}=scope || {};
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다. 대화를 다시 조회하세요.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(message=>message.job_id===job && message.session_job_unique===true && message.job?.status?.status==='completed' && !message.job?.final_response_truncated && typeof message.job?.final_response==='string' && message.job.final_response.includes('HERMES_FLUX_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 FLUX 제안 작업을 확인할 수 없습니다. 대화를 다시 조회하세요.');
  const result=await command('hermes-agent','hermes-flux-proposal',{id:job});
  if(result.job_id!==job || !result.proposal || (proposal && JSON.stringify(result.proposal)!==JSON.stringify(proposal)))throw new Error('FLUX 제안이 변경되었습니다. 대화를 다시 조회하세요.');
  return result.proposal;
}
