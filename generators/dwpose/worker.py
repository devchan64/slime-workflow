"""CUDA DWPose 단일 이미지 추출. 원본 좌표와 검출 신뢰도를 보존한다."""
from pathlib import Path
import sys
import json
import hashlib
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from generators.dwpose.contracts import DWPOSE_JOB_STORAGE, validate_fun_pose_assets
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from generators.kimodo.dwpose_runtime import FUN_POSE_MODEL_DIRECTORY, FUN_POSE_MODEL_NAMES, FUN_POSE_MODEL_REVISION, FUN_POSE_SOURCE_REVISION, render_selected_pose_parts


def execute_dwpose_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    import cv2
    import numpy as np
    import torch
    import onnxruntime as ort
    import yaml
    from generators.wan_fun.vendor.videox_fun.dwpose_utils.wholebody import Wholebody
    current_metrics_recorder.update_generation_stage('model-load')
    ort.preload_dlls()
    current_body_detector = Wholebody.__new__(Wholebody)
    for current_session_field, current_model_name in zip(('session_det', 'session_pose'), FUN_POSE_MODEL_NAMES):
        current_session_options = ort.SessionOptions()
        current_session_options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        current_cuda_session = ort.InferenceSession(str((FUN_POSE_MODEL_DIRECTORY/current_model_name).with_suffix('.cuda.onnx')), sess_options=current_session_options, providers=['CUDAExecutionProvider'])
        if current_cuda_session.get_providers()[0] != 'CUDAExecutionProvider':
            raise RuntimeError('DWPose CUDA 초기화 실패')
        current_cuda_session.disable_fallback()
        setattr(current_body_detector, current_session_field, current_cuda_session)
    current_source_path = current_job_root/current_request_record['references'][0]
    current_source_image = cv2.cvtColor(cv2.imread(str(current_source_path)), cv2.COLOR_BGR2RGB)
    current_scaled_height, current_scaled_width = 512, round(832*512/480)
    current_scaled_image = cv2.resize(current_source_image, (current_scaled_width, current_scaled_height), interpolation=cv2.INTER_CUBIC)
    current_padded_image = np.pad(current_scaled_image, ((0, 0), (0, (-current_scaled_width)%64), (0, 0)), mode='edge')
    current_metrics_recorder.update_generation_stage('pose-detection')
    with torch.no_grad():
        current_pose_records = Wholebody.format_result(current_body_detector(np.ascontiguousarray(current_padded_image)))
    if len(current_pose_records) != 1:
        raise ValueError(f'단일 인체 검출 필요: {len(current_pose_records)}명 검출')
    current_pose_image = render_selected_pose_parts(current_pose_records, current_padded_image.shape[:2], current_request_record.get('pose_include_hands', False), current_request_record.get('pose_include_face', False))[:, :current_scaled_width]
    current_pose_image = cv2.resize(current_pose_image, (832, 480), interpolation=cv2.INTER_AREA)
    current_metrics_recorder.update_generation_stage('saving')
    current_frame_hashes = save_video_outputs(current_attempt_root, [current_pose_image], 16)
    current_raw_records = json.loads(json.dumps(current_pose_records, default=lambda current_scalar_value: current_scalar_value.item()))
    current_metadata_record = {'schema_version': 1, 'source_sha256': hashlib.sha256(current_source_path.read_bytes()).hexdigest(), 'image': 'output-000.png', 'image_sha256': current_frame_hashes[0], 'image_size': [832, 480], 'model_revision': FUN_POSE_MODEL_REVISION, 'source_revision': FUN_POSE_SOURCE_REVISION, 'backend': 'ONNX Runtime CUDA; CPU fallback disabled', 'scale_percent': 100, 'pose_include_hands': current_request_record.get('pose_include_hands', False), 'pose_include_face': current_request_record.get('pose_include_face', False), 'coordinate_system': 'poses: 검출 입력 픽셀 좌표; body_keypoints: 원본 832×480 픽셀 좌표', 'padded_size': [current_padded_image.shape[1], current_padded_image.shape[0]], 'scaled_size': [current_scaled_width, current_scaled_height], 'poses': current_raw_records}
    current_metadata_record['body_keypoints'] = [None if current_body_point is None else {'x': float(current_body_point.x)*832/current_scaled_width, 'y': float(current_body_point.y)*480/current_scaled_height, 'score': float(current_body_point.score), 'id': int(current_body_point.id)} for current_body_point in current_pose_records[0].body.keypoints]
    (current_attempt_root/'keypoints.yaml').write_text(yaml.safe_dump(current_metadata_record, allow_unicode=True, sort_keys=False))
    with zipfile.ZipFile(current_attempt_root/'frames.zip', 'a') as current_output_archive:
        current_output_archive.write(current_attempt_root/'keypoints.yaml', 'keypoints.yaml')
    return {'attempt': current_attempt_root.name, 'frames': 1, 'frame_hashes': current_frame_hashes, 'keypoints': 'keypoints.yaml'}


if __name__ == '__main__':
    run_reference_video_worker(DWPOSE_JOB_STORAGE, Path(__file__), validate_fun_pose_assets, execute_dwpose_inference)
