export function requestErrorMessage(problem) {
  if (typeof problem?.message === "string" && problem.message.includes("SLIME_CONTENT_SERVICE_ORIGIN")) {
    return "콘텐츠 서비스 주소가 설정되지 않았거나 유효하지 않습니다. 서비스 설정을 확인하세요.";
  }
  if (problem instanceof TypeError && /fetch|network|load failed/i.test(problem.message || "")) {
    return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  }
  return problem?.message || "요청을 처리할 수 없습니다. 다시 시도하세요.";
}
