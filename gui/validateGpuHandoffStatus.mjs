export function validateGpuHandoffStatus(value,session,id,service) {
  if(!value || typeof value!=='object')throw new Error('GPU 양도 상태를 확인할 수 없습니다.');
  if(value.state==='not_found') {
    if(value.request_id!==id)throw new Error('GPU 양도 요청 ID가 일치하지 않습니다.');
  } else if(value.id!==id || value.service!==service || value.session_id!==session) {
    throw new Error('GPU 양도 접수가 현재 세션과 일치하지 않습니다.');
  }
  return value;
}
