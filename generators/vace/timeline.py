"""VACE V2V의 희소 프레임 입력과 수정 마스크 계약."""
import base64
import json
from pathlib import Path
from PIL import Image, ImageOps
from generators.vace.contracts import validate_vace_request
from tools.review.domains.image.three_reference_generation import verify_reference_snapshots

VACE_TIMELINE_STORAGE_ROOT = Path(__file__).resolve().parents[2]/'.tmp/test/wan21-vace-v2v'
VACE_TIMELINE_SLOT_LIMIT = 161


def validate_timeline_request(current_request_record):
    if not isinstance(current_request_record, dict):
        raise ValueError('요청은 객체여야 합니다.')
    current_frame_entries = current_request_record.get('frame_entries')
    current_image_values = current_request_record.get('images')
    current_identity_count = current_request_record.get('identity_reference_count', 0)
    if type(current_identity_count) is not int or current_identity_count not in (0, 1):
        raise ValueError('외형 참조는 0장 또는 1장이어야 합니다.')
    if not isinstance(current_frame_entries,list) or not 1 <= len(current_frame_entries) <= VACE_TIMELINE_SLOT_LIMIT:
        raise ValueError('배치 이미지는 1~161장이어야 합니다.')
    if not isinstance(current_image_values,list) or len(current_image_values)!=len(current_frame_entries)+current_identity_count:
        raise ValueError('이미지와 프레임 배치 개수가 다릅니다.')
    current_base_request = {current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name not in ('frame_entries', 'identity_reference_count')}
    current_base_request['images'] = current_image_values[:1]
    current_base_request.setdefault('negative_prompt','')
    current_validated_record = validate_vace_request(current_base_request)
    current_normalized_images = []
    current_seen_frames = set()
    for current_frame_entry,current_image_value in zip(current_frame_entries,current_image_values):
        if not isinstance(current_frame_entry,dict) or set(current_frame_entry)!={'frame','editable'}:
            raise ValueError('프레임 항목은 frame, editable만 허용합니다.')
        current_frame_number = current_frame_entry['frame']
        if type(current_frame_number) is not int or not 0 <= current_frame_number < current_validated_record['frames'] or current_frame_number in current_seen_frames:
            raise ValueError('프레임 번호는 0부터 시작하며 범위 내에서 중복 없이 지정해야 합니다.')
        if type(current_frame_entry['editable']) is not bool:
            raise ValueError('editable은 참/거짓이어야 합니다.')
        current_seen_frames.add(current_frame_number)
        current_base_request['images']=[current_image_value]
        current_normalized_images.extend(validate_vace_request(current_base_request)['images'])
    if current_identity_count:
        current_base_request['images'] = current_image_values[-1:]
        current_normalized_images.extend(validate_vace_request(current_base_request)['images'])
        current_validated_record['identity_reference_count'] = current_identity_count
    current_validated_record['images']=current_normalized_images
    current_validated_record['frame_entries']=current_frame_entries
    current_validated_record['vace'].update(task='v2v',video='assembled-frames',mask='editable-white-preserved-black')
    return current_validated_record


def verify_timeline_request(current_job_root):
    current_saved_record=json.loads((current_job_root/'request.json').read_text())
    if not current_saved_record.get('reference_snapshots'):
        raise ValueError('입력 스냅샷이 없습니다.')
    verify_reference_snapshots(current_job_root,current_saved_record)
    current_restored_record={current_field_name:current_field_value for current_field_name,current_field_value in current_saved_record.items() if current_field_name not in ('vace','references','reference_snapshots')}
    current_restored_record['images']=[base64.b64encode((current_job_root/current_reference_name).read_bytes()).decode() for current_reference_name in current_saved_record['references']]
    current_validated_record=validate_timeline_request(current_restored_record)
    if current_validated_record['vace']!=current_saved_record['vace']:
        raise ValueError('저장된 설정 또는 프롬프트 해시가 일치하지 않습니다.')
    return current_saved_record


def assemble_timeline_inputs(current_job_root,current_request_record):
    current_target_size=(current_request_record['width'],current_request_record['height'])
    current_video_frames=[Image.new('RGB',current_target_size,(127,127,127)) for _ in range(current_request_record['frames'])]
    current_mask_frames=[Image.new('RGB',current_target_size,'white') for _ in range(current_request_record['frames'])]
    for current_frame_entry,current_reference_name in zip(current_request_record['frame_entries'],current_request_record['references']):
        with Image.open(current_job_root/current_reference_name) as current_source_image:
            current_video_frames[current_frame_entry['frame']]=ImageOps.pad(current_source_image.convert('RGB'),current_target_size,color='white')
        current_mask_frames[current_frame_entry['frame']]=Image.new('RGB',current_target_size,'white' if current_frame_entry['editable'] else 'black')
    return current_video_frames,current_mask_frames


def load_identity_references(current_job_root, current_request_record):
    """포즈 입력 뒤의 외형 참조만 별도 모델 입력으로 읽는다."""
    if not current_request_record.get('identity_reference_count', 0):
        return None
    current_reference_path = current_job_root / current_request_record['references'][-1]
    with Image.open(current_reference_path) as current_reference_image:
        return [current_reference_image.convert('RGB')]
