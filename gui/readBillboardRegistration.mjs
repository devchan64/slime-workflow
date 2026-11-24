import {untilAborted} from "./managementCommand.js";

export async function readBillboardRegistration(file,signal) {
  if(signal.aborted)throw new DOMException("조회가 중단됐습니다.","AbortError");
  const result=await untilAborted((async()=>{
    const response=await fetch("/management/assistant/billboard-registration-review",{
      method:"POST",headers:{"Content-Type":"application/json"},body:file,signal
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data?.error || "등록 요청을 확인할 수 없습니다.");
    return data;
  })(),signal);
  if(!result || typeof result.requestId!=="string" || !result.requestId || !Number.isSafeInteger(result.expectedGeneration) || typeof result.asset?.assetId!=="string" || !result.asset.assetId || typeof result.asset?.image?.path!=="string" || !Number.isFinite(result.asset.image.width) || !Number.isFinite(result.asset.image.height))throw new Error("등록 검토 응답을 확인할 수 없습니다.");
  return result;
}

export function confirmedBillboardRegistration(review,result) {
  return result?.saved===true && typeof review?.asset?.assetId==="string" && result.asset===review.asset.assetId && Number.isSafeInteger(result.generation) && result.generation===review.expectedGeneration+1;
}
