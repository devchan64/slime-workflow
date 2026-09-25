"""도메인 공용 생성 기록의 원자적 저장."""
import json
import uuid

def write_record_atomically(record_file_path, record_payload_value):
    temporary_record_path = record_file_path.with_name(record_file_path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary_record_path.write_text(json.dumps(record_payload_value, ensure_ascii=False)+'\n')
    temporary_record_path.replace(record_file_path)

