"""타일 원본을 보존하면서 공용 보더 크롭 결과와 출처를 저장한다."""
import hashlib
import json
import logging
from pathlib import Path

from PIL import Image

from tools.review.common.image_borders import crop_inner_border
from tools.review.common.image_edges import TEXTURE_COLOR_DIFFERENCE, TEXTURE_TRANSITION_RUN

TILE_BORDER_CROP_RATIO = 0.01
TILE_BORDER_CROP_NAME = 'border-crop.png'
TILE_BORDER_RECORD_NAME = 'border-crop.json'


def save_tile_border_result(current_job_root, current_request_record):
    """저장된 서버 크롭 설정이 있는 작업만 처리한다. 실패 시 원본은 보존한다."""
    if 'border_crop' not in current_request_record:
        return
    if current_request_record['border_crop'] != {'ratio': TILE_BORDER_CROP_RATIO}:
        raise ValueError('지원하지 않는 타일 보더 크롭 설정입니다.')
    current_job_root = Path(current_job_root)
    original_image_path = current_job_root/'result.png'
    cropped_image_path = current_job_root/TILE_BORDER_CROP_NAME
    crop_record_path = current_job_root/TILE_BORDER_RECORD_NAME
    temporary_crop_path = current_job_root/'border-crop.partial.png'
    logging.info('stage=border-crop source=%s ratio=%s', original_image_path, TILE_BORDER_CROP_RATIO)
    try:
        with Image.open(original_image_path) as original_image_value:
            cropped_image_value, crop_measurement_record = crop_inner_border(original_image_value, retained_border_ratio=TILE_BORDER_CROP_RATIO)
            cropped_image_value.save(temporary_crop_path)
        crop_result_record = {'status':'completed','source':'result.png','output':TILE_BORDER_CROP_NAME,'source_sha256':hashlib.sha256(original_image_path.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(temporary_crop_path.read_bytes()).hexdigest(),'output_size':list(cropped_image_value.size),'color_difference_threshold':TEXTURE_COLOR_DIFFERENCE,'transition_run':TEXTURE_TRANSITION_RUN,**crop_measurement_record}
        temporary_crop_path.replace(cropped_image_path)
        crop_record_path.write_text(json.dumps(crop_result_record,ensure_ascii=False,indent=2)+'\n')
        generation_result_path = current_job_root/'result.json'
        generation_result_record = json.loads(generation_result_path.read_text())
        generation_result_record['border_crop'] = crop_result_record
        generation_result_record['outputs'] = {'original':'result.png','border_crop':TILE_BORDER_CROP_NAME}
        temporary_result_path = current_job_root/'result.partial.json'
        temporary_result_path.write_text(json.dumps(generation_result_record,ensure_ascii=False,indent=2)+'\n')
        temporary_result_path.replace(generation_result_path)
        logging.info('stage=border-crop-completed output=%s size=%s',cropped_image_path,cropped_image_value.size)
    except Exception as crop_failure_value:
        temporary_crop_path.unlink(missing_ok=True)
        cropped_image_path.unlink(missing_ok=True)
        crop_record_path.write_text(json.dumps({'status':'failed','source':'result.png','error':str(crop_failure_value)},ensure_ascii=False,indent=2)+'\n')
        logging.exception('stage=border-crop-failed source=%s',original_image_path)
        raise
