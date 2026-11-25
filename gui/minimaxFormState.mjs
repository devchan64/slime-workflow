export const formStateLabel=(state,receiptState)=>state==='external_receipt'
  ? ({accepted:'기존 경로 접수됨',rejected:'기존 접수 거부됨'}[receiptState] || '기존 접수 확인 필요')
  : ({editing:'수정 가능',submitting:'접수 상태 확인 중',accepted:'생성 대기열 등록 완료'}[state] || '상태 확인 필요');
