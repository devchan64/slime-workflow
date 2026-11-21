"""영상 생성 완료 기록의 공개 결과 파일 검증."""
import re
import json

VIDEO_RESULT_FILE_NAMES = ('preview.mp4', 'frames.zip', 'output-000.png')


def validate_video_result_files(current_job_root, current_result_record):
    current_attempt_identifier = current_result_record.get('attempt')
    if not isinstance(current_attempt_identifier, str) or not re.fullmatch(r'[a-f0-9]{32}', current_attempt_identifier):
        raise ValueError('영상 결과의 실행 시도 ID가 올바르지 않습니다.')
    current_attempt_root = current_job_root / 'attempts' / current_attempt_identifier
    for current_file_name in VIDEO_RESULT_FILE_NAMES:
        current_result_path = current_attempt_root / current_file_name
        if not current_result_path.resolve().is_relative_to(current_job_root.resolve()):
            raise ValueError(f'영상 결과 경로가 작업 폴더를 벗어났습니다: {current_result_path}')
        if not current_result_path.is_file():
            raise ValueError(f'완료 기록의 영상 결과 파일이 없습니다: {current_result_path}')


def enrich_video_result_status(current_job_root, current_status_record, current_route_prefix):
    if current_status_record['status'] != 'completed':
        return current_status_record
    current_status_record = dict(current_status_record)
    for current_field_name in ('video', 'download', 'image', 'result_error'):
        current_status_record.pop(current_field_name, None)
    try:
        current_result_path = current_job_root / 'result.json'
        if not current_result_path.resolve().is_relative_to(current_job_root.resolve()):
            raise ValueError('영상 결과 기록 경로가 작업 폴더를 벗어났습니다.')
        current_result_record = json.loads(current_result_path.read_text())
        if not isinstance(current_result_record, dict):
            raise ValueError('영상 결과 기록은 객체여야 합니다.')
        validate_video_result_files(current_job_root, current_result_record)
    except (ValueError, OSError) as current_result_error:
        # 생성 작업 상태와 결과 조회 오류는 구분한다. 잘못된 결과 URL은 공개하지 않는다.
        current_status_record['result_error'] = str(current_result_error)
        return current_status_record
    current_result_base = f'{current_route_prefix}/jobs/{current_job_root.name}/attempts/{current_result_record["attempt"]}/'
    current_status_record.update(video=current_result_base+'preview.mp4', download=current_result_base+'frames.zip', image=current_result_base+'output-000.png')
    return current_status_record
