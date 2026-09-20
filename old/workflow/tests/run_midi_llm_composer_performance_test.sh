#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STAGE="midi-llm-composer-performance-test"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/.result/workflow/tests/midi-llm-composer-performance/${RUN_ID}"
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

PROMPT_JSON="${ROOT_DIR}/workflow/nodes/midi_llm_composer/packages/test-input.prompt-intent.json"

write_state "bootstrap"
log "INFO" "run_id=${RUN_ID}"
log "INFO" "result_dir=${RESULT_DIR}"
log "INFO" "prompt_json=${PROMPT_JSON}"
[[ -f "${PROMPT_JSON}" ]]

start_heartbeat

write_state "run_node"
log "INFO" "MIDI-LLM 노드 실행"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" -m workflow.nodes.midi_llm_composer.runtime.cli \
  --input-json "${PROMPT_JSON}" \
  --run-root "${RESULT_DIR}"

RESULT_JSON="${RESULT_DIR}/result.json"

write_state "validate"
log "INFO" "결과 검증"

"${PYTHON_BIN}" - <<'PY' "${RESULT_JSON}"
import json
import sys
from pathlib import Path

result_path = Path(sys.argv[1])
if not result_path.is_file():
    raise RuntimeError(f"result.json 누락: {result_path}")

result = json.loads(result_path.read_text(encoding="utf-8"))
mid_path = Path(str(result.get("mid_path", "")).strip())
raw_path = Path(str(result.get("raw_output_path", "")).strip())
token_path = Path(str(result.get("token_output_path", "")).strip())
report_path = Path(str(result.get("report_path", "")).strip())

for path in (mid_path, raw_path, token_path, report_path):
    if not path.is_file():
        raise RuntimeError(f"출력 누락: {path}")

tokens = json.loads(token_path.read_text(encoding="utf-8")).get("tokens", [])
if not tokens:
    raise RuntimeError("MIDI token 출력이 비어 있습니다")

report = json.loads(report_path.read_text(encoding="utf-8"))
if int(report.get("generated_tokens", 0)) <= 0:
    raise RuntimeError("generated_tokens가 0입니다")
if float(report.get("tokens_per_second", 0.0)) <= 0.0:
    raise RuntimeError("tokens_per_second가 0입니다")

print(f"generated_tokens={int(report['generated_tokens'])}")
print(f"midi_token_count={int(report['midi_token_count'])}")
print(f"elapsed={float(report['elapsed_seconds']):.2f}")
print(f"tokens_per_second={float(report['tokens_per_second']):.3f}")
PY

write_state "complete"
log "INFO" "테스트 성공"
log "INFO" "result_json=${RESULT_JSON}"
