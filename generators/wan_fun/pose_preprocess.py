"""VideoX-Fun DWPose 원본과 CUDA ONNX 세션을 연결한다."""
from pathlib import Path
import hashlib
import json
import sys
import time

FUN_POSE_SOURCE_REVISION = '13bb3c625e8b1e457d7124d92207b49e00e4a6fe'
FUN_POSE_MODEL_REVISION = '1a7144101628d69ee7a3768d1ee3a094070dc388'
FUN_POSE_MODEL_DIRECTORY = Path(__file__).resolve().parents[2]/'.model/wan22-fun-pose'
FUN_POSE_MODEL_NAMES = ('yolox_l.onnx', 'dw-ll_ucoco_384.onnx')


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


def prepare_fun_pose_frames(current_job_root, current_attempt_root, current_request_record):
    import cv2
    import numpy as np
    import torch
    import onnxruntime as ort
    import imageio.v2 as imageio
    from PIL import Image, ImageOps
    from generators.wan_fun.vendor.videox_fun.dwpose_utils import DWposeDetector
    from generators.wan_fun.vendor.videox_fun.dwpose_utils.wholebody import Wholebody
    validate_fun_pose_assets()
    if not torch.cuda.is_available():
        raise RuntimeError('VideoX-Fun 포즈 추출에는 CUDA가 필요합니다.')
    torch.zeros(1, device='cuda')
    ort.preload_dlls()
    current_source_path = current_job_root/'driving.mp4'
    if current_request_record['driving_video_file'] != 'driving.mp4' or hashlib.sha256(current_source_path.read_bytes()).hexdigest() != current_request_record['driving_video_sha256']:
        raise ValueError('SOMA 입력 영상 사본 해시 불일치')
    # 공식 Wholebody의 OpenCV CPU 초기화만 우회한다. 공식 ONNX 추론 분기를 사용한다.
    current_body_detector = Wholebody.__new__(Wholebody)
    for current_session_field, current_model_name in zip(('session_det', 'session_pose'), FUN_POSE_MODEL_NAMES):
        current_session_options = ort.SessionOptions()
        current_session_options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        current_cuda_session = ort.InferenceSession(str((FUN_POSE_MODEL_DIRECTORY/current_model_name).with_suffix('.cuda.onnx')), sess_options=current_session_options, providers=['CUDAExecutionProvider'])
        if current_cuda_session.get_providers()[0] != 'CUDAExecutionProvider':
            raise RuntimeError('VideoX-Fun ONNX CUDA 초기화 실패')
        current_cuda_session.disable_fallback()
        setattr(current_body_detector, current_session_field, current_cuda_session)
    current_pose_detector = DWposeDetector.__new__(DWposeDetector)
    current_pose_detector.pose_estimation = current_body_detector
    current_frame_paths = []
    current_video_capture = cv2.VideoCapture(str(current_source_path))
    current_source_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
    current_output_directory = current_attempt_root/'pose-frames'
    current_output_directory.mkdir()
    try:
        with imageio.get_writer(str(current_attempt_root/'pose.mp4'), fps=16, codec='libx264', quality=8, macro_block_size=1) as current_video_writer:
            for current_frame_index in range(current_request_record['frames']):
                # 30fps SOMA의 시간축을 16fps 출력에 맞춘다. 끝 프레임 복제는 하지 않는다.
                current_video_capture.set(cv2.CAP_PROP_POS_FRAMES, round(current_frame_index*current_source_fps/16))
                current_frame_ready, current_frame_array = current_video_capture.read()
                if not current_frame_ready:
                    raise ValueError(f'SOMA 영상 길이 부족: 출력 {current_frame_index+1}프레임')
                current_frame_array = cv2.cvtColor(current_frame_array, cv2.COLOR_BGR2RGB)
                # 공식 VideoToPose.process_frame: 짧은 변 512, 64배수 edge padding, 검출 후 padding 제거.
                current_resize_ratio = 512/min(current_frame_array.shape[:2])
                current_scaled_height, current_scaled_width = [round(current_dimension_value*current_resize_ratio) for current_dimension_value in current_frame_array.shape[:2]]
                current_scaled_image = cv2.resize(current_frame_array, (current_scaled_width, current_scaled_height), interpolation=cv2.INTER_CUBIC if current_resize_ratio>1 else cv2.INTER_AREA)
                current_padded_image = np.pad(current_scaled_image, ((0, (-current_scaled_height)%64), (0, (-current_scaled_width)%64), (0, 0)), mode='edge')
                current_pose_image = current_pose_detector(np.ascontiguousarray(current_padded_image))[:current_scaled_height, :current_scaled_width]
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
    (current_attempt_root/'pose-preprocess.json').write_text(json.dumps({'source': 'VideoX-Fun VideoToPose / DWposeDetector', 'revision': FUN_POSE_SOURCE_REVISION, 'model_revision': FUN_POSE_MODEL_REVISION, 'backend': 'ONNX Runtime CUDA; CPU fallback disabled', 'source_fps': current_source_fps, 'output_fps': 16, 'frames': current_frame_paths}, ensure_ascii=False))
    return current_frame_paths


if __name__ == '__main__':
    import threading
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    current_stop_event = threading.Event()
    def report_pose_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/fun/pose-heartbeat VideoX-Fun CUDA 전처리 중', flush=True)
    threading.Thread(target=report_pose_heartbeat, daemon=True).start()
    try:
        current_job_directory = Path(sys.argv[1])
        prepare_fun_pose_frames(current_job_directory, Path(sys.argv[2]), json.loads((current_job_directory/'request.json').read_text()))
    finally:
        current_stop_event.set()
