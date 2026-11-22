export async function readCaptureProposal(command,{session,job,snapshot,offset}){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(m=>m.job_id===job && m.session_job_unique===true && m.job?.status?.status==='completed' && !m.job?.final_response_truncated && typeof m.job?.final_response==='string' && m.job.final_response.includes('HERMES_CAPTURE_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 캡처 제안 작업을 확인할 수 없습니다.');
  const response=await command('hermes-agent','hermes-capture-proposal',{id:job});
  const proposal=response.proposal,registration=response.map_registration;
  if(response.job_id!==job || !proposal || !['map-review','character-review'].includes(proposal.service) || !proposal.settings || typeof proposal.settings!=='object' || !registration || !['registered','not_registered','unavailable','not_applicable'].includes(registration.status))throw new Error('캡처 제안을 확인할 수 없습니다.');
  if(proposal.service==='map-review' && (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(proposal.settings.map || '') || registration.map!==proposal.settings.map || registration.status==='not_applicable'))throw new Error('맵 등록 정보가 제안과 일치하지 않습니다.');
  if(proposal.service==='character-review' && registration.status!=='not_applicable')throw new Error('캡처 등록 정보를 확인할 수 없습니다.');
  return {proposal,registration};
}
