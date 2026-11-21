#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -I -S -B "${SCRIPT_DIRECTORY_PATH}/../workflow/common/management_launcher.py" "$@"
