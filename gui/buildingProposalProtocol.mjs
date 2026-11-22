import {billboardProposalRequestId,validateBillboardReceipt} from './billboardProposalProtocol.mjs';

import {spriteProposalRequestId} from './spriteProposalProtocol.mjs';
import {effectProposalRequestId,validateEffectReceipt} from './effectProposalProtocol.mjs';
import {cityProposalRequestId,validateCityReceipt} from './cityProposalProtocol.mjs';
import {fieldProposalRequestId,validateFieldReceipt} from './fieldProposalProtocol.mjs';

export async function verifyBuildingProposalMembership(command,session,job,snapshot,offset){
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.snapshot!==snapshot || page.offset!==offset || !Array.isArray(page.messages) ||
     page.messages.filter(message=>message.job_id===job && message.session_job_unique===true &&
       message.job?.status?.status==='completed' && !message.job?.final_response_truncated &&
       typeof message.job?.final_response==='string' && message.job.final_response.includes('HERMES_BUILDING_PROPOSAL')).length!==1)
    throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다. 대화를 다시 조회하세요.');
}

export async function verifyBuildingProposalBeforeSave(command,session,job,review){
  await verifyBuildingProposalMembership(command,session,job,review.snapshot,review.offset);
  const current=await command('hermes-agent','hermes-building-proposal',{id:job});
  if(current.job_id!==job || JSON.stringify(current.proposal)!==JSON.stringify(review.draft))
    throw new Error('검토한 건물 제안이 변경되었습니다. 다시 검토하세요.');
}

export async function prepareBuildingProposal(command,session,job,snapshot,offset){
  const id=await buildingProposalRequestId(session,job);
  await verifyBuildingProposalMembership(command,session,job,snapshot,offset);
  const response=await command('hermes-agent','hermes-building-proposal',{id:job});
  if(response.job_id!==job || !response.proposal?.texture)throw new Error('건물 제안을 확인할 수 없습니다.');
  const receipt=await command('hermes-agent','hermes-building-receipt',{request_id:id});
  if(receipt.state!=='not_found'){
    buildingReceiptStatus(receipt,id,response.proposal.texture);
    return {receipt:{...receipt,request_id:id}};
  }
  const preview=await command('hermes-agent','hermes-building-preview',{draft:response.proposal});
  if(preview.texture!==response.proposal.texture || !preview.before || !preview.after || !Array.isArray(preview.maps) || !/^[a-f0-9]{64}$/.test(preview.review_sha256 || ''))throw new Error('건물 검토 결과를 확인할 수 없습니다.');
  return {review:{id,draft:response.proposal,preview,snapshot,offset}};
}
export async function buildingProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)
    throw new Error('대화·작업 식별자 또는 안전한 접수 기능을 확인하세요.');
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:building`));
  return 'chat_'+Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
}

export function buildingReceiptStatus(receipt,id,texture){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id || (receipt.texture && receipt.texture!==texture))throw new Error('접수 대상이 제안과 일치하지 않습니다.');
  if(receipt.state!=='completed' || receipt.saved!==true)return '접수 확인 필요';
  const status=receipt.texture ? '건물 앵커 저장 기록 · '+receipt.texture : '저장 기록 · 건물 대상 미확인';
  return status+(receipt.ledger_status_at_save==='pending' ? ' · 저장 당시 원장 반영 대기' : '');
}

export async function readBuildingSessionReceipts(command,session,offset=0,snapshot){
  const payload={session_id:session,offset,limit:6,...(snapshot ? {snapshot}:{})};
  const view=await command('hermes-agent','hermes-session-view',payload);
  if(view.id!==session || view.offset!==offset || !Array.isArray(view.messages) || !/^[a-f0-9]{64}$/.test(view.snapshot || '') || (snapshot && view.snapshot!==snapshot))throw new Error('대화 이력 페이지를 확인할 수 없습니다.');
  const rows=[];
  for(const message of view.messages){
    const answer=message.job?.final_response || '';
    if(answer.includes('HERMES_FIELD_PROPOSAL')){
      if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){rows.push([message.job_id || '확인 불가','야외 맵 제안 또는 접수 조회 불가','GPU 작업 아님']);}
      else try{
        const id=await fieldProposalRequestId(session,message.job_id);
        const proposal=await command('hermes-agent','hermes-field-proposal',{id:message.job_id});
        if(proposal.job_id!==message.job_id || typeof proposal.proposal?.map!=='string')throw new Error();
        const receipt=validateFieldReceipt(await command('hermes-agent','hermes-field-receipt',{request_id:id}),id,proposal.proposal.map);
        if(receipt)rows.push([message.job_id,receipt.state==='completed' && receipt.saved===true ? '야외 맵 저장 기록 · '+receipt.map : '야외 맵 접수 확인 필요','GPU 작업 아님']);
      }catch{rows.push([message.job_id,'야외 맵 제안 또는 접수 조회 불가','GPU 작업 아님']);}
    }
    if(answer.includes('HERMES_CITY_PROPOSAL')){
      if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){rows.push([message.job_id || '확인 불가','도시 맵 제안 또는 접수 조회 불가','GPU 작업 아님']);}
      else try{
        const id=await cityProposalRequestId(session,message.job_id);
        const proposal=await command('hermes-agent','hermes-city-proposal',{id:message.job_id});
        if(proposal.job_id!==message.job_id || typeof proposal.proposal?.map!=='string')throw new Error();
        const receipt=validateCityReceipt(await command('hermes-agent','hermes-city-receipt',{request_id:id}),id,proposal.proposal.map);
        if(receipt)rows.push([message.job_id,receipt.state==='completed' && receipt.saved===true ? '도시 DB 저장 기록 · '+receipt.map : '도시 맵 접수 확인 필요','GPU 작업 아님']);
      }catch{rows.push([message.job_id,'도시 맵 제안 또는 접수 조회 불가','GPU 작업 아님']);}
    }
    if(answer.includes('HERMES_EFFECT_PROPOSAL')){
      if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){
        rows.push([message.job_id || '확인 불가','이펙트 제안 또는 접수 조회 불가','GPU 작업 아님']);
      }else{
        try{
          const id=await effectProposalRequestId(session,message.job_id);
          const proposal=await command('hermes-agent','hermes-effect-proposal',{id:message.job_id});
          if(proposal.job_id!==message.job_id || typeof proposal.proposal?.id!=='string')throw new Error();
          const receipt=validateEffectReceipt(await command('hermes-agent','hermes-effect-receipt',{request_id:id}),id,proposal.proposal.id);
          if(receipt){
            const status=receipt.state==='completed' && receipt.saved===true ? (receipt.effect_id ? '이펙트 저장 기록 · '+receipt.effect_id : '이펙트 저장 기록 · 대상 미확인') : '이펙트 접수 확인 필요';
            rows.push([message.job_id,status+(receipt.ledger_status_at_save==='pending' ? ' · 저장 당시 원장 반영 대기' : ''),'GPU 작업 아님']);
          }
        }catch{rows.push([message.job_id,'이펙트 제안 또는 접수 조회 불가','GPU 작업 아님']);}
      }
    }
    if(answer.includes('HERMES_SPRITE_PROPOSAL')){
      if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){
        rows.push([message.job_id || '확인 불가','스프라이트 제안 또는 접수 조회 불가','GPU 작업 아님']);
      }else{
        try{
          const id=await spriteProposalRequestId(session,message.job_id);
          const proposal=await command('hermes-agent','hermes-sprite-proposal',{id:message.job_id});
          if(proposal.job_id!==message.job_id || typeof proposal.proposal?.path!=='string')throw new Error();
          const receipt=await command('hermes-agent','hermes-sprite-receipt',{request_id:id});
          if(receipt.state!=='not_found'){
            if(receipt.request_id!==id || (receipt.path && receipt.path!==proposal.proposal.path))throw new Error();
            const status=receipt.state==='completed' && receipt.saved===true ? (receipt.path ? '스프라이트 저장 기록 · '+receipt.path : '스프라이트 저장 기록 · 대상 미확인') : '스프라이트 접수 확인 필요';
            rows.push([message.job_id,status,'GPU 작업 아님']);
          }
        }catch{rows.push([message.job_id,'스프라이트 제안 또는 접수 조회 불가','GPU 작업 아님']);}
      }
    }
    if(answer.includes('HERMES_BILLBOARD_PROPOSAL')){
      if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){
        rows.push([message.job_id || '확인 불가','빌보드 제안 또는 접수 조회 불가','GPU 작업 아님']);
      }else{
        try{
          const id=await billboardProposalRequestId(session,message.job_id);
          const proposal=await command('hermes-agent','hermes-billboard-proposal',{id:message.job_id});
          if(proposal.job_id!==message.job_id || typeof proposal.proposal?.texture!=='string')throw new Error();
          const receipt=validateBillboardReceipt(await command('hermes-agent','hermes-billboard-receipt',{request_id:id}),id,[{texture:proposal.proposal.texture}]);
          if(receipt){
            const status=receipt.state==='completed' && receipt.saved===true ? (receipt.textures ? '빌보드 저장 기록 · '+receipt.textures.join(', ') : '빌보드 저장 기록 · 대상 미확인') : '빌보드 접수 확인 필요';
            rows.push([message.job_id,status+(receipt.ledger_status_at_save==='pending' ? ' · 저장 당시 원장 반영 대기' : ''),'GPU 작업 아님']);
          }
        }catch{rows.push([message.job_id,'빌보드 제안 또는 접수 조회 불가','GPU 작업 아님']);}
      }
    }
    if(!answer.includes('HERMES_BUILDING_PROPOSAL'))continue;
    if(message.session_job_unique!==true || message.job?.status?.status!=='completed' || message.job?.final_response_truncated){
      rows.push([message.job_id || '확인 불가','제안 또는 접수 조회 불가','GPU 작업 아님']);continue;
    }
    try{
      const id=await buildingProposalRequestId(session,message.job_id);
      const proposal=await command('hermes-agent','hermes-building-proposal',{id:message.job_id});
      if(proposal.job_id!==message.job_id || !proposal.proposal?.texture)throw new Error();
      const receipt=await command('hermes-agent','hermes-building-receipt',{request_id:id});
      const status=buildingReceiptStatus(receipt,id,proposal.proposal.texture);
      if(status!==null)rows.push([message.job_id,status,'GPU 작업 아님']);
    }catch{rows.push([message.job_id,'제안 또는 접수 조회 불가','GPU 작업 아님']);}
  }
  const verified=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot:view.snapshot});
  if(verified.id!==session || verified.offset!==offset || verified.snapshot!==view.snapshot)throw new Error('조회 중 대화 이력이 변경되었습니다. 다시 조회하세요.');
  return {page:view,rows};
}
