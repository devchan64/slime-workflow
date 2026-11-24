import {untilAborted} from './managementCommand.js';

export async function readGeneratorUsage(generator,signal,fetcher=fetch){
  const response=await untilAborted(fetcher('/management/assistant/usage/'+encodeURIComponent(generator),{cache:'no-store',signal}),signal);
  if(!response.ok)throw new Error('사용설명 조회 실패 · HTTP '+response.status);
  const result=await untilAborted(response.json(),signal);
  if(!result || typeof result.content!=='string')throw new Error('사용설명 응답을 확인할 수 없습니다.');
  return result.content;
}
