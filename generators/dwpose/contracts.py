"""단일 PNG DWPose 추출 요청 계약."""
import io
from pathlib import Path
from PIL import Image
from tools.review.domains.image.three_reference_generation import decode_reference_image
from generators.kimodo.dwpose_runtime import validate_fun_pose_assets
DWPOSE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DWPOSE_JOB_STORAGE = DWPOSE_WORKSPACE_ROOT / '.tmp/test/dwpose'


def validate_dwpose_request(current_request_record):
    current_allowed_fields = {'action', 'images', 'pose_include_hands', 'pose_include_face'}
    if not isinstance(current_request_record, dict) or set(current_request_record) - current_allowed_fields or not {'action', 'images'} <= set(current_request_record):
        raise ValueError('DWPose 요청 필드 오류')
    if current_request_record['action'] != 'generate' or not isinstance(current_request_record['images'], list) or len(current_request_record['images']) != 1:
        raise ValueError('generate와 PNG 이미지 1장이 필요합니다.')
    current_image_bytes = decode_reference_image(current_request_record['images'][0])
    with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
        if current_source_image.size != (832, 480):
            raise ValueError('DWPose 입력은 832×480 PNG여야 합니다.')
    for current_option_name in ('pose_include_hands', 'pose_include_face'):
        if type(current_request_record.get(current_option_name, False)) is not bool:
            raise ValueError(f'{current_option_name}: bool이 필요합니다.')
    return {**current_request_record, 'frames': 1, 'steps': 1, 'width': 832, 'height': 480, 'prompt': '단일 이미지 DWPose 추출', 'seed': 0}
