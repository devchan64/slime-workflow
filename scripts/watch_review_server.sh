#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_REPOSITORY_PATH="$(cd -- "${SCRIPT_DIRECTORY_PATH}/.." && pwd)"
FRONTEND_REPOSITORY_PATH="${FRONTEND_REPOSITORY_PATH:-$(cd -- "${WORKFLOW_REPOSITORY_PATH}/../slime-frontend" 2>/dev/null && pwd || true)}"
REVIEW_SERVER_PORT="${REVIEW_SERVER_PORT:-8770}"
VIRTUAL_ENVIRONMENT_PATH="${VIRTUAL_ENVIRONMENT_PATH:-${WORKFLOW_REPOSITORY_PATH}/.venv}"
MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH="${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH:-${WORKFLOW_REPOSITORY_PATH}/.venv-management}"

log_review_watch_event() {
    printf '%s/asset-review-watch/%s\n' "$(date --iso-8601=seconds)" "$1"
}

trap 'log_review_watch_event "실패 line=${LINENO} command=${BASH_COMMAND}"' ERR

prepare_environment_pip() {
    local environment_python_path="$1/bin/python"
    if ! "${environment_python_path}" -c 'import importlib.util, sys; sys.exit(importlib.util.find_spec("pip") is None)'; then
        log_review_watch_event "pip 준비 python=${environment_python_path}"
        "${environment_python_path}" -m ensurepip --upgrade
    fi
    "${environment_python_path}" -m pip --version
}

if [[ -z "${FRONTEND_REPOSITORY_PATH}" || ! -d "${FRONTEND_REPOSITORY_PATH}" ]]; then
    log_review_watch_event "프론트엔드 저장소를 찾을 수 없습니다 경로=${FRONTEND_REPOSITORY_PATH:-미지정}"
    exit 1
fi

if [[ ! -x "${VIRTUAL_ENVIRONMENT_PATH}/bin/python" ]]; then
    log_review_watch_event "가상환경 생성 path=${VIRTUAL_ENVIRONMENT_PATH}"
    python3 -m venv "${VIRTUAL_ENVIRONMENT_PATH}"
fi

if [[ ! -x "${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH}/bin/python" ]]; then
    log_review_watch_event "관리 UI 가상환경 생성 path=${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH}"
    python3 -m venv "${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH}"
fi

prepare_environment_pip "${VIRTUAL_ENVIRONMENT_PATH}"
prepare_environment_pip "${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH}"

log_review_watch_event "의존성 설치 runtime=${VIRTUAL_ENVIRONMENT_PATH} management=${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH} requirements=${WORKFLOW_REPOSITORY_PATH}/requirements.txt"
"${VIRTUAL_ENVIRONMENT_PATH}/bin/python" -m pip install --disable-pip-version-check --requirement "${WORKFLOW_REPOSITORY_PATH}/requirements.txt"
"${MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH}/bin/python" -m pip install --disable-pip-version-check --requirement "${WORKFLOW_REPOSITORY_PATH}/requirements.txt"
log_review_watch_event "시작 workflow=${WORKFLOW_REPOSITORY_PATH} frontend=${FRONTEND_REPOSITORY_PATH} port=${REVIEW_SERVER_PORT}"
exec "${VIRTUAL_ENVIRONMENT_PATH}/bin/python" "${WORKFLOW_REPOSITORY_PATH}/tools/review/serve.py" \
    --frontend-repo "${FRONTEND_REPOSITORY_PATH}" \
    --port "${REVIEW_SERVER_PORT}" \
    --watch \
    "$@"
