"""도메인 공용 생성 기록의 원자적 저장."""
import json
import uuid

def validate_history_tag(history_tag_value):
    if not isinstance(history_tag_value,str):raise ValueError('생성 이력 태그는 문자열이어야 합니다.')
    normalized_tag_value=history_tag_value.strip()
    if len(normalized_tag_value)>80 or '\n' in normalized_tag_value or '\r' in normalized_tag_value:raise ValueError('생성 이력 태그는 줄바꿈 없이 80자 이하여야 합니다.')
    return normalized_tag_value

def write_record_atomically(record_file_path, record_payload_value):
    temporary_record_path = record_file_path.with_name(record_file_path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary_record_path.write_text(json.dumps(record_payload_value, ensure_ascii=False)+'\n')
    temporary_record_path.replace(record_file_path)


def load_generation_history_records(history_directory_path, generation_jobs_directory):
    """색인과 작업 원본을 합쳐 조회한다. 명시적으로 숨긴 과거 기록은 복구하지 않는다."""
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo

    generation_identifier_pattern = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}"
    history_reset_path = history_directory_path / '.reset-marker'
    history_reset_timestamp = history_reset_path.stat().st_mtime if history_reset_path.is_file() else 0
    history_records_by_identifier = {}
    for history_record_path in sorted(history_directory_path.glob('*.json')):
        current_history_record = json.loads(history_record_path.read_text())
        generation_job_identifier = current_history_record.get('id')
        if not isinstance(generation_job_identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', generation_job_identifier):
            raise ValueError(f'생성 이력 ID가 올바르지 않습니다: {history_record_path}')
        history_records_by_identifier[generation_job_identifier] = current_history_record
    if generation_jobs_directory.is_dir():
        for generation_job_path in generation_jobs_directory.iterdir():
            if not re.fullmatch(generation_identifier_pattern, generation_job_path.name):
                continue
            if generation_job_path.is_symlink():
                raise ValueError(f'생성 작업 경로는 심볼릭 링크일 수 없습니다: {generation_job_path}')
            generation_request_path = generation_job_path / 'request.json'
            generation_status_path = generation_job_path / 'status.json'
            if not generation_request_path.is_file() or not generation_status_path.is_file():
                continue
            if generation_request_path.stat().st_mtime <= history_reset_timestamp:
                continue
            generation_job_identifier = generation_job_path.name
            if generation_job_identifier not in history_records_by_identifier:
                history_records_by_identifier[generation_job_identifier] = {
                    'id': generation_job_identifier,
                    'created_at': datetime.strptime(generation_job_identifier[:19], '%Y-%m-%d_%H-%M-%S').replace(tzinfo=ZoneInfo('Asia/Seoul')).isoformat(),
                    'request': json.loads(generation_request_path.read_text()),
                    'status': json.loads(generation_status_path.read_text()),
                    'job_path': str(generation_job_path),
                }
    for generation_job_identifier in list(history_records_by_identifier):
        if (generation_jobs_directory / generation_job_identifier / '.history-deleted').exists() or (history_directory_path / 'deleted' / generation_job_identifier).exists():
            del history_records_by_identifier[generation_job_identifier]
    return sorted(history_records_by_identifier.values(), key=lambda current_history_record: current_history_record.get('created_at', current_history_record['id']), reverse=True)
