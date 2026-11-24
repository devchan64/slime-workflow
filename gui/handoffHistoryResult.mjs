import {validateGpuHandoffStatus} from './validateGpuHandoffStatus.mjs';

export function readHandoffHistoryResult(result,session,startedRevision,currentRevision){
  if(result?.session_id!==session || !Array.isArray(result.handoffs) || result.handoffs.length>20)
    throw new Error('GPU 양도 이력 응답이 일치하지 않습니다.');
  const seen=new Set();
  for(const row of result.handoffs){
    if(!row || typeof row.id!=='string' || !/^[A-Za-z0-9_-]{8,80}$/.test(row.id) || typeof row.service!=='string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.service) || seen.has(row.id))
      throw new Error('GPU 양도 이력 형식 오류');
    validateGpuHandoffStatus(row,session,row.id,row.service);seen.add(row.id);
  }
  if(startedRevision!==currentRevision)throw new Error('조회 중 양도 상태가 변경됐습니다. 이력을 다시 조회하세요.');
  return result.handoffs;
}
