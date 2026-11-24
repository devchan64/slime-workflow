import {requestErrorMessage} from "./requestError.mjs";

export function validEffectSaveResponse(result){
  return Boolean(result && result.saved===true && typeof result.revision==="string" && /^[a-f0-9]{64}$/.test(result.revision) && Number.isSafeInteger(result.generation) && result.generation>=0);
}

export function effectSaveFailure(problem,dispatched){
  return (dispatched ? "저장 결과를 확인하지 못했습니다. 다시 저장하기 전에 원본과 이력을 확인하세요. · " : "저장 요청을 보내지 못했습니다. · ")+requestErrorMessage(problem);
}

export function effectSaveNotice(result){
  return "이펙트 정렬을 저장했습니다. · "+(result.snapshot==="pending" ? "저장 당시 원장 반영 대기" : "원장 반영 상태는 아래에서 확인하세요.");
}
