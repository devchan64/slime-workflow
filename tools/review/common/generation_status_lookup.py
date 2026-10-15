"""자동 갱신 중 삭제된 이력과 조회 실패를 구분한다."""


def read_existing_generation_status(current_command_callback, current_job_identifier):
    try:
        return current_command_callback('status', {'id': current_job_identifier})
    except (RuntimeError, ValueError) as current_status_error:
        current_history_records = current_command_callback('history', {})['records']
        if any(current_history_record['id'] == current_job_identifier for current_history_record in current_history_records):
            raise current_status_error
        return None
