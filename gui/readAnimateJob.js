import {untilAborted} from "./managementCommand.js";
export async function readAnimateJob(id,{signal}={}){
  const prefix="/management/assistant/animate-input/"+encodeURIComponent(id);
  const controller=new AbortController();let timedOut=false;
  const cancel=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",cancel,{once:true});
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{
    const response=await untilAborted(fetch(prefix+"/request",{cache:"no-store",signal:controller.signal}),controller.signal);
    if(!response.ok)throw new Error("저장된 입력을 확인할 수 없습니다.");
    let record;
    try{record=await untilAborted(response.json(),controller.signal);}catch(problem){if(controller.signal.aborted)throw problem;throw new Error("저장된 입력 형식을 확인할 수 없습니다.");}
    if(!record || record.id!==id || !record.request || typeof record.request.prompt!=="string" ||
      ![record.request.frames,record.request.steps,record.request.seed].every(Number.isInteger) || !['none','lightx2v'].includes(record.request.lora_mode ?? 'none') ||
      record.reference!==prefix+"/reference" || record.motion!==prefix+"/motion")throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
    return record;
  }catch(problem){if(timedOut)throw new Error("저장된 입력 조회 시간이 초과됐습니다.");throw problem;}
  finally{clearTimeout(timer);signal?.removeEventListener("abort",cancel);}
}
