// Generation-specific readiness includes runtime requirements when provided.
export function generationReady(status){
  return Boolean(status?.generation_ready ?? status?.ready);
}

// 별도 모델 파일의 준비 상태는 생성 경로의 준비 여부와 구분한다.
export function modelFilesReady(status){
  return status?.ready === true;
}
