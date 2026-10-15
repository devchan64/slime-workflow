"""저장된 참조 이미지 사본과 설정을 검증해 Gradio 입력으로 복원한다."""
import hashlib
import io
from pathlib import Path
import re
import gradio as gr
from PIL import Image

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]


def restore_reference_inputs(current_history_record, reference_storage_root=None, reference_slot_limit=3):
    current_request_record=current_history_record.get('request',{})
    restored_reference_images=[]
    reference_snapshot_records=current_request_record.get('reference_snapshots',[])
    if reference_snapshot_records:
        generation_identifier_value=current_history_record.get('id','')
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-f0-9]{8}',generation_identifier_value):
            raise gr.Error('생성 ID 형식 오류')
        reference_storage_root=Path(reference_storage_root or WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-2511-three-reference').resolve()
        for reference_slot_number,current_snapshot_record in enumerate(reference_snapshot_records,1):
            if reference_slot_number>reference_slot_limit or current_snapshot_record['path']!=f'reference-{reference_slot_number}.png':
                raise gr.Error('참조 이미지 순서 또는 경로 오류')
            reference_source_path=(reference_storage_root/generation_identifier_value/current_snapshot_record['path']).resolve()
            if not reference_source_path.is_relative_to(reference_storage_root):raise gr.Error('참조 이미지 경로 오류')
            if not reference_source_path.is_file():raise gr.Error('저장된 참조 이미지가 없습니다: '+current_snapshot_record['path'])
            reference_source_bytes=reference_source_path.read_bytes()
            if hashlib.sha256(reference_source_bytes).hexdigest()!=current_snapshot_record['sha256']:raise gr.Error('참조 이미지 해시 불일치')
            with Image.open(io.BytesIO(reference_source_bytes)) as reference_image_value:
                restored_reference_images.append(reference_image_value.copy())
    restored_reference_images.extend([None]*(reference_slot_limit-len(restored_reference_images)))
    return (current_request_record.get('prompt',''),current_request_record.get('tag',''),current_request_record.get('width',512),current_request_record.get('height',512),current_request_record.get('steps',4),current_request_record.get('seed',10107),*restored_reference_images,'선택한 이력의 설정과 참조 이미지 '+str(len(reference_snapshot_records))+'장을 불러왔습니다.')

