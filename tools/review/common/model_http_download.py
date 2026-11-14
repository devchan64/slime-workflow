"""고정 SHA-256 다운로드의 중단 복구와 공용 상태 기록."""
import hashlib
import os
import re
import urllib.request
import urllib.error

from tools.review.common.model_download_records import track_model_download


def download_verified_http(current_download_url, current_target_path, expected_sha256_value, model_identifier_value, current_partial_path=None, expected_total_bytes=None):
    current_target_path.parent.mkdir(parents=True, exist_ok=True)
    current_partial_path = current_partial_path or current_target_path.with_suffix(current_target_path.suffix + '.partial')
    if current_target_path.is_symlink() or current_partial_path.is_symlink():
        raise ValueError('모델 파일에 심볼릭 링크를 사용할 수 없습니다.')
    with track_model_download(model_identifier_value) as current_record_value:
        if current_target_path.is_file():
            with current_target_path.open('rb') as current_file_stream:
                if hashlib.file_digest(current_file_stream, 'sha256').hexdigest() != expected_sha256_value:
                    raise ValueError(f'기존 파일 해시 불일치: {current_target_path}')
            current_record_value.update(stage='검증 완료', bytes=current_target_path.stat().st_size, total_bytes=current_target_path.stat().st_size)
            return
        current_resume_offset = current_partial_path.stat().st_size if current_partial_path.exists() else 0
        if expected_total_bytes is not None and current_resume_offset > expected_total_bytes:
            raise ValueError('부분 다운로드 크기가 예상 크기를 초과합니다.')
        if expected_total_bytes is not None and current_partial_path.exists() and current_resume_offset == expected_total_bytes:
            with current_partial_path.open('rb') as current_file_stream:
                current_partial_hash = hashlib.file_digest(current_file_stream, 'sha256').hexdigest()
            if current_partial_hash != expected_sha256_value:
                raise ValueError('기존 부분 파일 해시가 일치하지 않습니다.')
            current_record_value.update(stage='SHA-256 검증 완료', bytes=current_resume_offset, total_bytes=expected_total_bytes, resumed_bytes=current_resume_offset)
            os.replace(current_partial_path, current_target_path)
            return
        current_record_value.update(stage='서버 연결 중', bytes=current_resume_offset, total_bytes=expected_total_bytes, resumed_bytes=current_resume_offset)
        current_request_headers = {'Range': f'bytes={current_resume_offset}-'} if current_resume_offset else {}
        current_http_request = urllib.request.Request(current_download_url, headers=current_request_headers)
        try:
            current_http_response = urllib.request.urlopen(current_http_request, timeout=120)
        except urllib.error.HTTPError as current_http_error:
            if current_http_error.code != 416 or not current_resume_offset:
                raise
            with current_partial_path.open('rb') as current_file_stream:
                current_partial_hash = hashlib.file_digest(current_file_stream, 'sha256').hexdigest()
            if current_partial_hash != expected_sha256_value:
                raise ValueError('이어받기 파일이 완전하지 않거나 해시가 일치하지 않습니다.') from current_http_error
            current_download_record_bytes = current_partial_path.stat().st_size
            current_record_value.update(stage='SHA-256 검증 완료', bytes=current_download_record_bytes, total_bytes=current_download_record_bytes, resumed_bytes=current_download_record_bytes)
            os.replace(current_partial_path, current_target_path)
            return
        with current_http_response:
            current_response_status = current_http_response.status
            if current_resume_offset and current_response_status == 206:
                current_content_range = current_http_response.headers.get('Content-Range', '')
                current_range_match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', current_content_range)
                if not current_range_match or int(current_range_match.group(1)) != current_resume_offset:
                    raise ValueError('이어받기 응답 범위 오류')
                current_total_bytes = int(current_range_match.group(3))
                current_file_mode = 'ab'
            elif current_response_status == 200:
                if current_resume_offset:
                    raise ValueError('서버가 이어받기 범위를 지원하지 않아 기존 부분 파일을 보존했습니다.')
                current_resume_offset = 0
                current_content_length = current_http_response.headers.get('Content-Length')
                current_total_bytes = int(current_content_length) if current_content_length is not None else None
                current_file_mode = 'wb'
            else:
                raise ValueError(f'다운로드 응답 오류: {current_response_status}')
            if expected_total_bytes is not None and current_total_bytes is not None and current_total_bytes != expected_total_bytes:
                raise ValueError('서버 모델 크기가 예상 크기와 일치하지 않습니다.')
            current_received_bytes = current_resume_offset
            current_record_value.update(stage='다운로드', bytes=current_received_bytes, total_bytes=current_total_bytes, resumed_bytes=current_resume_offset)
            with current_partial_path.open(current_file_mode) as current_file_stream:
                while current_download_chunk := current_http_response.read(1024 * 1024):
                    current_file_stream.write(current_download_chunk)
                    current_received_bytes += len(current_download_chunk)
                    current_record_value.update(bytes=current_received_bytes)
        if ((current_total_bytes is not None and current_received_bytes != current_total_bytes)
                or (expected_total_bytes is not None and current_received_bytes != expected_total_bytes)):
            raise ValueError('다운로드 크기 불일치')
        current_record_value.update(stage='SHA-256 검증')
        with current_partial_path.open('rb') as current_file_stream:
            if hashlib.file_digest(current_file_stream, 'sha256').hexdigest() != expected_sha256_value:
                raise ValueError(f'다운로드 해시 불일치: {current_partial_path}')
        os.replace(current_partial_path, current_target_path)


def import_verified_http_prefix(current_download_url, current_source_path, current_partial_path, expected_total_bytes, current_record_value, expected_identity_value=None, retain_checkpoint_value=False):
    """서버 범위와 대조한 지점을 원자적으로 보존하고 중단 후 재검증해 이어간다."""
    import json
    current_source_path = current_source_path.resolve(strict=True)
    current_source_stat = current_source_path.stat()
    current_prefix_bytes = current_source_stat.st_size
    if not current_source_path.is_file() or current_prefix_bytes <= 0 or current_prefix_bytes >= expected_total_bytes:
        raise ValueError('기존 부분 파일의 크기가 올바르지 않습니다.')
    current_partial_path.parent.mkdir(parents=True, exist_ok=True)
    current_checkpoint_path = current_partial_path.with_name(current_partial_path.name + '.checkpoint.json')
    current_verified_path = current_partial_path.with_name(current_partial_path.name + '.checkpoint.bin')
    current_completed_link = current_partial_path.exists()
    if current_partial_path.is_symlink():
        raise ValueError('이어받기 대상에 심볼릭 링크를 사용할 수 없습니다.')
    if current_completed_link and (not current_checkpoint_path.is_file() or (current_verified_path.exists() and not os.path.samefile(current_partial_path, current_verified_path))):
        raise FileExistsError('검증 근거가 없는 이어받기 대상 파일이 이미 있습니다.')
    if current_completed_link and not current_verified_path.exists():
        current_verified_path = current_partial_path
    current_source_identity = {'dev': current_source_stat.st_dev, 'ino': current_source_stat.st_ino, 'size': current_prefix_bytes, 'mtime_ns': current_source_stat.st_mtime_ns, 'total': expected_total_bytes, 'remote': expected_identity_value or hashlib.sha256(current_download_url.encode()).hexdigest()}
    current_verified_bytes = 0
    current_prefix_digest = hashlib.sha256()
    if current_verified_path.exists() and not current_checkpoint_path.exists() and not current_completed_link and current_verified_path.is_file() and not current_verified_path.is_symlink() and current_verified_path.stat().st_size == 0:
        # 최초 빈 파일을 만든 직후 종료된 경우에도 같은 지점에서 다시 시작한다.
        pass
    elif current_checkpoint_path.exists() or current_verified_path.exists():
        if current_checkpoint_path.is_symlink() or current_verified_path.is_symlink():
            raise ValueError('검증 지점에 심볼릭 링크를 사용할 수 없습니다.')
        try:
            current_checkpoint_record = json.loads(current_checkpoint_path.read_text(encoding='utf-8'))
            current_verified_bytes = current_checkpoint_record['bytes']
            if current_checkpoint_record['source'] != current_source_identity or isinstance(current_verified_bytes, bool) or not isinstance(current_verified_bytes, int) or not 0 <= current_verified_bytes <= current_prefix_bytes:
                raise ValueError('검증 지점의 원본이나 크기가 일치하지 않습니다.')
            if current_completed_link and current_verified_bytes != current_prefix_bytes:
                raise ValueError('완성된 링크의 검증 지점이 불완전합니다.')
            current_saved_digest = hashlib.sha256()
            with current_source_path.open('rb') as current_source_stream, current_verified_path.open('rb') as current_verified_stream:
                current_remaining_bytes = current_verified_bytes
                while current_remaining_bytes:
                    current_chunk_length = min(1024 * 1024, current_remaining_bytes)
                    current_source_chunk = current_source_stream.read(current_chunk_length)
                    current_saved_chunk = current_verified_stream.read(current_chunk_length)
                    if len(current_source_chunk) != current_chunk_length or current_source_chunk != current_saved_chunk:
                        raise ValueError('저장된 검증 지점의 파일이 변경되었습니다.')
                    current_saved_digest.update(current_saved_chunk)
                    current_remaining_bytes -= current_chunk_length
            if current_saved_digest.hexdigest() != current_checkpoint_record['sha256']:
                raise ValueError('저장된 검증 지점의 해시가 일치하지 않습니다.')
            current_prefix_digest = current_saved_digest
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as current_checkpoint_error:
            raise ValueError('검증 지점이 누락되었거나 손상되었습니다.') from current_checkpoint_error
    else:
        with current_verified_path.open('xb'):
            pass

    def persist_verified_checkpoint(current_verified_stream):
        current_verified_stream.flush()
        os.fsync(current_verified_stream.fileno())
        current_checkpoint_record = {'source': current_source_identity, 'bytes': current_verified_bytes, 'sha256': current_prefix_digest.hexdigest()}
        current_temporary_path = current_checkpoint_path.with_name(current_checkpoint_path.name + '.' + os.urandom(8).hex() + '.tmp')
        try:
            with current_temporary_path.open('x', encoding='utf-8') as current_checkpoint_stream:
                json.dump(current_checkpoint_record, current_checkpoint_stream)
                current_checkpoint_stream.flush()
                os.fsync(current_checkpoint_stream.fileno())
            os.replace(current_temporary_path, current_checkpoint_path)
            current_directory_fd = os.open(current_checkpoint_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(current_directory_fd)
            finally:
                os.close(current_directory_fd)
        finally:
            current_temporary_path.unlink(missing_ok=True)

    with current_source_path.open('rb') as current_source_stream, current_verified_path.open('r+b') as current_verified_stream:
        current_source_stream.seek(current_verified_bytes)
        current_verified_stream.truncate(current_verified_bytes)
        current_verified_stream.seek(current_verified_bytes)
        if not current_checkpoint_path.exists():
            persist_verified_checkpoint(current_verified_stream)
        current_record_value.update(stage='기존 부분 파일 검증', bytes=current_verified_bytes, total_bytes=expected_total_bytes, existing_bytes=current_prefix_bytes, verified_bytes=current_verified_bytes, resumed_bytes=current_verified_bytes)
        if current_verified_bytes < current_prefix_bytes:
            current_http_request = urllib.request.Request(current_download_url, headers={'Range': f'bytes={current_verified_bytes}-{current_prefix_bytes-1}', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(current_http_request, timeout=120) as current_http_response:
                current_expected_range = f'bytes {current_verified_bytes}-{current_prefix_bytes-1}/{expected_total_bytes}'
                if current_http_response.status != 206 or current_http_response.headers.get('Content-Range') != current_expected_range:
                    raise ValueError('서버가 부분 파일 검증에 필요한 정확한 범위를 제공하지 않았습니다.')
                current_last_checkpoint = current_verified_bytes
                while current_verified_bytes < current_prefix_bytes:
                    current_chunk_length = min(1024 * 1024, current_prefix_bytes - current_verified_bytes)
                    current_local_chunk = current_source_stream.read(current_chunk_length)
                    current_remote_chunk = current_http_response.read(current_chunk_length)
                    if len(current_local_chunk) != current_chunk_length or current_local_chunk != current_remote_chunk:
                        raise ValueError('기존 부분 파일이 서버 데이터와 일치하지 않습니다.')
                    current_verified_stream.write(current_local_chunk)
                    current_prefix_digest.update(current_local_chunk)
                    current_verified_bytes += current_chunk_length
                    if current_verified_bytes - current_last_checkpoint >= 16 * 1024 * 1024 or current_verified_bytes == current_prefix_bytes:
                        persist_verified_checkpoint(current_verified_stream)
                        current_last_checkpoint = current_verified_bytes
                    current_record_value.update(stage='기존 부분 파일 검증', bytes=current_verified_bytes, total_bytes=expected_total_bytes, verified_bytes=current_verified_bytes)
        current_final_stat = current_source_path.stat()
        if (current_final_stat.st_dev, current_final_stat.st_ino, current_final_stat.st_size, current_final_stat.st_mtime_ns) != (current_source_stat.st_dev, current_source_stat.st_ino, current_source_stat.st_size, current_source_stat.st_mtime_ns):
            raise ValueError('검증 중 기존 부분 파일이 변경되었습니다.')
    if not current_completed_link:
        os.link(current_verified_path, current_partial_path)
        current_directory_fd = os.open(current_partial_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(current_directory_fd)
        finally:
            os.close(current_directory_fd)
    if not retain_checkpoint_value:
        if current_verified_path != current_partial_path:
            current_verified_path.unlink(missing_ok=True)
        current_checkpoint_path.unlink(missing_ok=True)
    current_record_value.update(stage='기존 부분 파일 검증 완료', bytes=current_prefix_bytes, total_bytes=expected_total_bytes, resumed_bytes=current_prefix_bytes)
    return current_prefix_bytes


def download_verified_curl(current_download_url, current_target_path, expected_sha256_value, expected_total_bytes, model_identifier_value):
    """기존 파일 경로를 부분 파일로 쓰는 curl 전송을 공용 상태와 해시 검증에 연결한다."""
    import subprocess
    import threading
    if current_target_path.is_symlink():
        raise ValueError('모델 파일에 심볼릭 링크를 사용할 수 없습니다.')
    current_target_path.parent.mkdir(parents=True, exist_ok=True)
    current_resume_bytes = current_target_path.stat().st_size if current_target_path.exists() else 0
    if current_resume_bytes > expected_total_bytes:
        raise ValueError('부분 다운로드 크기가 예상 크기를 초과합니다.')
    with track_model_download(model_identifier_value) as current_download_record:
        current_download_record.update(stage='다운로드', bytes=current_resume_bytes, total_bytes=expected_total_bytes, resumed_bytes=current_resume_bytes)
        current_stop_event = threading.Event()
        def report_curl_download_progress():
            while not current_stop_event.wait(1):
                current_received_bytes = current_target_path.stat().st_size if current_target_path.exists() else 0
                current_download_record.update(bytes=current_received_bytes)
        current_progress_thread = threading.Thread(target=report_curl_download_progress, daemon=True)
        current_progress_thread.start()
        try:
            if current_resume_bytes != expected_total_bytes:
                subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error', '--retry', '2', '--continue-at', '-', '--output', str(current_target_path), current_download_url], check=True)
        finally:
            current_stop_event.set()
            current_progress_thread.join()
        current_received_bytes = current_target_path.stat().st_size
        current_download_record.update(stage='SHA-256 검증', bytes=current_received_bytes)
        if current_received_bytes != expected_total_bytes:
            raise ValueError('모델 파일 크기가 일치하지 않습니다.')
        with current_target_path.open('rb') as current_file_stream:
            if hashlib.file_digest(current_file_stream, 'sha256').hexdigest() != expected_sha256_value:
                raise ValueError('모델 파일 SHA-256이 일치하지 않습니다.')
