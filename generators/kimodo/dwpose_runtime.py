"""VideoX-Fun DWPose 원본과 ROCm ONNX 세션을 연결한다."""
from pathlib import Path
import hashlib
import json
import sys
import time

FUN_POSE_SOURCE_REVISION = '13bb3c625e8b1e457d7124d92207b49e00e4a6fe'
FUN_POSE_MODEL_REVISION = '1a7144101628d69ee7a3768d1ee3a094070dc388'
FUN_POSE_MODEL_DIRECTORY = Path(__file__).resolve().parents[2]/'.model/wan22-fun-pose'
FUN_POSE_MODEL_NAMES = ('yolox_l.onnx', 'dw-ll_ucoco_384.onnx')


class MigraphxPoseInferenceSession:
    """MIGraphX가 반환한 SimCC 축을 입력 크기에 맞춰 확인한다."""
    def __init__(self, current_session_instance):
        self.current_session_instance = current_session_instance

    def get_inputs(self):
        return self.current_session_instance.get_inputs()

    def run(self, current_output_names, current_input_values):
        current_output_values = self.current_session_instance.run(current_output_names, current_input_values)
        if len(current_output_values) != 2:
            raise ValueError('DWPose SimCC 출력 개수가 올바르지 않습니다.')
        if (current_output_values[0].shape[-1], current_output_values[1].shape[-1]) == (768, 576):
            current_output_values = [current_output_values[1], current_output_values[0]]
        if (current_output_values[0].shape[-1], current_output_values[1].shape[-1]) != (576, 768):
            raise ValueError('DWPose SimCC 출력 크기가 올바르지 않습니다.')
        return current_output_values


def validate_fun_pose_assets():
    current_prepared_record = json.loads((FUN_POSE_MODEL_DIRECTORY/'prepared.json').read_text())
    if current_prepared_record.get('revision') != FUN_POSE_MODEL_REVISION:
        raise ValueError('VideoX-Fun 포즈 모델 리비전 불일치')
    for current_model_name in FUN_POSE_MODEL_NAMES:
        current_model_path = (FUN_POSE_MODEL_DIRECTORY/current_model_name).with_suffix('.cuda.onnx')
        with current_model_path.open('rb') as current_model_stream:
            current_model_hash = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
        if current_prepared_record.get('files', {}).get(current_model_path.name) != current_model_hash:
            raise ValueError(f'VideoX-Fun CUDA 모델 해시 불일치: {current_model_path}')


def render_selected_pose_parts(current_pose_records, current_image_shape, current_include_hands, current_include_face):
    """몸 18점은 유지하고 공식 렌더러에 전달할 손·얼굴 상세만 선택한다."""
    from generators.wan_fun.vendor.videox_fun.dwpose_utils import draw_pose
    current_selected_records = [current_pose_record._replace(
        left_hand=current_pose_record.left_hand if current_include_hands else None,
        right_hand=current_pose_record.right_hand if current_include_hands else None,
        face=current_pose_record.face if current_include_face else None,
    ) for current_pose_record in current_pose_records]
    return draw_pose(current_selected_records, *current_image_shape)


def prepare_fun_pose_frames(current_job_root, current_attempt_root, current_request_record, current_pose_transform=None, current_output_fps=16):
    import cv2
    import numpy as np
    import torch
    import onnxruntime as ort
    import imageio.v2 as imageio
    from PIL import Image, ImageOps
    from generators.wan_fun.vendor.videox_fun.dwpose_utils.wholebody import Wholebody
    validate_fun_pose_assets()
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('VideoX-Fun 포즈 추출에는 AMD ROCm GPU가 필요합니다.')
    torch.zeros(1, device='cuda')
    import migraphx
    import onnxruntime_ep_migraphx as current_provider_plugin
    for current_provider_name, current_library_path in zip(current_provider_plugin.get_ep_names(), current_provider_plugin.get_library_paths()):
        if current_provider_name not in ort.get_available_providers():
            ort.register_execution_provider_library(current_provider_name, current_library_path)
    if 'MIGraphXExecutionProvider' not in ort.get_available_providers():
        raise RuntimeError('ONNX Runtime MIGraphX 실행 공급자를 사용할 수 없습니다.')
    current_gpu_devices = [current_device_record for current_device_record in ort.get_ep_devices()
                           if current_device_record.ep_name == 'MIGraphXExecutionProvider'
                           and current_device_record.device.type == ort.OrtHardwareDeviceType.GPU]
    if not current_gpu_devices:
        raise RuntimeError('MIGraphX에서 AMD GPU 장치를 찾지 못했습니다.')
    current_source_path = current_job_root/'driving.mp4'
    if current_request_record['driving_video_file'] != 'driving.mp4' or hashlib.sha256(current_source_path.read_bytes()).hexdigest() != current_request_record['driving_video_sha256']:
        raise ValueError('SOMA 입력 영상 사본 해시 불일치')
    # 공식 Wholebody의 OpenCV CPU 초기화만 우회한다. 공식 ONNX 추론 분기를 사용한다.
    current_body_detector = Wholebody.__new__(Wholebody)
    for current_session_field, current_model_name in zip(('session_det', 'session_pose'), FUN_POSE_MODEL_NAMES):
        current_session_options = ort.SessionOptions()
        current_session_options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        current_session_options.add_provider_for_devices(current_gpu_devices[:1], {})
        current_gpu_session = ort.InferenceSession(str((FUN_POSE_MODEL_DIRECTORY/current_model_name).with_suffix('.cuda.onnx')), sess_options=current_session_options)
        if current_gpu_session.get_providers()[0] != 'MIGraphXExecutionProvider':
            raise RuntimeError('VideoX-Fun ONNX MIGraphX 초기화 실패')
        current_gpu_session.disable_fallback()
        if current_session_field == 'session_pose':
            current_gpu_session = MigraphxPoseInferenceSession(current_gpu_session)
        setattr(current_body_detector, current_session_field, current_gpu_session)
    # 과거 기록은 손·얼굴 포함으로 재개한다. 신규 요청은 검증 시 False를 저장한다.
    current_include_hands = current_request_record.get('pose_include_hands', True)
    current_include_face = current_request_record.get('pose_include_face', True)
    current_frame_paths = []
    current_video_capture = cv2.VideoCapture(str(current_source_path))
    current_source_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
    current_output_directory = current_attempt_root/'pose-frames'
    current_output_directory.mkdir()
    current_detected_frames = []
    try:
        for current_frame_index in range(current_request_record['frames']):
            current_video_capture.set(cv2.CAP_PROP_POS_FRAMES, round(current_frame_index*current_source_fps/current_output_fps))
            current_frame_ready, current_frame_array = current_video_capture.read()
            if not current_frame_ready:
                raise ValueError('SOMA 영상 길이 부족')
            current_frame_array = cv2.cvtColor(current_frame_array, cv2.COLOR_BGR2RGB)
            current_resize_ratio = 512/min(current_frame_array.shape[:2])
            current_scaled_height, current_scaled_width = [round(current_dimension_value*current_resize_ratio) for current_dimension_value in current_frame_array.shape[:2]]
            current_scaled_image = cv2.resize(current_frame_array, (current_scaled_width, current_scaled_height), interpolation=cv2.INTER_CUBIC if current_resize_ratio>1 else cv2.INTER_AREA)
            current_padded_image = np.pad(current_scaled_image, ((0, (-current_scaled_height)%64), (0, (-current_scaled_width)%64), (0, 0)), mode='edge')
            with torch.no_grad():
                current_pose_records = Wholebody.format_result(current_body_detector(np.ascontiguousarray(current_padded_image)))
            if len(current_pose_records) != 1:
                raise ValueError(f'단일 인체 검출 필요: {current_frame_index+1}프레임')
            current_detected_frames.append(current_pose_records)
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/kimodo/dwpose-detect {current_frame_index+1}/{current_request_record["frames"]}', flush=True)
        (current_attempt_root/'pose-keypoints-raw.json').write_text(json.dumps(current_detected_frames,default=lambda current_scalar_value:current_scalar_value.item()))
        if current_pose_transform is not None:
            current_detected_frames = current_pose_transform(current_detected_frames, current_padded_image.shape[:2])
        (current_attempt_root/'pose-keypoints-adjusted.json').write_text(json.dumps(current_detected_frames,default=lambda current_scalar_value:current_scalar_value.item()))
        with imageio.get_writer(str(current_attempt_root/'pose.mp4'), fps=current_output_fps, codec='libx264', quality=8, macro_block_size=1) as current_video_writer:
            for current_frame_index in range(current_request_record['frames']):
                current_pose_records = current_detected_frames[current_frame_index]
                current_pose_image = render_selected_pose_parts(current_pose_records, current_padded_image.shape[:2], current_include_hands, current_include_face)[:current_scaled_height, :current_scaled_width]
                if not np.any(current_pose_image):
                    raise ValueError(f'VideoX-Fun 인체 검출 실패: {current_frame_index+1}프레임. 단일 SOMA 인체가 보이는 영상을 입력하세요.')
                current_output_image = ImageOps.pad(Image.fromarray(current_pose_image), (832, 480), color='black')
                current_frame_path = current_output_directory/f'pose-{current_frame_index:03d}.png'
                current_output_image.save(current_frame_path)
                current_frame_paths.append(str(current_frame_path))
                current_video_writer.append_data(np.asarray(current_output_image))
                print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/fun/pose {current_frame_index+1}/{current_request_record["frames"]}', flush=True)
    finally:
        current_video_capture.release()
    (current_attempt_root/'pose-preprocess.json').write_text(json.dumps({'source': 'VideoX-Fun VideoToPose / DWposeDetector', 'revision': FUN_POSE_SOURCE_REVISION, 'model_revision': FUN_POSE_MODEL_REVISION, 'backend': 'ONNX Runtime MIGraphX; CPU fallback disabled', 'source_fps': current_source_fps, 'output_fps': current_output_fps, 'pose_include_hands': current_include_hands, 'pose_include_face': current_include_face, 'body_head_points': True, 'frames': current_frame_paths}, ensure_ascii=False))
    return current_frame_paths


if __name__ == '__main__':
    import threading
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    current_stop_event = threading.Event()
    def report_pose_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/fun/pose-heartbeat VideoX-Fun ROCm 전처리 중', flush=True)
    threading.Thread(target=report_pose_heartbeat, daemon=True).start()
    try:
        current_job_directory = Path(sys.argv[1])
        prepare_fun_pose_frames(current_job_directory, Path(sys.argv[2]), json.loads((current_job_directory/'request.json').read_text()))
    finally:
        current_stop_event.set()
