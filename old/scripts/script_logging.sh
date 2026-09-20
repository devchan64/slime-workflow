#!/usr/bin/env bash
# 실행 로그 저장과 장시간 작업 진행 상태를 공통으로 관리한다.
SCRIPT_LOG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_LOG_AREA="$(basename "$0" .sh)"
SCRIPT_LOG_DIR="${SCRIPT_LOG_ROOT}/.local/logs"
mkdir -p "$SCRIPT_LOG_DIR"
SCRIPT_LOG_FILE="${SCRIPT_LOG_DIR}/${SCRIPT_LOG_AREA}-$(date '+%Y%m%d-%H%M%S')-$$.log"
exec > >(tee -a "$SCRIPT_LOG_FILE") 2>&1
printf '%s/%s/start 로그: %s\n' "$(date -Iseconds)" "$SCRIPT_LOG_AREA" "$SCRIPT_LOG_FILE"
(
  while sleep 5; do
    printf '%s/%s/heartbeat 진행 중, 로그 줄 수: %s, 로그 바이트: %s\n' \
      "$(date -Iseconds)" "$SCRIPT_LOG_AREA" "$(wc -l < "$SCRIPT_LOG_FILE")" "$(wc -c < "$SCRIPT_LOG_FILE")"
    tail -n 2 "$SCRIPT_LOG_FILE"
  done
) &
SCRIPT_LOG_HEARTBEAT_PID=$!
script_log_exit() {
  local status=$?
  trap - EXIT
  kill "$SCRIPT_LOG_HEARTBEAT_PID" 2>/dev/null || true
  wait "$SCRIPT_LOG_HEARTBEAT_PID" 2>/dev/null || true
  printf '%s/%s/finish 종료 코드: %s\n' "$(date -Iseconds)" "$SCRIPT_LOG_AREA" "$status"
  if [[ "$status" -ne 0 ]]; then
    tail -n 30 "$SCRIPT_LOG_FILE" >&2
  fi
  exit "$status"
}
trap script_log_exit EXIT
trap 'printf "%s/%s/error line=%s command=%s\n" "$(date -Iseconds)" "$SCRIPT_LOG_AREA" "$LINENO" "$BASH_COMMAND"' ERR
