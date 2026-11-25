"""Hermes와 작가 AI가 공유하는 고정 Qwen 모델을 준비한다."""
import hashlib
import json
from pathlib import Path

from workflow.common.generation_records import write_record_atomically
from workflow.common.model_http_download import download_verified_http
from workflow.common.model_storage_layout import resolve_hermes_model_directory

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
HERMES_MODEL_DIRECTORY = resolve_hermes_model_directory(WORKFLOW_ROOT_DIRECTORY / '.model')
_INITIAL_MODEL_DIRECTORY = HERMES_MODEL_DIRECTORY
HERMES_MODEL_FILENAME = 'Qwen3.8-27B-IQ4_XS.gguf'
HERMES_MODEL_REVISION = '87410e7b9a5c21e6ca70c0c9cc5237de909fe621'
HERMES_MODEL_SHA256 = '4b927360fa7c4aa41a734302f0795ca45df0e8b8a258bc76cc5fbf9d98a484db'
HERMES_MODEL_DOWNLOAD_URL = f'https://huggingface.co/bartowski/Qwen3.8-27B-GGUF/resolve/{HERMES_MODEL_REVISION}/{HERMES_MODEL_FILENAME}'


def current_hermes_model_directory():
    """Resolve again so long-lived management processes observe a completed move."""
    if HERMES_MODEL_DIRECTORY != _INITIAL_MODEL_DIRECTORY:
        return HERMES_MODEL_DIRECTORY
    return resolve_hermes_model_directory(WORKFLOW_ROOT_DIRECTORY / '.model')


def inspect_hermes_model_files():
    """마지막 해시 검증 이후 파일 속성이 유지됐는지 확인한다."""
    current_directory = current_hermes_model_directory()
    current_model_path = current_directory / HERMES_MODEL_FILENAME
    current_marker_path = current_directory / 'ready.sha256'
    try:
        if current_model_path.is_symlink() or current_marker_path.is_symlink():
            return False
        current_model_stat = current_model_path.stat()
        current_marker_record = json.loads(current_marker_path.read_text(encoding='utf-8'))
        return current_marker_record == {'sha256': HERMES_MODEL_SHA256, 'size': current_model_stat.st_size, 'mtime_ns': current_model_stat.st_mtime_ns}
    except (OSError, ValueError):
        return False


def verify_hermes_model_integrity():
    """실행 전 전체 파일을 읽어 고정 해시와 비교한다."""
    current_model_path = current_hermes_model_directory() / HERMES_MODEL_FILENAME
    if current_model_path.is_symlink() or not current_model_path.is_file():
        raise ValueError('Hermes 모델 파일이 없거나 심볼릭 링크입니다.')
    with current_model_path.open('rb') as current_model_stream:
        if hashlib.file_digest(current_model_stream, 'sha256').hexdigest() != HERMES_MODEL_SHA256:
            raise ValueError('Hermes 모델 SHA-256 불일치')


def prepare_hermes_model_files():
    current_directory = current_hermes_model_directory()
    current_model_path = current_directory / HERMES_MODEL_FILENAME
    download_verified_http(HERMES_MODEL_DOWNLOAD_URL, current_model_path, HERMES_MODEL_SHA256, 'hermes-agent/' + HERMES_MODEL_FILENAME)
    verify_hermes_model_integrity()
    current_model_stat = current_model_path.stat()
    write_record_atomically(current_directory / 'ready.sha256', {'sha256': HERMES_MODEL_SHA256, 'size': current_model_stat.st_size, 'mtime_ns': current_model_stat.st_mtime_ns})
