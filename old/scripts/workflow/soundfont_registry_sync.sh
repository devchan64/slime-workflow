#!/usr/bin/env bash
set -Eeuo pipefail

AREA="ai-workflow"
STEP="soundfont-registry-sync"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REGISTRY_PATH="${ROOT_DIR}/workflow/nodes/audio_render/packages/soundfont-registry.json"
SOUNDFONTS_ROOT="${ROOT_DIR}/.soundfonts"
STATE_FILE_REL="registry-state.json"
DRY_RUN="false"
FORCE="false"
ONLY_ID=""
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

usage() {
  cat <<USAGE
사용법:
  $(basename "$0") [--registry PATH] [--soundfonts-root PATH] [--only-id ID] [--force] [--dry-run]
기본 루트: .soundfonts
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY_PATH="$2"; shift 2 ;;
    --soundfonts-root) SOUNDFONTS_ROOT="$2"; shift 2 ;;
    --only-id) ONLY_ID="$2"; shift 2 ;;
    --force) FORCE="true"; shift ;;
    --dry-run) DRY_RUN="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) log "ERROR" "알 수 없는 인자: $1"; usage; exit 1 ;;
  esac
done

[[ -f "${REGISTRY_PATH}" ]] || { log "ERROR" "레지스트리 파일이 없다: ${REGISTRY_PATH}"; exit 1; }
command -v curl >/dev/null 2>&1 || { log "ERROR" "curl 명령이 필요하다"; exit 1; }
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { log "ERROR" "python3 명령이 필요하다"; exit 1; }

mkdir -p "${SOUNDFONTS_ROOT}"
STATE_PATH="${SOUNDFONTS_ROOT}/${STATE_FILE_REL}"
STATE_TMP="${STATE_PATH}.tmp"
: > "${STATE_TMP}"

export REGISTRY_PATH SOUNDFONTS_ROOT ONLY_ID
PARSED_LINES="$("${PYTHON_BIN}" <<'PY'
import json
import os
import sys
from pathlib import Path

registry_path = Path(os.environ["REGISTRY_PATH"])
soundfonts_root = Path(os.environ["SOUNDFONTS_ROOT"])
only_id = os.environ.get("ONLY_ID", "").strip()

try:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR\tjson-parse\t{exc}")
    sys.exit(1)

items = registry.get("soundfonts", [])
if not isinstance(items, list) or not items:
    print("ERROR\tregistry\tsoundfonts 항목이 비어 있음")
    sys.exit(1)

print(f"__META__\t{soundfonts_root}")
matched = 0
for item in items:
    soundfont_id = str(item.get("id", "")).strip()
    if only_id and soundfont_id != only_id:
        continue
    matched += 1
    name = str(item.get("name", "")).strip()
    fmt = str(item.get("format", "")).strip()
    license_name = str(item.get("license", "")).strip()
    engine = str(item.get("engine", "")).strip()
    dist = item.get("distribution", {})
    kind = str(dist.get("kind", "")).strip()
    url = str(dist.get("url", "")).strip()
    target_relpath = str(item.get("install", {}).get("target_relpath", "")).strip()
    roles = "|".join(str(x).strip() for x in item.get("roles", []) if str(x).strip()) or "-"
    if not all([soundfont_id, name, fmt, license_name, engine, kind, url, target_relpath]):
        print(f"ERROR\tentry\t필수값 누락: id={soundfont_id or 'unknown'}")
        sys.exit(1)
    print("\t".join([
        soundfont_id,
        name,
        fmt,
        license_name,
        engine,
        roles,
        kind,
        url,
        str(soundfonts_root / target_relpath),
    ]))

if only_id and matched == 0:
    print(f"ERROR\tentry\t해당 id를 찾지 못함: {only_id}")
    sys.exit(1)
PY
)"

downloaded=0
skipped=0
failed=0
planned=0

log "INFO" "사운드폰트 동기화 시작: registry=${REGISTRY_PATH}, root=${SOUNDFONTS_ROOT}, dry_run=${DRY_RUN}, force=${FORCE}, only_id=${ONLY_ID:-all}"

while IFS=$'\t' read -r soundfont_id name fmt license_name engine roles kind url target_path; do
  [[ -z "${soundfont_id}" || "${soundfont_id}" == "__META__" ]] && continue
  planned=$((planned + 1))
  log "INFO" "항목 확인: id=${soundfont_id}, format=${fmt}, engine=${engine}, roles=${roles}, target=${target_path}"

  if [[ -f "${target_path}" && "${FORCE}" != "true" ]]; then
    log "INFO" "기존 자산 유지: id=${soundfont_id}"
    skipped=$((skipped + 1))
    printf '{"id":"%s","status":"%s","path":"%s","format":"%s","license":"%s","engine":"%s"}\n' \
      "${soundfont_id}" "skipped" "${target_path}" "${fmt}" "${license_name}" "${engine}" >> "${STATE_TMP}"
    continue
  fi

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "INFO" "DRY-RUN 다운로드 예정: id=${soundfont_id}, url=${url}"
    printf '{"id":"%s","status":"%s","path":"%s","format":"%s","license":"%s","engine":"%s"}\n' \
      "${soundfont_id}" "planned" "${target_path}" "${fmt}" "${license_name}" "${engine}" >> "${STATE_TMP}"
    continue
  fi

  if [[ "${kind}" != "http_file" ]]; then
    log "ERROR" "현재 workflow 사운드폰트 동기화는 http_file만 지원한다: id=${soundfont_id}, kind=${kind}"
    failed=$((failed + 1))
    continue
  fi

  mkdir -p "$(dirname "${target_path}")"
  tmp_path="${target_path}.download"
  rm -f "${tmp_path}" "${target_path}"
  if ! curl -fL --retry 3 --connect-timeout 20 --max-time 7200 -o "${tmp_path}" "${url}"; then
    log "ERROR" "다운로드 실패: id=${soundfont_id}, url=${url}"
    rm -f "${tmp_path}"
    failed=$((failed + 1))
    printf '{"id":"%s","status":"%s","path":"%s","format":"%s","license":"%s","engine":"%s"}\n' \
      "${soundfont_id}" "failed" "${target_path}" "${fmt}" "${license_name}" "${engine}" >> "${STATE_TMP}"
    continue
  fi

  mv "${tmp_path}" "${target_path}"
  downloaded=$((downloaded + 1))
  log "INFO" "다운로드 완료: id=${soundfont_id}"
  printf '{"id":"%s","status":"%s","path":"%s","format":"%s","license":"%s","engine":"%s"}\n' \
    "${soundfont_id}" "downloaded" "${target_path}" "${fmt}" "${license_name}" "${engine}" >> "${STATE_TMP}"
done <<< "${PARSED_LINES}"

export STATE_TMP STATE_PATH
"${PYTHON_BIN}" <<'PY'
import os
from pathlib import Path

state_tmp = Path(os.environ["STATE_TMP"])
state_path = Path(os.environ["STATE_PATH"])
rows = [line.strip() for line in state_tmp.read_text(encoding="utf-8").splitlines() if line.strip()]
state_path.write_text('{\n  "items": [\n    ' + ',\n    '.join(rows) + '\n  ]\n}\n', encoding="utf-8")
state_tmp.unlink(missing_ok=True)
PY

log "INFO" "요약: planned=${planned}, downloaded=${downloaded}, skipped=${skipped}, failed=${failed}, state=${STATE_PATH}"
if [[ "${failed}" -gt 0 ]]; then
  exit 1
fi
