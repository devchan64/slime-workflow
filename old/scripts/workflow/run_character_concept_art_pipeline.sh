#!/usr/bin/env bash
set -Eeuo pipefail

AREA="ai-workflow"
STEP="character-concept-art"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

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

log "INFO" "캐릭터 컨셉아트 파이프라인 실행"
PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" -m workflow.pipelines.character_concept_art_generator "$@"
