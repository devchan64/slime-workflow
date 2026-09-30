#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIRECTORY_PATH}/../tools/review/common/management_launcher.py" gateway "$@"
