"""저장된 참조 이미지 사본과 설정을 검증해 Gradio 입력으로 복원한다."""
import hashlib
import io
from pathlib import Path
import re
import gradio as gr
from PIL import Image

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]


def validate_history_input_settings(current_history_record):
    if not isinstance(current_history_record, dict):
        raise gr.Error('저장 이력은 객체여야 합니다.')
    current_request_record=current_history_record.get('request',{})
    if not isinstance(current_request_record, dict):
        raise gr.Error('저장된 입력 요청은 객체여야 합니다.')
    for current_setting_name in ('prompt', 'tag'):
        if current_setting_name in current_request_record and not isinstance(current_request_record[current_setting_name], str):
            raise gr.Error(f'저장된 {current_setting_name} 값은 문자열이어야 합니다.')
    for current_setting_name in ('width', 'height', 'steps', 'seed'):
        if current_setting_name in current_request_record and type(current_request_record[current_setting_name]) is not int:
            raise gr.Error(f'저장된 {current_setting_name} 값은 정수여야 합니다.')
    return current_request_record


def restore_reference_inputs(current_history_record, reference_storage_root=None, reference_slot_limit=3):
    current_request_record = validate_history_input_settings(current_history_record)
    restored_reference_images=[]
    reference_snapshot_records=current_request_record.get('reference_snapshots',[])
    current_reference_names = current_request_record.get('references', [])
    if not isinstance(current_reference_names, list) or any(not isinstance(current_reference_name, str) for current_reference_name in current_reference_names):
        raise gr.Error('저장된 참조 목록은 파일명 문자열 목록이어야 합니다.')
    if not isinstance(reference_snapshot_records, list):
        raise gr.Error('저장된 참조 사본 정보는 목록이어야 합니다.')
    for current_snapshot_record in reference_snapshot_records:
        if not isinstance(current_snapshot_record, dict) or not isinstance(current_snapshot_record.get('path'), str):
            raise gr.Error('저장된 참조 사본에 유효한 경로가 없습니다.')
        current_snapshot_digest = current_snapshot_record.get('sha256')
        if not isinstance(current_snapshot_digest, str) or not re.fullmatch(r'[a-f0-9]{64}', current_snapshot_digest):
            raise gr.Error('저장된 참조 사본의 SHA-256 형식이 잘못되었습니다.')
    if current_reference_names and not reference_snapshot_records:
        raise gr.Error('저장된 참조 목록에 사본 검증 정보가 없어 입력을 복원할 수 없습니다. 참조 이미지를 직접 첨부하세요.')
    if current_reference_names and (
        not isinstance(reference_snapshot_records, list)
        or any(not isinstance(current_snapshot_record, dict) for current_snapshot_record in reference_snapshot_records)
        or [current_snapshot_record.get('path') for current_snapshot_record in reference_snapshot_records] != current_reference_names
    ):
        raise gr.Error('저장된 참조 목록과 사본 정보의 개수 또는 순서가 다릅니다.')
    if reference_snapshot_records:
        generation_identifier_value=current_history_record.get('id','')
        if not isinstance(generation_identifier_value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-f0-9]{8}',generation_identifier_value):
            raise gr.Error('생성 ID 형식 오류')
        reference_storage_root=Path(reference_storage_root or WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-2511-three-reference').resolve()
        reference_job_directory = reference_storage_root/generation_identifier_value
        if reference_job_directory.is_symlink():
            raise gr.Error('참조 이미지 작업 폴더는 심볼릭 링크일 수 없습니다.')
        for reference_slot_number,current_snapshot_record in enumerate(reference_snapshot_records,1):
            if reference_slot_number>reference_slot_limit or current_snapshot_record['path']!=f'reference-{reference_slot_number}.png':
                raise gr.Error('참조 이미지 순서 또는 경로 오류')
            reference_source_path=(reference_job_directory/current_snapshot_record['path']).resolve()
            if not reference_source_path.is_relative_to(reference_job_directory):raise gr.Error('참조 이미지가 선택한 작업 폴더 밖을 가리킵니다.')
            if not reference_source_path.is_file():raise gr.Error('저장된 참조 이미지가 없습니다: '+current_snapshot_record['path'])
            reference_source_bytes=reference_source_path.read_bytes()
            if hashlib.sha256(reference_source_bytes).hexdigest()!=current_snapshot_record['sha256']:raise gr.Error('참조 이미지 해시 불일치')
            with Image.open(io.BytesIO(reference_source_bytes)) as reference_image_value:
                restored_reference_images.append(reference_image_value.copy())
    restored_reference_images.extend([None]*(reference_slot_limit-len(restored_reference_images)))
    return (current_request_record.get('prompt',''),current_request_record.get('tag',''),current_request_record.get('width',512),current_request_record.get('height',512),current_request_record.get('steps',4),current_request_record.get('seed',10107),*restored_reference_images,'선택한 이력의 설정과 참조 이미지 '+str(len(reference_snapshot_records))+'장을 불러왔습니다.')
