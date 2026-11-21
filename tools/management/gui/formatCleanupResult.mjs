export function formatCleanupResult(result) {
  if (!Number.isFinite(result.deleted_bytes)) {
    return "삭제 명령을 처리했습니다. 삭제 용량은 서비스에서 제공하지 않았습니다.";
  }
  const preserved = result.skipped_jobs?.length || 0;
  const summary = "작업 " + result.deleted_jobs + "건 삭제 · " + result.deleted_bytes.toLocaleString("ko-KR") + "바이트 정리";
  return preserved ? summary + " · 삭제 제외 " + preserved + "건 보존" : summary;
}
