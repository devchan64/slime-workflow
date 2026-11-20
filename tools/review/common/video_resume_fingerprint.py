"""영상 재개 검토에 쓰일 저장 요청과 모든 입력 파일의 지문."""
import hashlib
import json
import os
import stat
from pathlib import Path


VIDEO_RESUME_SERVICES = ('dwpose', 'wan22-animate2', 'wan22-vace')
VIDEO_MODE_ATTACHMENTS = {
    'text': (), 'reference': (), 'first_frame': (),
    'video_edit': ('edit_video', 'edit_mask'),
    'video_condition': ('edit_video',), 'pose': ('pose_video',),
}


def fingerprint_video_resume_inputs(current_job_directory, current_service_name):
    """작업을 실행하지 않고 저장된 일반 파일의 내용을 스트리밍 해시한다."""
    if current_service_name not in VIDEO_RESUME_SERVICES:
        raise ValueError('영상 재개 서비스 오류')
    current_result_hash = hashlib.sha256()
    current_result_hash.update(b'video-resume-v1\0' + current_service_name.encode('ascii') + b'\0')
    try:
        current_directory_descriptor = os.open(Path(current_job_directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            def hash_saved_video_file(current_file_name, optional_file_value=False, parse_json_value=False):
                try:
                    current_file_descriptor = os.open(current_file_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current_directory_descriptor)
                except FileNotFoundError:
                    if not optional_file_value:
                        raise
                    current_result_hash.update(current_file_name.encode('ascii') + b'\0missing\0')
                    return None
                with os.fdopen(current_file_descriptor, 'rb') as current_file_stream:
                    initial_file_stat = os.fstat(current_file_stream.fileno())
                    if not stat.S_ISREG(initial_file_stat.st_mode) or (parse_json_value and initial_file_stat.st_size > 8 * 1024 * 1024):
                        raise ValueError('영상 재개 기록은 크기가 제한된 일반 파일이어야 합니다.')
                    current_file_hash = hashlib.sha256()
                    current_json_parts = []
                    for current_file_chunk in iter(lambda: current_file_stream.read(1024 * 1024), b''):
                        current_file_hash.update(current_file_chunk)
                        if parse_json_value:
                            current_json_parts.append(current_file_chunk)
                    final_file_stat = os.fstat(current_file_stream.fileno())
                    current_path_stat = os.stat(current_file_name, dir_fd=current_directory_descriptor, follow_symlinks=False)
                    def stable_file_identity(current_stat_record):
                        return (current_stat_record.st_dev, current_stat_record.st_ino, current_stat_record.st_size, current_stat_record.st_mtime_ns, current_stat_record.st_ctime_ns)
                    if stable_file_identity(initial_file_stat) != stable_file_identity(final_file_stat) or stable_file_identity(final_file_stat) != stable_file_identity(current_path_stat):
                        raise ValueError('영상 재개 입력이 조회 중 변경됐습니다.')
                    current_result_hash.update(current_file_name.encode('ascii') + b'\0present\0' + current_file_hash.digest())
                    return json.loads(b''.join(current_json_parts)) if parse_json_value else None

            saved_request_record = hash_saved_video_file('request.json', parse_json_value=True)
            saved_status_record = hash_saved_video_file('status.json', parse_json_value=True)
            if not isinstance(saved_request_record, dict) or not isinstance(saved_status_record, dict) or saved_status_record.get('status') not in ('failed', 'cancelled', 'paused'):
                raise ValueError('실패·취소·일시정지 영상 작업만 재개를 검토할 수 있습니다.')
            if current_service_name == 'wan22-vace':
                current_mode_value = saved_request_record.get('mode')
                if not isinstance(current_mode_value, str) or current_mode_value not in VIDEO_MODE_ATTACHMENTS:
                    raise ValueError('영상 재개 입력 모드 오류')
                selected_field_names = VIDEO_MODE_ATTACHMENTS[current_mode_value]
                expected_image_count = 0 if current_mode_value == 'text' else 1
            else:
                selected_field_names = ('driving_video',) if current_service_name == 'wan22-animate2' else ()
                expected_image_count = 1
            current_reference_names = saved_request_record.get('references')
            if current_reference_names != [f'reference-{current_index}.png' for current_index in range(1, expected_image_count + 1)]:
                raise ValueError('영상 재개 참조 이미지 목록 오류')
            for current_reference_name in current_reference_names:
                hash_saved_video_file(current_reference_name)
            for current_field_name in selected_field_names:
                expected_file_name = 'driving.mp4' if current_field_name == 'driving_video' else current_field_name.replace('_', '-') + '.mp4'
                if saved_request_record.get(current_field_name + '_file') != expected_file_name:
                    raise ValueError('영상 재개 첨부 파일 이름 오류')
                hash_saved_video_file(expected_file_name)
            hash_saved_video_file('gpu-command.json', optional_file_value=True)
            return {'status': saved_status_record['status'], 'fingerprint': current_result_hash.hexdigest()}
        finally:
            os.close(current_directory_descriptor)
    except (OSError, UnicodeError, json.JSONDecodeError) as current_read_error:
        raise ValueError('영상 재개 기록을 확인할 수 없습니다.') from current_read_error
