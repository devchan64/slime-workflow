"""대기열 접속 전용 검수 캡처 작업자. 기본 운영 경로에는 아직 등록하지 않는다."""
import argparse
import json
import signal
from pathlib import Path

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.capture_delegation import normalize_capture_delegation_request


def execute_capture_worker_job(current_job_directory):
    """검증한 서비스와 입력으로 원 캡처를 실행하고 결과를 작업 폴더에 기록한다."""
    current_job_directory = Path(current_job_directory)
    if current_job_directory.is_symlink() or not current_job_directory.is_dir():
        raise ValueError('캡처 작업 폴더 오류')
    current_request_path = current_job_directory / 'request.json'
    if current_request_path.is_symlink() or not current_request_path.is_file():
        raise ValueError('캡처 요청 기록 오류')
    current_result_path = current_job_directory / 'capture-result.json'
    if current_result_path.is_symlink() or current_result_path.exists():
        raise ValueError('캡처 결과 경로가 이미 있거나 심볼릭 링크입니다.')
    current_request_record = json.loads(current_request_path.read_text(encoding='utf-8'))
    if not isinstance(current_request_record, dict) or set(current_request_record) != {'request_id', 'service', 'settings'}:
        raise ValueError('캡처 요청 형식 오류')
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_record['request_id'],str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_record['request_id']):
        raise ValueError('캡처 접수 ID 형식 오류')
    current_service_name = current_request_record['service']
    current_capture_settings = normalize_capture_delegation_request(current_service_name, current_request_record['settings'])
    if current_service_name == 'map-review':
        from tools.review.domains.map_review.capture import capture_map_review
        current_capture_result = capture_map_review(current_capture_settings)
    else:
        from tools.review.domains.character_review.capture import capture_character_review
        current_capture_result = capture_character_review(current_capture_settings)
    if not isinstance(current_capture_result, dict) or current_capture_result.get('status') != 'completed' or not isinstance(current_capture_result.get('images'), dict) or not current_capture_result['images']:
        raise ValueError('캡처 결과를 확인할 수 없습니다.')
    write_record_atomically(current_result_path, current_capture_result)
    return current_capture_result


def main_capture_worker_command():
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--job-dir', required=True)
    current_argument_values = current_argument_parser.parse_args()
    def interrupt_capture_worker(current_signal_number, current_stack_frame):
        raise RuntimeError('캡처 작업이 중지되었습니다.')
    current_previous_handler = signal.signal(signal.SIGTERM, interrupt_capture_worker)
    try:
        execute_capture_worker_job(current_argument_values.job_dir)
    finally:
        signal.signal(signal.SIGTERM, current_previous_handler)


if __name__ == '__main__':
    main_capture_worker_command()
