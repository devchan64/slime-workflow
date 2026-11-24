import {validVideoJobId} from './videoJobId.mjs';

export function classifyVideoReceipt(response,id,service){
  const receipt=response?.receipt;
  if(receipt?.request_id!==id || receipt.service!==service)throw new Error('접수 기록이 일치하지 않습니다.');
  if(receipt.state==='not_found')return {state:'editing',id};
  if(receipt.state==='accepted' && validVideoJobId(receipt.job_id))return {state:'accepted',id,job:receipt.job_id};
  return {state:'unknown',id};
}
