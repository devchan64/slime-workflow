import {untilAborted} from './managementCommand.js';
import {requestErrorMessage} from './requestError.mjs';

/** 동일 저장소의 동시 이력 조회만 제한적으로 재시도한다. */
export async function historyObserveRetry(read,signal,wait=()=>new Promise(resolve=>setTimeout(resolve,1000))){
  for(let attempt=0;attempt<3;attempt++){
    signal.throwIfAborted();
    try{return await untilAborted(read(),signal);}
    catch(error){
      if(signal?.aborted || attempt===2 || !requestErrorMessage(error).includes('이력 조회가 이미 진행 중'))throw error;
      await untilAborted(wait(),signal);
    }
  }
}
