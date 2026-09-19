#!/usr/bin/env bash
set -Eeuo pipefail

AREA="workflow"
STAGE="midi-trim-bars-smoke"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/.result/workflow/tests/midi-trim-bars-smoke/${RUN_ID}"
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

write_state "bootstrap"
log "INFO" "run_id=${RUN_ID}"
log "INFO" "result_dir=${RESULT_DIR}"

start_heartbeat

write_state "prepare_fixture"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

FIXTURE_MIDI="${RESULT_DIR}/fixture.mid"
"${PYTHON_BIN}" - <<'PY' "${FIXTURE_MIDI}"
import sys
from pathlib import Path
import mido

path = Path(sys.argv[1])
mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
bar_ticks = 4 * mid.ticks_per_beat
for bar in range(48):
    note = 60 + (bar % 12)
    track.append(mido.Message("note_on", note=note, velocity=80, time=0, channel=0))
    track.append(mido.Message("note_off", note=note, velocity=0, time=bar_ticks, channel=0))
track.append(mido.MetaMessage("end_of_track", time=0))
mid.save(str(path))
PY

write_state "run_node"
"${PYTHON_BIN}" -m workflow.nodes.midi_trim_bars.runtime.cli \
  --midi-path "${FIXTURE_MIDI}" \
  --bars 32 \
  --run-root "${RESULT_DIR}"

RESULT_JSON="${RESULT_DIR}/result.json"

write_state "validate"
"${PYTHON_BIN}" - <<'PY' "${RESULT_JSON}"
import json
import sys
from pathlib import Path
import mido

result_path = Path(sys.argv[1])
if not result_path.is_file():
    raise RuntimeError(f"result.json 누락: {result_path}")

result = json.loads(result_path.read_text(encoding="utf-8"))
out_midi = Path(str(result.get("midi_path", "")).strip())
report = Path(str(result.get("report_path", "")).strip())
if not out_midi.is_file():
    raise RuntimeError(f"trimmed midi 누락: {out_midi}")
if not report.is_file():
    raise RuntimeError(f"report 누락: {report}")

mid = mido.MidiFile(str(out_midi))
max_tick = 0
for track in mid.tracks:
    t = 0
    for msg in track:
        t += msg.time
    max_tick = max(max_tick, t)
limit = 32 * 4 * mid.ticks_per_beat
if max_tick > limit:
    raise RuntimeError(f"트림 실패: max_tick={max_tick} > limit={limit}")

print(f"max_tick={max_tick}")
print(f"limit_tick={limit}")
PY

write_state "complete"
log "INFO" "테스트 성공"
log "INFO" "result_json=${RESULT_JSON}"
