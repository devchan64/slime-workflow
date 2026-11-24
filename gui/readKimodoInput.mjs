import {untilAborted} from "./managementCommand.js";

export async function readKimodoJson(url,signal,errorMessage,fetcher=globalThis.fetch){
  if(signal.aborted)throw new DOMException("조회가 중단됐습니다.","AbortError");
  const response=await untilAborted(fetcher(url,{signal}),signal);
  if(!response.ok)throw new Error(errorMessage);
  return untilAborted(response.json(),signal);
}

export function readKimodoInput(url,signal,{restored=false,fetcher=globalThis.fetch}={}){
  return readKimodoJson(url,signal,restored ? "이전 작업의 입력을 불러올 수 없습니다." : "생성 기본값을 조회할 수 없습니다.",fetcher);
}
