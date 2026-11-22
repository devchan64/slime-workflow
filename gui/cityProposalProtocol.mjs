export async function cityProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('대화·작업 식별자를 확인할 수 없습니다.');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:city`));
  return 'chat_'+Array.from(new Uint8Array(bytes),value=>value.toString(16).padStart(2,'0')).join('');
}
export function validateCityReceipt(receipt,id,map){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id || receipt.map!==map)throw new Error('도시 맵 접수 대상이 제안과 일치하지 않습니다.');
  return receipt;
}
function same(a,b){
  if(a===b)return true;
  if(!a || !b || typeof a!=='object' || typeof b!=='object' || Array.isArray(a)!==Array.isArray(b))return false;
  const ka=Object.keys(a).sort(),kb=Object.keys(b).sort();
  return ka.length===kb.length && ka.every((key,index)=>key===kb[index] && same(a[key],b[key]));
}
export function applyCityChanges(source,proposal){
  if(source.map!==proposal.map || source.generation!==proposal.generation || source.revision!==proposal.revision || !source.document || !Array.isArray(proposal.changes))throw new Error('도시 맵 원본 또는 리비전이 변경되었습니다.');
  const draft=JSON.parse(JSON.stringify(source));
  for(const change of proposal.changes){
    if(!Array.isArray(change.path) || change.path.length<2 || change.path[0]!=='data')throw new Error('도시 변경 경로를 확인할 수 없습니다.');
    let parent=draft.document;
    for(const key of change.path.slice(0,-1)){
      if((typeof key!=='string' && !Number.isInteger(key)) || ['__proto__','constructor','prototype'].includes(key) || !parent || typeof parent!=='object' || !Object.hasOwn(parent,key))throw new Error('도시 변경 경로를 확인할 수 없습니다.');
      parent=parent[key];
    }
    const key=change.path.at(-1);
    if((typeof key!=='string' && !Number.isInteger(key)) || ['__proto__','constructor','prototype'].includes(key) || !parent || typeof parent!=='object' || !Object.hasOwn(parent,key) || !same(parent[key],change.before))throw new Error('도시 맵 기존 값이 변경되었습니다.');
    parent[key]=change.after;
  }
  return draft;
}
export async function prepareCityProposal(command,session,job,snapshot,offset){
  const id=await cityProposalRequestId(session,job);
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(m=>m.job_id===job && m.session_job_unique===true && m.job?.status?.status==='completed' && !m.job?.final_response_truncated && typeof m.job?.final_response==='string' && m.job.final_response.includes('HERMES_CITY_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
  const response=await command('hermes-agent','hermes-city-proposal',{id:job});
  if(response.job_id!==job || typeof response.proposal?.map!=='string')throw new Error('도시 맵 제안을 확인할 수 없습니다.');
  const proposal=response.proposal;
  const receipt=validateCityReceipt(await command('hermes-agent','hermes-city-receipt',{request_id:id}),id,proposal.map);
  if(receipt)return {receipt};
  const source=await command('hermes-agent','hermes-city-load',{map:proposal.map});
  const draft=applyCityChanges(source,proposal);
  const preview=await command('hermes-agent','hermes-city-preview',{draft});
  if(preview.cityId!==proposal.map || !/^[a-f0-9]{64}$/.test(preview.token || '') || preview.save_available!==false)throw new Error('도시 맵 검토 결과를 확인할 수 없습니다.');
  return {proposal,preview};
}
