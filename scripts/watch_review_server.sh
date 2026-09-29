#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_REPOSITORY_PATH="$(cd -- "${SCRIPT_DIRECTORY_PATH}/.." && pwd)"
FRONTEND_REPOSITORY_PATH="${FRONTEND_REPOSITORY_PATH:-$(cd -- "${WORKFLOW_REPOSITORY_PATH}/../slime-frontend" 2>/dev/null && pwd || true)}"
REVIEW_SERVER_PORT="${REVIEW_SERVER_PORT:-8770}"

log_review_watch_event() {
    printf '%s/asset-review-watch/%s\n' "$(date --iso-8601=seconds)" "$1"
}

trap 'log_review_watch_event "실패 line=${BASH_LINENO[0]} command=${BASH_COMMAND}"' ERR

if [[ -z "${FRONTEND_REPOSITORY_PATH}" || ! -d "${FRONTEND_REPOSITORY_PATH}" ]]; then
    log_review_watch_event "프론트엔드 저장소를 찾을 수 없습니다 경로=${FRONTEND_REPOSITORY_PATH:-미지정}"
    exit 1
fi

log_review_watch_event "시작 workflow=${WORKFLOW_REPOSITORY_PATH} frontend=${FRONTEND_REPOSITORY_PATH} port=${REVIEW_SERVER_PORT}"
exec python3 "${WORKFLOW_REPOSITORY_PATH}/tools/review/serve.py" \
    --frontend-repo "${FRONTEND_REPOSITORY_PATH}" \
    --port "${REVIEW_SERVER_PORT}" \
    --watch \
    "$@"
