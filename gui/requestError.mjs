export function requestErrorMessage(problem) {
  if (problem instanceof TypeError && /fetch|network|load failed/i.test(problem.message || "")) {
    return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  }
  return problem?.message || "요청을 처리할 수 없습니다. 다시 시도하세요.";
}
