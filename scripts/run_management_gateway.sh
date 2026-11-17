#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIRECTORY_PATH}/workflow.sh" gateway "$@"
