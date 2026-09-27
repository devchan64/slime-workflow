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
