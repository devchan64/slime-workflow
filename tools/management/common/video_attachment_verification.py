"""재개할 영상 입력의 저장 파일과 해시를 검사한다."""
import hashlib
import os
import re
import stat


def verify_saved_video_attachments(current_job_root, saved_request_record, selected_field_names, attachment_filename_overrides=None, allow_legacy_missing_hash=False):
    for current_field_name in selected_field_names:
        expected_file_name = current_field_name.replace('_', '-') + '.mp4'
        if current_field_name == 'driving_video':
            expected_file_name = 'driving.mp4'
        if attachment_filename_overrides is not None:
            expected_file_name = attachment_filename_overrides.get(current_field_name, expected_file_name)
        expected_hash_value = saved_request_record.get(current_field_name + '_sha256')
        if (saved_request_record.get(current_field_name + '_file') != expected_file_name
                or not ((allow_legacy_missing_hash and current_field_name + '_sha256' not in saved_request_record)
                        or (isinstance(expected_hash_value, str) and re.fullmatch(r'[0-9a-f]{64}', expected_hash_value) is not None))):
            raise ValueError('영상 입력 파일 또는 해시 기록이 올바르지 않습니다.')
        current_file_path = current_job_root / expected_file_name
        try:
            current_file_descriptor = os.open(current_file_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(current_file_descriptor, 'rb') as current_file_stream:
                initial_file_stat = os.fstat(current_file_stream.fileno())
                if not stat.S_ISREG(initial_file_stat.st_mode):
                    raise ValueError('영상 입력은 일반 파일이어야 합니다.')
                current_hash_object = hashlib.sha256()
                while current_file_chunk := current_file_stream.read(1024 * 1024):
                    current_hash_object.update(current_file_chunk)
                final_file_stat = os.fstat(current_file_stream.fileno())
                current_path_stat = os.stat(current_file_path, follow_symlinks=False)
                if ((initial_file_stat.st_dev, initial_file_stat.st_ino, initial_file_stat.st_size, initial_file_stat.st_mtime_ns, initial_file_stat.st_ctime_ns)
                        != (final_file_stat.st_dev, final_file_stat.st_ino, final_file_stat.st_size, final_file_stat.st_mtime_ns, final_file_stat.st_ctime_ns)
                        or (final_file_stat.st_dev, final_file_stat.st_ino) != (current_path_stat.st_dev, current_path_stat.st_ino)
                        or (expected_hash_value is not None and current_hash_object.hexdigest() != expected_hash_value)):
                    raise ValueError('영상 입력 파일이 변경되었거나 해시가 일치하지 않습니다.')
        except OSError as current_file_error:
            raise ValueError('영상 입력 일반 파일을 확인할 수 없습니다.') from current_file_error
