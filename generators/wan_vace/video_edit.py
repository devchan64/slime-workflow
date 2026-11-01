"""VACE 공식 마스크 편집 조건: 흰 영역 재생성, 검정 영역 원본 조건."""
import base64
import hashlib
import tempfile
from pathlib import Path
import cv2
import numpy as np

VACE_EDIT_INPUT_FIELDS = ('edit_video', 'edit_mask')


def decode_edit_video(current_video_path, current_frame_count):
    current_video_capture = cv2.VideoCapture(str(current_video_path))
    try:
        if (int(current_video_capture.get(3)), int(current_video_capture.get(4))) != (832, 480) or abs(current_video_capture.get(5)-16) > .01:
            raise ValueError('입력 영상·마스크는 832×480, 16fps여야 합니다.')
        current_frame_arrays = []
        for current_frame_index in range(current_frame_count):
            current_frame_ready, current_frame_pixels = current_video_capture.read()
            if not current_frame_ready:
                raise ValueError('입력 영상·마스크 프레임이 부족합니다.')
            current_frame_arrays.append(cv2.cvtColor(current_frame_pixels, cv2.COLOR_BGR2RGB))
        return np.stack(current_frame_arrays)
    finally:
        current_video_capture.release()


def validate_edit_inputs(current_request_record, current_input_fields=VACE_EDIT_INPUT_FIELDS):
    for current_field_name in current_input_fields:
        current_encoded_value = current_request_record[current_field_name]
        if not isinstance(current_encoded_value, str) or len(current_encoded_value) > 45_000_000:
            raise ValueError('입력 MP4는 base64 문자열 32MiB 이하여야 합니다.')
        current_video_bytes = base64.b64decode(current_encoded_value, validate=True)
        if len(current_video_bytes) > 32*1024*1024 or current_video_bytes[4:8] != b'ftyp':
            raise ValueError('32MiB 이하 MP4가 필요합니다.')
        with tempfile.NamedTemporaryFile(suffix='.mp4') as current_temp_file:
            current_temp_file.write(current_video_bytes)
            current_temp_file.flush()
            current_frame_arrays = decode_edit_video(current_temp_file.name, current_request_record['frames'])
        if current_field_name == 'edit_mask':
            if np.max(np.ptp(current_frame_arrays.astype(np.int16), axis=-1)) > 8:
                raise ValueError('편집 마스크는 무채색 영상이어야 합니다.')
            current_edit_pixels = current_frame_arrays.mean(axis=-1) >= 128
            if not current_edit_pixels.any() or current_edit_pixels.all():
                raise ValueError('부분 편집 마스크에는 보존 영역과 편집 영역이 모두 필요합니다.')


def save_edit_inputs(current_job_root, current_request_record, current_input_fields=VACE_EDIT_INPUT_FIELDS):
    current_saved_record = dict(current_request_record)
    for current_field_name in current_input_fields:
        current_video_bytes = base64.b64decode(current_saved_record.pop(current_field_name), validate=True)
        current_file_name = current_field_name.replace('_', '-')+'.mp4'
        (current_job_root/current_file_name).write_bytes(current_video_bytes)
        current_saved_record[current_field_name+'_file'] = current_file_name
        current_saved_record[current_field_name+'_sha256'] = hashlib.sha256(current_video_bytes).hexdigest()
    return current_saved_record


def build_edit_conditions(current_job_root, current_request_record, current_reference_tensor):
    import torch
    current_input_arrays = {}
    for current_field_name in VACE_EDIT_INPUT_FIELDS:
        current_file_name = current_field_name.replace('_', '-')+'.mp4'
        current_input_path = current_job_root/current_file_name
        if current_request_record[current_field_name+'_file'] != current_file_name or hashlib.sha256(current_input_path.read_bytes()).hexdigest() != current_request_record[current_field_name+'_sha256']:
            raise ValueError('편집 입력 파일·해시 불일치')
        current_input_arrays[current_field_name] = decode_edit_video(current_input_path, current_request_record['frames'])
    current_mask_tensor = torch.from_numpy((current_input_arrays['edit_mask'].mean(axis=-1) >= 128).astype(np.float32))
    current_video_tensor = torch.from_numpy(current_input_arrays['edit_video'].astype(np.float32)/255)
    # 공식 pipeline의 정규화 공간 0은 ComfyUI 이미지 공간 0.5에 대응한다.
    current_video_tensor = current_video_tensor*(1-current_mask_tensor[..., None]) + .5*current_mask_tensor[..., None]
    return {'control_video': current_video_tensor, 'control_masks': current_mask_tensor, 'reference_image': current_reference_tensor}
