#!/usr/bin/env bash
# 기존 watch 명령은 GUI 전용 실행기의 호환 진입점이다.
set -Eeuo pipefail
SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIRECTORY_PATH}/run_management_gui.sh" --watch "$@"
