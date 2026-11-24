import {untilAborted} from './managementCommand.js';

export async function verifyPriorityTarget(verify,controller,timeoutMs=30000){
  let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},timeoutMs);
  try{
    await untilAborted(Promise.resolve().then(()=>{if(controller.signal.aborted)throw new DOMException('조회가 중단됐습니다.','AbortError');return verify?.();}),controller.signal);
    if(controller.signal.aborted)throw new DOMException('조회가 중단됐습니다.','AbortError');
  }catch(error){
    if(timedOut)throw new Error('요청 전 대상 확인 시간이 초과됐습니다. 순서 변경 요청은 보내지 않았습니다.');
    if(error.name==='AbortError')throw error;
    throw new Error(error.message+' · 순서 변경 요청은 보내지 않았습니다.');
  }finally{clearTimeout(timer);}
}
