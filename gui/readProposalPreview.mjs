import {managementCommand,untilAborted} from './managementCommand.js';

export async function readProposalPreview(prepare,selection,signal){
  const command=(service,name,payload)=>{
    if(signal.aborted)return Promise.reject(new DOMException('조회가 중단됐습니다.','AbortError'));
    return untilAborted(managementCommand(service,name,payload,{signal}),signal);
  };
  return untilAborted(prepare(command,...selection),signal);
}

export async function verifyProposalWithDeadline(verify,selection,controller){
  let timedOut=false;
  const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{
    await readProposalPreview(verify,selection,controller.signal);
    if(controller.signal.aborted)throw new DOMException('조회가 중단됐습니다.','AbortError');
  }catch(error){if(timedOut)throw new Error('저장 전 확인 시간이 초과됐습니다. 다시 확인하세요.');throw error;}
  finally{clearTimeout(timeout);}
}
