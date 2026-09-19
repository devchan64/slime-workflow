#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STAGE="musicgen-small-max-duration-test"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/.result/workflow/tests/musicgen-small-max-duration/${RUN_ID}"
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

PROMPT_JSON="${ROOT_DIR}/workflow/nodes/musicgen_small/packages/prompt-max-duration.json"

write_state "bootstrap"
log "INFO" "run_id=${RUN_ID}"
log "INFO" "result_dir=${RESULT_DIR}"
log "INFO" "prompt_json=${PROMPT_JSON}"
[[ -f "${PROMPT_JSON}" ]]

start_heartbeat

write_state "run_node"
log "INFO" "musicgen-small 노드 실행"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" -m workflow.nodes.musicgen_small.runtime.cli \
  --input-json "${PROMPT_JSON}" \
  --run-root "${RESULT_DIR}"

RESULT_JSON="${RESULT_DIR}/result.json"

write_state "validate"
log "INFO" "결과 검증"

"${PYTHON_BIN}" - <<'PY' "${RESULT_JSON}" "${PROMPT_JSON}"
import json
import sys
import wave
from pathlib import Path

result_path = Path(sys.argv[1])
prompt_path = Path(sys.argv[2])
if not result_path.is_file():
    raise RuntimeError(f"result.json 누락: {result_path}")

result = json.loads(result_path.read_text(encoding="utf-8"))
prompt = json.loads(prompt_path.read_text(encoding="utf-8"))

wav_path = Path(str(result.get("wav_path", "")).strip())
report_path = Path(str(result.get("report_path", "")).strip())
if not wav_path.is_file():
    raise RuntimeError(f"wav 출력 누락: {wav_path}")
if not report_path.is_file():
    raise RuntimeError(f"report 출력 누락: {report_path}")

with wave.open(str(wav_path), "rb") as wf:
    frames = wf.getnframes()
    rate = wf.getframerate()
    duration = frames / float(rate)

report = json.loads(report_path.read_text(encoding="utf-8"))
requested = int(prompt.get("duration_seconds", 0))
if requested <= 0:
    raise RuntimeError("테스트 프롬프트 duration_seconds가 비정상입니다")

if duration < max(5.0, requested * 0.6):
    raise RuntimeError(f"생성 길이가 너무 짧습니다: requested={requested}s, generated={duration:.2f}s")

print(f"requested={requested}")
print(f"generated_duration={duration:.2f}")
print(f"elapsed={float(report.get('elapsed_seconds', 0.0)):.2f}")
print(f"rtf={float(report.get('realtime_factor', 0.0)):.4f}")
PY

write_state "complete"
log "INFO" "테스트 성공"
log "INFO" "result_json=${RESULT_JSON}"
