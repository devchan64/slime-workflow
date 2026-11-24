import {untilAborted} from './managementCommand.js';

export function startModelReadinessPoller({read,validate,delayForStatus,initialRetryDelay,onStart,onSuccess,onFailure,onFinish,timeoutMs=30000}){
  let active=true,timer=null,controller=null,retryDelay=initialRetryDelay;
  async function poll(){
    controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},timeoutMs);
    onStart();
    try{
      const status=await untilAborted(read(controller.signal),controller.signal);
      if(!active)return;
      if(!validate(status))throw new Error('모델 상태 응답을 확인하세요.');
      retryDelay=delayForStatus(status);
      onSuccess(status);
    }catch(problem){if(active)onFailure(problem,timedOut);}
    finally{
      clearTimeout(timeout);
      if(active){onFinish();if(retryDelay!==null)timer=setTimeout(poll,retryDelay);}
    }
  }
  poll();
  return ()=>{active=false;clearTimeout(timer);controller?.abort();};
}
