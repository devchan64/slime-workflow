#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STEP="export-music-spec-runtime-patch"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/.result/workflow/local-apply"
mkdir -p "${LOG_DIR}"
LOG_PATH="${LOG_DIR}/export.log"
exec > >(tee -a "${LOG_PATH}") 2>&1

log() {
  local level="$1"; shift
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${AREA}] [${STEP}] [${level}] $*"
}

on_error() {
  local exit_code=$?
  local line_no=$1
  log "ERROR" "line=${line_no} command=${BASH_COMMAND} exit=${exit_code}"
  tail -n 120 "${LOG_PATH}" || true
  exit "${exit_code}"
}
trap 'on_error $LINENO' ERR

BASE_REF_INPUT="${1:-origin/main}"
OUT_PATH="${2:-${ROOT_DIR}/.result/workflow/local-apply/music-spec-runtime.patch}"
INCLUDE_PATHS_RAW="${3:-}"

resolve_base_ref() {
  local requested="$1"
  if git -C "${ROOT_DIR}" rev-parse --verify "${requested}" >/dev/null 2>&1; then
    echo "${requested}"
    return 0
  fi
  if git -C "${ROOT_DIR}" rev-parse --verify "origin/main" >/dev/null 2>&1; then
    echo "origin/main"
    return 0
  fi
  if git -C "${ROOT_DIR}" rev-parse --verify "main" >/dev/null 2>&1; then
    echo "main"
    return 0
  fi
  if git -C "${ROOT_DIR}" rev-parse --verify "HEAD~1" >/dev/null 2>&1; then
    echo "HEAD~1"
    return 0
  fi
  return 1
}

if ! BASE_REF="$(resolve_base_ref "${BASE_REF_INPUT}")"; then
  log "ERROR" "기준 ref를 찾을 수 없습니다: requested=${BASE_REF_INPUT}, fallback=[origin/main, main, HEAD~1]"
  exit 1
fi

log "INFO" "base_ref=${BASE_REF} (requested=${BASE_REF_INPUT})"
log "INFO" "out_path=${OUT_PATH}"

mkdir -p "$(dirname "${OUT_PATH}")"

if [[ -n "${INCLUDE_PATHS_RAW}" ]]; then
  IFS=',' read -r -a INCLUDE_PATHS <<< "${INCLUDE_PATHS_RAW}"
else
  INCLUDE_PATHS=(
    "workflow/pipelines"
    "workflow/nodes"
    "workflow/tests/fixtures/music-composer"
    "workflow/pipelines/tests"
    "scripts/workflow/export_music_spec_runtime_patch.sh"
    "docs/design/20260507-000000-local-apply-music-spec-runtime.md"
  )
fi
log "INFO" "include_paths=${INCLUDE_PATHS[*]}"

git -C "${ROOT_DIR}" diff --binary "${BASE_REF}"...HEAD -- "${INCLUDE_PATHS[@]}" > "${OUT_PATH}"
log "INFO" "패치 생성 완료: ${OUT_PATH}"
log "INFO" "적용 예시: git apply --3way ${OUT_PATH}"
