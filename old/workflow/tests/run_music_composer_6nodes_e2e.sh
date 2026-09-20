#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STAGE="music-composer-6nodes-e2e"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/.result/workflow/tests/music-composer-6nodes-e2e/${RUN_ID}"
LOG_PATH="${RESULT_DIR}/run.log"
STATE_PATH="${RESULT_DIR}/state.txt"
SPEC_PATH="${ROOT_DIR}/workflow/pipelines/specs/music-composer-6nodes.json"
INPUT_PATH="${ROOT_DIR}/workflow/tests/fixtures/pipelines/music-composer-6nodes.input.json"
OUT_PATH="${RESULT_DIR}/pipeline-result.json"

mkdir -p "${RESULT_DIR}"
exec > >(tee -a "${LOG_PATH}") 2>&1

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { local level="$1"; shift; echo "[$(ts)] [${AREA}] [${STAGE}] [${level}] $*"; }
write_state() { printf '%s\n' "$1" > "${STATE_PATH}"; }

HEARTBEAT_PID=""
start_heartbeat() {
  (
    while true; do
      sleep 5
      step="unknown"; [[ -f "${STATE_PATH}" ]] && step="$(cat "${STATE_PATH}" 2>/dev/null || echo unknown)"
      lines="0"; [[ -f "${LOG_PATH}" ]] && lines="$(wc -l < "${LOG_PATH}" | tr -d ' ')"
      artifacts="0"; [[ -d "${RESULT_DIR}" ]] && artifacts="$(find "${RESULT_DIR}" -type f | wc -l | tr -d ' ')"
      log "HEARTBEAT" "progress=${step} log_lines=${lines} artifacts=${artifacts}"
    done
  ) &
  HEARTBEAT_PID="$!"
}
stop_heartbeat() { [[ -n "${HEARTBEAT_PID}" ]] && kill "${HEARTBEAT_PID}" >/dev/null 2>&1 || true; }
on_error() {
  local code="$?" line_no="$1"
  log "ERROR" "line=${line_no} command=${BASH_COMMAND} exit=${code}"
  tail -n 120 "${LOG_PATH}" || true
  stop_heartbeat
  exit "${code}"
}
trap 'on_error $LINENO' ERR
trap 'stop_heartbeat' EXIT

write_state "bootstrap"
log "INFO" "run_id=${RUN_ID}"
log "INFO" "result_dir=${RESULT_DIR}"
log "INFO" "spec=${SPEC_PATH}"
log "INFO" "input=${INPUT_PATH}"
[[ -f "${SPEC_PATH}" ]]
[[ -f "${INPUT_PATH}" ]]

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

start_heartbeat

write_state "run_pipeline"
"${PYTHON_BIN}" -m workflow.pipelines.runtime.pipeline_json_runner \
  --spec "${SPEC_PATH}" \
  --input "${INPUT_PATH}" \
  --run-root "${RESULT_DIR}" \
  --output "${OUT_PATH}"

write_state "validate"
"${PYTHON_BIN}" - <<'PY' "${OUT_PATH}"
import json
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
if not out_path.is_file():
    raise RuntimeError(f"pipeline-result.json 누락: {out_path}")

result = json.loads(out_path.read_text(encoding="utf-8"))
outputs = result.get("outputs", {}) if isinstance(result, dict) else {}
mp3 = outputs.get("mp3", {}) if isinstance(outputs, dict) else {}
mp3_path = Path(str(mp3.get("path", "")).strip())
if not mp3_path.is_file():
    raise RuntimeError(f"최종 MP3 출력 누락: {mp3_path}")

print(f"mp3_path={mp3_path}")
print(f"pipeline={result.get('pipeline')}")
PY

write_state "complete"
log "INFO" "테스트 성공"
log "INFO" "result_json=${OUT_PATH}"
