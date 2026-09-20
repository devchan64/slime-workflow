#!/usr/bin/env bash
set -Eeuo pipefail

AREA="ai-design-runtime"
STEP="install-fluidsynth"
DRY_RUN="false"
ASSUME_YES="false"

log() {
  local level="$1"; shift
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${AREA}] [${STEP}] [${level}] $*"
}

on_error() {
  local exit_code=$?
  local line_no=$1
  log "ERROR" "실패 지점: line=${line_no}, command=${BASH_COMMAND}, exit=${exit_code}"
  exit "${exit_code}"
}
trap 'on_error $LINENO' ERR

usage() {
  cat <<'USAGE'
사용법:
  scripts/install_fluidsynth.sh [--dry-run] [--yes]

설명:
  Ubuntu/Debian 계열에서 fluidsynth 시스템 패키지를 설치한다.
  현재 사용자가 root가 아니면 sudo를 사용한다.

옵션:
  --dry-run   실제 설치 대신 실행 예정 명령만 출력
  --yes       apt-get에 -y 옵션을 전달
  -h, --help  도움말 출력
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN="true"; shift ;;
    --yes) ASSUME_YES="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) log "ERROR" "알 수 없는 인자: $1"; usage; exit 1 ;;
  esac
done

command -v apt-get >/dev/null 2>&1 || { log "ERROR" "apt-get 명령이 없어 Debian/Ubuntu 계열이 아닌 것으로 보인다"; exit 1; }

APT_PREFIX=()
if [[ "${EUID}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    APT_PREFIX=(sudo)
  else
    log "ERROR" "root 권한이 아니고 sudo도 없어 설치를 진행할 수 없다"
    exit 1
  fi
fi

APT_YES=()
if [[ "${ASSUME_YES}" == "true" ]]; then
  APT_YES=(-y)
fi

UPDATE_CMD=("${APT_PREFIX[@]}" apt-get update)
INSTALL_CMD=("${APT_PREFIX[@]}" apt-get install "${APT_YES[@]}" fluidsynth)

log "INFO" "설치 준비 완료: dry_run=${DRY_RUN}, assume_yes=${ASSUME_YES}, user=$(id -un)"
log "INFO" "업데이트 명령: ${UPDATE_CMD[*]}"
log "INFO" "설치 명령: ${INSTALL_CMD[*]}"

if [[ "${DRY_RUN}" == "true" ]]; then
  log "INFO" "DRY-RUN 모드로 종료한다"
  exit 0
fi

"${UPDATE_CMD[@]}"
"${INSTALL_CMD[@]}"

if command -v fluidsynth >/dev/null 2>&1; then
  log "INFO" "설치 완료: $(command -v fluidsynth)"
  fluidsynth --version || true
else
  log "ERROR" "패키지 설치 후에도 fluidsynth 바이너리를 찾지 못했다"
  exit 1
fi
