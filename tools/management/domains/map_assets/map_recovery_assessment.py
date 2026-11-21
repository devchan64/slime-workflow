"""맵 변경 복구에 필요한 DB 접수와 파일 해시를 부작용 없이 분류한다."""
import re


def assess_map_recovery_evidence(current_request_hash, current_receipt_record, current_file_records):
    """관측 결과만 분류한다. 반환값은 복구·재접수 권한이 아니다."""
    current_hash_pattern = re.compile(r"[a-f0-9]{64}")
    if not isinstance(current_request_hash, str) or not current_hash_pattern.fullmatch(current_request_hash):
        raise ValueError('맵 변경 요청 해시 오류')
    if not isinstance(current_receipt_record, dict) or current_receipt_record.get('request_sha256') != current_request_hash or current_receipt_record.get('state') not in ('matched', 'mismatch', 'not_found', 'unavailable'):
        raise ValueError('맵 변경 접수 관측 오류')
    if not isinstance(current_file_records, list) or not current_file_records:
        raise ValueError('맵 변경 파일 관측 누락')
    current_file_states = []
    current_file_names = set()
    for current_file_record in current_file_records:
        if not isinstance(current_file_record, dict) or set(current_file_record) != {'name', 'before_sha256', 'after_sha256', 'observed_sha256'}:
            raise ValueError('맵 변경 파일 관측 형식 오류')
        current_file_name = current_file_record['name']
        if not isinstance(current_file_name, str) or not current_file_name or current_file_name in current_file_names:
            raise ValueError('맵 변경 파일 식별 오류')
        current_file_names.add(current_file_name)
        for current_hash_key in ('before_sha256', 'after_sha256', 'observed_sha256'):
            current_hash_value = current_file_record[current_hash_key]
            if not isinstance(current_hash_value, str) or not current_hash_pattern.fullmatch(current_hash_value):
                raise ValueError('맵 변경 파일 해시 오류')
        if current_file_record['observed_sha256'] == current_file_record['after_sha256']:
            current_file_state = 'after'
        elif current_file_record['observed_sha256'] == current_file_record['before_sha256']:
            current_file_state = 'before'
        else:
            current_file_state = 'conflict'
        current_file_states.append({'name': current_file_name, 'state': current_file_state})
    current_receipt_state = current_receipt_record['state']
    if any(current_file_value['state'] == 'conflict' for current_file_value in current_file_states):
        current_assessment_state = 'file_conflict'
    elif current_receipt_state == 'mismatch':
        current_assessment_state = 'receipt_mismatch'
    elif current_receipt_state != 'matched':
        current_assessment_state = 'receipt_unconfirmed'
    elif any(current_file_value['state'] == 'before' for current_file_value in current_file_states):
        current_assessment_state = 'files_incomplete'
    else:
        current_assessment_state = 'files_match_receipt'
    return {'state': current_assessment_state, 'receipt_state': current_receipt_state, 'files': current_file_states}


def assess_map_plan_evidence(current_plan_record, current_before_files, current_observed_files, current_receipt_record):
    """메모리의 변경 계획과 관측 바이트를 대조하며 파일을 읽거나 수정하지 않는다."""
    import hashlib
    import json
    if not isinstance(current_plan_record, dict) or set(current_plan_record) != {'database_request', 'request_sha256', 'pending_files'}:
        raise ValueError('맵 변경 계획 형식 오류')
    try:
        current_request_bytes = json.dumps(current_plan_record['database_request'], sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as current_serialization_error:
        raise ValueError('맵 변경 요청 직렬화 오류') from current_serialization_error
    current_request_hash = hashlib.sha256(current_request_bytes).hexdigest()
    if current_request_hash != current_plan_record['request_sha256']:
        raise ValueError('맵 변경 계획의 요청 해시 불일치')
    current_pending_files = current_plan_record['pending_files']
    if not isinstance(current_pending_files, dict) or not current_pending_files or not isinstance(current_before_files, dict) or not isinstance(current_observed_files, dict) or set(current_pending_files) != set(current_before_files) or set(current_pending_files) != set(current_observed_files):
        raise ValueError('맵 변경 계획과 관측 파일 목록 불일치')
    current_file_records = []
    for current_file_path, current_after_bytes in current_pending_files.items():
        current_before_bytes = current_before_files[current_file_path]
        current_observed_bytes = current_observed_files[current_file_path]
        if not all(isinstance(current_file_bytes, bytes) for current_file_bytes in (current_before_bytes, current_after_bytes, current_observed_bytes)):
            raise ValueError('맵 변경 파일 바이트 오류')
        current_file_records.append({'name': str(current_file_path), 'before_sha256': hashlib.sha256(current_before_bytes).hexdigest(), 'after_sha256': hashlib.sha256(current_after_bytes).hexdigest(), 'observed_sha256': hashlib.sha256(current_observed_bytes).hexdigest()})
    return assess_map_recovery_evidence(current_request_hash, current_receipt_record, current_file_records)
