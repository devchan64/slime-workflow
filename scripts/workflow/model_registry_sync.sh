#!/usr/bin/env bash
set -Eeuo pipefail

AREA="ai-workflow"
STEP="model-registry-sync"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REGISTRY_PATH="${ROOT_DIR}/workflow/nodes/concept_image/packages/model-registry.json"
STORAGE_CONFIG_PATH="${ROOT_DIR}/workflow/nodes/concept_image/packages/model-storage-paths.json"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"

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

log "INFO" "workflow 모델 레지스트리 동기화 시작"
PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" -m workflow.nodes.concept_image.runtime.model_registry_sync \
  --registry "${REGISTRY_PATH}" \
  --storage-config "${STORAGE_CONFIG_PATH}" \
  "$@"
log "INFO" "workflow 모델 레지스트리 동기화 종료"
