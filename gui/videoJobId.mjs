/** 영상 생성 서비스가 이력과 결과 조회에 사용하는 작업 식별자. */
export function validVideoJobId(value){
  return typeof value==='string' && value.length===28 && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(value);
}
