function validProposal(value){
  if(!value || typeof value!=='object' || Array.isArray(value))return false;
  const keys=Object.keys(value).sort();
  if(keys.length===1 && keys[0]==='example_id')return typeof value.example_id==='string' && Boolean(value.example_id.trim());
  return keys.join(',')==='frames,prompt,seed,steps' && typeof value.prompt==='string' && Boolean(value.prompt.trim()) && value.prompt.length<=2000 && Number.isInteger(value.frames) && value.frames>=30 && value.frames<=300 && Number.isInteger(value.steps) && value.steps>=2 && value.steps<=100 && Number.isInteger(value.seed) && value.seed>=0 && value.seed<=2147483647;
}

export async function verifyKimodoProposal(command,{session,job,snapshot,offset},proposal){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다. 대화를 다시 조회하세요.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(message=>message.job_id===job && message.session_job_unique===true && message.job?.status?.status==='completed' && !message.job?.final_response_truncated && typeof message.job?.final_response==='string' && message.job.final_response.includes('HERMES_KIMODO_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 Kimodo 제안 작업을 확인할 수 없습니다. 대화를 다시 조회하세요.');
  const result=await command('hermes-agent','hermes-kimodo-proposal',{id:job});
  if(result?.job_id!==job || !validProposal(result.proposal))throw new Error('Kimodo 제안을 확인할 수 없습니다. 대화를 다시 조회하세요.');
  if(proposal && JSON.stringify(result.proposal)!==JSON.stringify(proposal))throw new Error('Kimodo 제안이 변경되었습니다. 대화를 다시 조회하세요.');
  return result.proposal;
}
