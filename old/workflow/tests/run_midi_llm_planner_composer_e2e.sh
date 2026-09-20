#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STAGE="midi-llm-planner-composer-e2e"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/.result/workflow/tests/midi-llm-planner-composer-e2e/${RUN_ID}"
LOG_PATH="${RESULT_DIR}/run.log"
STATE_PATH="${RESULT_DIR}/state.txt"

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

PLANNER_INPUT="${ROOT_DIR}/workflow/nodes/midi_llm_planner/packages/prompt-plan.input.json"

write_state "bootstrap"
log "INFO" "run_id=${RUN_ID}"
log "INFO" "result_dir=${RESULT_DIR}"

start_heartbeat

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

write_state "run_planner"
"${PYTHON_BIN}" -m workflow.nodes.midi_llm_planner.runtime.cli \
  --input-json "${PLANNER_INPUT}" \
  --run-root "${RESULT_DIR}"

COMPOSER_INPUT_JSON="${RESULT_DIR}/outputs/planner/midi-llm-planner.composer-input.json"

write_state "run_composer"
"${PYTHON_BIN}" -m workflow.nodes.midi_llm_composer.runtime.cli \
  --input-json "${COMPOSER_INPUT_JSON}" \
  --run-root "${RESULT_DIR}"

RESULT_JSON="${RESULT_DIR}/result.json"

write_state "validate"
"${PYTHON_BIN}" - <<'PY' "${RESULT_DIR}" "${RESULT_JSON}"
import json
import sys
from pathlib import Path

run_root = Path(sys.argv[1])
result_json = Path(sys.argv[2])
if not result_json.is_file():
    raise RuntimeError(f"result.json 누락: {result_json}")

result = json.loads(result_json.read_text(encoding="utf-8"))
mid_path = Path(str(result.get("mid_path", "")).strip())
if not mid_path.is_file():
    raise RuntimeError(f"midi 출력 누락: {mid_path}")

planner_report = run_root / "outputs" / "planner" / "midi-llm-planner.report.json"
if not planner_report.is_file():
    raise RuntimeError(f"planner report 누락: {planner_report}")

print(f"mid_path={mid_path}")
print(f"planner_report={planner_report}")
PY

write_state "complete"
log "INFO" "테스트 성공"
log "INFO" "result_json=${RESULT_JSON}"
