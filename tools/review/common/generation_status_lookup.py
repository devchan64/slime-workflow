"""자동 갱신 중 삭제된 이력과 조회 실패를 구분한다."""


def read_existing_generation_status(current_command_callback, current_job_identifier):
    try:
        return current_command_callback('status', {'id': current_job_identifier})
    except (RuntimeError, ValueError) as current_status_error:
        current_history_response = current_command_callback('history', {})
        if not isinstance(current_history_response, dict) or not isinstance(current_history_response.get('records'), list):
            raise ValueError('이력 조회 응답의 records는 목록이어야 합니다.') from current_status_error
        current_history_records = current_history_response['records']
        for current_history_record in current_history_records:
            if not isinstance(current_history_record, dict) or not isinstance(current_history_record.get('id'), str) or not current_history_record['id'].strip():
                raise ValueError('이력 조회 응답의 각 항목에는 비어 있지 않은 문자열 id가 필요합니다.') from current_status_error
        if any(current_history_record['id'] == current_job_identifier for current_history_record in current_history_records):
            raise current_status_error
        return None
