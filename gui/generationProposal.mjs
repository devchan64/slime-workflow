import {untilAborted} from './managementCommand.js';

const kinds={audio:'AUDIO',video:'VIDEO',writer:'WRITER'};
export function generationProposalScope(search,session,kind){
  const query=new URLSearchParams(search),job=query.get('proposal_job');
  if(!job)return null;
  const offset=query.get('proposal_offset');
  if(!/^\d+$/.test(offset || ''))throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  return {session,job,snapshot:query.get('proposal_snapshot'),offset:Number(offset),kind};
}
export async function writerProposalId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('안전한 작가 제안 접수를 확인할 수 없습니다.');
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify([session,job])));
  return 'writer_'+Array.from(new Uint8Array(digest),value=>value.toString(16).padStart(2,'0')).join('');
}
export async function readGenerationProposal(command,{session,job,snapshot,offset,kind},{signal}={}){
  const marker=kinds[kind];
  if(!marker || !/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const controller=new AbortController();let timedOut=false;
  const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',abort,{once:true});
  const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{
  if(controller.signal.aborted)throw new DOMException('대화 제안 조회가 중단됐습니다.','AbortError');
  const page=await untilAborted(command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot},{signal:controller.signal}),controller.signal);
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(m=>m.job_id===job && m.session_job_unique===true && m.job?.status?.status==='completed' && !m.job?.final_response_truncated && typeof m.job?.final_response==='string' && m.job.final_response.includes('HERMES_'+marker+'_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
  if(controller.signal.aborted)throw new DOMException('대화 제안 조회가 중단됐습니다.','AbortError');
  const response=await untilAborted(command('hermes-agent','hermes-'+kind+'-proposal',{id:job},{signal:controller.signal}),controller.signal);
  if(response.job_id!==job || !response.proposal || typeof response.proposal!=='object')throw new Error('제안을 확인할 수 없습니다.');
  const p=response.proposal;
  if(kind==='audio' && (!['music-heartmula','sfx-dasheng-audiogen'].includes(p.service) || !p.request || typeof p.request.prompt!=='string'))throw new Error('오디오 제안을 확인할 수 없습니다.');
  if(kind==='video' && (!['dwpose','wan22-animate2','wan22-fun-control','wan22-vace','wan22-i2v','minimax-h3-i2v','minimax-h3-ref2va','wan21-t2v','wan21-i2v'].includes(p.service) || typeof p.mode!=='string' || typeof p.prompt!=='string'))throw new Error('영상 제안을 확인할 수 없습니다.');
  if(kind==='writer' && (typeof p.mode!=='string' || typeof p.prompt!=='string'))throw new Error('작가 제안을 확인할 수 없습니다.');
  return p;
  }catch(error){if(timedOut)throw new Error('대화 제안 조회 시간이 초과됐습니다.');throw error;}
  finally{clearTimeout(timeout);signal?.removeEventListener('abort',abort);}
}
export function audioProposalInputs(defaults,proposal,service){
  if(!defaults || typeof defaults!=='object' || proposal?.service!==service || !proposal.request || proposal.request.action!=='generate')throw new Error('제안한 생성기와 현재 도구가 다릅니다.');
  const fields=service==='music-heartmula' ? ['prompt','lyrics','duration_seconds','seed','loop_request'] : service==='sfx-dasheng-audiogen' ? ['prompt','seed','loop_request'] : [];
  if(!fields.length || fields.some(field=>!(field in proposal.request)))throw new Error('제안 입력을 확인할 수 없습니다.');
  return {...defaults,...Object.fromEntries(fields.map(field=>[field,proposal.request[field]]))};
}
export function vaceProposalInputs(defaults,proposal){
  if(proposal?.service!=='wan22-vace' || !['text','reference','first_frame','video_edit','video_condition','pose'].includes(proposal.mode) || typeof proposal.prompt!=='string')throw new Error('제안한 영상 입력을 확인할 수 없습니다.');
  return {...defaults,mode:proposal.mode,prompt:proposal.prompt};
}
export function funProposalInputs(defaults,proposal){
  if(proposal?.service!=='wan22-fun-control' || proposal.mode!=='pose_video' || typeof proposal.prompt!=='string' || !proposal.prompt.trim())throw new Error('이 도구는 처리된 포즈 영상 제안만 입력으로 불러올 수 있습니다.');
  return {...defaults,prompt:proposal.prompt};
}
export function wan21ProposalInputs(defaults,proposal,service){
  const expected=service==='wan21-t2v'?'text':service==='wan21-i2v'?'first_frame':null;
  if(!expected || proposal?.service!==service || proposal.mode!==expected || typeof proposal.prompt!=='string' || !proposal.prompt.trim())throw new Error('제안한 영상 입력을 확인할 수 없습니다.');
  return {...defaults,prompt:proposal.prompt};
}
