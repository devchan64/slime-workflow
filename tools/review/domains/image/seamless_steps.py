"""심리스 단계별 산출물 체크포인트 무결성 검증."""
import hashlib
import json


def calculate_stage_file_hash(current_file_path):
    return hashlib.sha256(current_file_path.read_bytes()).hexdigest()


def read_seamless_stage_checkpoints(current_job_root, current_request_record, stage_output_names):
    request_digest_value = hashlib.sha256(json.dumps(current_request_record,sort_keys=True).encode()).hexdigest()
    completed_stage_count = 0
    for stage_index_value in range(1,len(stage_output_names)+1):
        checkpoint_file_path = current_job_root/f'stage-{stage_index_value}.checkpoint.json'
        if not checkpoint_file_path.exists():
            if any((current_job_root/f'stage-{later_stage_index}.checkpoint.json').exists() for later_stage_index in range(stage_index_value+1,len(stage_output_names)+1)):
                raise ValueError('단계 체크포인트 순서 오류')
            break
        checkpoint_record_value = json.loads(checkpoint_file_path.read_text())
        expected_hash_values = {current_file_name:calculate_stage_file_hash(current_job_root/current_file_name) for current_file_name in stage_output_names[stage_index_value-1]}
        if checkpoint_record_value != {'request_sha256':request_digest_value,'files':expected_hash_values}:
            raise ValueError(f'{stage_index_value}단계 체크포인트 무결성 오류')
        completed_stage_count = stage_index_value
    return completed_stage_count, request_digest_value
