#!/usr/bin/env bash
set -Eeuo pipefail

AREA="ai-workflow"
STEP="workflow-unit-tests-docker"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
WORKFLOW_TEST_DOCKER_IMAGE="${WORKFLOW_TEST_DOCKER_IMAGE:-python:3.12-slim}"

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

log "INFO" "워크플로우 유닛테스트를 Docker 컨테이너에서 실행합니다."

exec "${DOCKER_BIN}" run --rm \
  -v "${ROOT_DIR}:/workspace" \
  -w /workspace \
  -e PYTHONPATH="/workspace" \
  "${WORKFLOW_TEST_DOCKER_IMAGE}" \
  /bin/bash -lc "python -m unittest discover -s workflow -p 'test_*.py'"
