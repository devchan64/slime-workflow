import {useEffect,useState} from 'react';
import {fluxProposalRequestId} from './fluxProposalReceipt.mjs';
import {managementCommand,untilAborted} from './managementCommand.js';
import {classifyVideoReceipt} from './videoDelegationReceipt.mjs';

/** 제안별 영상 위임 접수의 중복 여부를 확인한다. */
export function useVideoDelegationReceipt(scope,service){
  const session=scope?.session,job=scope?.job;
  const scopeKey=session && job ? JSON.stringify([session,job,service]) : '';
  const [value,setValue]=useState({state:scopeKey?'checking':'direct',scopeKey});
  const [revision,setRevision]=useState(0);
  useEffect(()=>{
    if(!scopeKey){setValue({state:'direct',scopeKey});return;}
    let active=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
    setValue({state:'checking',scopeKey});
    (async()=>{try{
      const id=await fluxProposalRequestId(session,job,service);
      const response=await untilAborted(managementCommand('hermes-agent','hermes-video-status',{request_id:id,service},{signal:controller.signal}),controller.signal);
      if(!active)return;
      setValue({...classifyVideoReceipt(response,id,service),scopeKey});
    }catch(problem){if(active)setValue({state:'unknown',error:problem.message,scopeKey});}finally{clearTimeout(timer);}})();
    return()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,job,service,revision,scopeKey]);
  return {...(value.scopeKey===scopeKey ? value : {state:scopeKey?'checking':'direct'}),
    refresh:()=>setRevision(value=>value+1),unknown:()=>setValue({state:'unknown',id:value.id,scopeKey})};
}
