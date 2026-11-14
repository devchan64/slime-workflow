"""고정 리비전의 기존 Hugging Face 부분 파일을 안전하게 확인한다."""
import hashlib
import json
import os
import re
from pathlib import Path

from tools.review.common.model_download_records import track_model_download
from tools.review.common.model_http_download import download_verified_http, import_verified_http_prefix


class ModelRecoveryError(ValueError):
    """부분 파일을 안전하게 복구하지 못해 자동 대체를 거절한다."""



def read_completed_verification(current_checkpoint_target, current_candidate_path, current_expected_hash, current_file_size):
    """이전 확정 단계의 하드링크와 해시를 확인한다. 불명확한 파일은 변경하지 않는다."""
    current_checkpoint_path = current_checkpoint_target.with_name(current_checkpoint_target.name + '.checkpoint.json')
    current_verified_path = current_checkpoint_target.with_name(current_checkpoint_target.name + '.checkpoint.bin')
    if not current_checkpoint_path.exists():
        return False
    if any(current_path_value.is_symlink() for current_path_value in (current_checkpoint_path, current_verified_path, current_candidate_path)):
        raise ValueError('검증 확정 파일에는 심볼릭 링크를 사용할 수 없습니다.')
    if not current_candidate_path.exists():
        return False
    if current_verified_path.exists() and not os.path.samefile(current_verified_path, current_candidate_path):
        return False
    try:
        current_checkpoint_record = json.loads(current_checkpoint_path.read_text(encoding='utf-8'))
        current_source_record = current_checkpoint_record['source']
        current_verified_bytes = current_checkpoint_record['bytes']
        if (current_source_record['remote'] != current_expected_hash or current_source_record['total'] != current_file_size
                or isinstance(current_verified_bytes, bool) or not isinstance(current_verified_bytes, int)
                or current_verified_bytes != current_source_record['size']
                or not 0 < current_verified_bytes <= current_candidate_path.stat().st_size <= current_file_size):
            raise ValueError('확정된 검증 지점의 식별 정보가 일치하지 않습니다.')
        current_prefix_digest = hashlib.sha256()
        with current_candidate_path.open('rb') as current_file_stream:
            current_remaining_bytes = current_verified_bytes
            while current_remaining_bytes:
                current_file_chunk = current_file_stream.read(min(8 * 1024 * 1024, current_remaining_bytes))
                if not current_file_chunk:
                    raise ValueError('확정된 검증 지점의 파일 길이가 부족합니다.')
                current_prefix_digest.update(current_file_chunk)
                current_remaining_bytes -= len(current_file_chunk)
        current_verified_digest = current_prefix_digest.hexdigest()
        if current_verified_digest != current_checkpoint_record['sha256']:
            raise ValueError('확정된 검증 지점의 해시가 일치하지 않습니다.')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as current_checkpoint_error:
        raise ValueError('확정된 검증 지점이 손상되었습니다.') from current_checkpoint_error
    return True


def remove_completed_verification(current_checkpoint_target):
    current_checkpoint_target.with_name(current_checkpoint_target.name + '.checkpoint.bin').unlink(missing_ok=True)
    current_checkpoint_target.with_name(current_checkpoint_target.name + '.checkpoint.json').unlink(missing_ok=True)


def recover_huggingface_partial(current_repo_name, current_revision_value, current_local_root, current_file_record, current_endpoint_value=None, resume_report_callback=None):
    """같은 파일·해시의 조각을 서버와 대조해 완성한다. 원본 조각은 보존한다."""
    from huggingface_hub import get_hf_file_metadata, hf_hub_url
    from huggingface_hub._local_folder import get_local_download_paths
    from huggingface_hub.utils import WeakFileLock
    current_file_name = current_file_record.filename
    current_file_size = current_file_record.file_size
    current_file_url = hf_hub_url(current_repo_name, current_file_name, revision=current_revision_value, endpoint=current_endpoint_value)
    current_file_metadata = get_hf_file_metadata(current_file_url, token=False, endpoint=current_endpoint_value)
    current_file_etag = current_file_metadata.etag or ''
    if not re.fullmatch(r'[0-9a-f]{64}', current_file_etag) or current_file_metadata.size != current_file_size:
        return False
    current_local_paths = get_local_download_paths(Path(current_local_root), current_file_name)
    current_expected_path = Path(current_file_record.local_path)
    if current_local_paths.file_path.resolve() != current_expected_path.resolve():
        raise ValueError('Hugging Face 로컬 대상 경로가 일치하지 않습니다.')
    current_legacy_path = current_local_paths.incomplete_path(current_file_etag)
    current_target_path = current_local_paths.file_path
    current_partial_path = current_target_path.with_suffix(current_target_path.suffix + '.partial')
    def report_partial_resume():
        if resume_report_callback is not None:
            resume_report_callback(current_partial_path.stat().st_size)
    try:
        with WeakFileLock(current_local_paths.lock_path, timeout=0.25):
            if current_target_path.exists():
                return False
            if current_partial_path.exists():
                current_previous_target = current_partial_path.with_name(current_partial_path.name + '.verified')
                if read_completed_verification(current_partial_path, current_partial_path, current_file_etag, current_file_size):
                    report_partial_resume()
                    download_verified_http(current_file_url, current_target_path, current_file_etag, current_repo_name + '/' + current_file_name)
                    remove_completed_verification(current_partial_path)
                    return True
                if read_completed_verification(current_previous_target, current_partial_path, current_file_etag, current_file_size):
                    report_partial_resume()
                    download_verified_http(current_file_url, current_target_path, current_file_etag, current_repo_name + '/' + current_file_name)
                    remove_completed_verification(current_previous_target)
                    return True
                if current_partial_path.is_symlink() or not current_partial_path.is_file():
                    raise ValueError('이어받기 부분 파일은 일반 파일이어야 합니다.')
                current_partial_size = current_partial_path.stat().st_size
                if current_partial_size == current_file_size:
                    report_partial_resume()
                    download_verified_http(current_file_url, current_target_path, current_file_etag, current_repo_name + '/' + current_file_name)
                    return True
                if not 0 < current_partial_size < current_file_size:
                    raise ValueError('이어받기 부분 파일의 크기가 올바르지 않습니다.')
                current_source_path = current_partial_path
                current_verified_path = current_partial_path.with_name(current_partial_path.name + '.verified')
            else:
                current_candidate_paths = [current_legacy_path, *current_legacy_path.parent.glob(current_legacy_path.stem + '.*.incomplete')]
                current_candidate_paths = [current_path_value for current_path_value in current_candidate_paths if current_path_value.is_file() and not current_path_value.is_symlink() and 0 < current_path_value.stat().st_size < current_file_size]
                if not current_candidate_paths:
                    return False
                current_source_path = max(current_candidate_paths, key=lambda current_path_value: current_path_value.stat().st_size)
                current_verified_path = current_partial_path
            with track_model_download(current_repo_name + '/' + current_file_name) as current_download_record:
                import_verified_http_prefix(current_file_url, current_source_path, current_verified_path, current_file_size, current_download_record, expected_identity_value=current_file_etag, retain_checkpoint_value=True)
            if current_verified_path != current_partial_path:
                os.replace(current_verified_path, current_partial_path)
                current_directory_fd = os.open(current_partial_path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(current_directory_fd)
                finally:
                    os.close(current_directory_fd)
            report_partial_resume()
            download_verified_http(current_file_url, current_target_path, current_file_etag, current_repo_name + '/' + current_file_name)
            remove_completed_verification(current_verified_path)
        return True
    except Exception as current_recovery_error:
        current_recovery_reason = str(current_recovery_error) if isinstance(current_recovery_error, ValueError) else type(current_recovery_error).__name__
        raise ModelRecoveryError('기존 모델 부분 파일 또는 검증 지점을 안전하게 복구하지 못했습니다: ' + current_recovery_reason) from current_recovery_error
