"""동작 영상에서 공식 Wan 포즈·얼굴 조건을 CUDA로 추출한다."""
from pathlib import Path
import hashlib
import json
import sys
import time
import threading
import traceback

ANIMATE_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
ANIMATE_PREPROCESS_ROOT=ANIMATE_WORKSPACE_ROOT/'.local/wan22-animate/preprocess'
ANIMATE_PREPROCESS_MODELS=ANIMATE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint'


def prepare_animation_conditions(current_job_root,current_attempt_root):
    import numpy as np
    import torch
    import onnxruntime as ort
    import cv2
    import imageio.v2 as imageio
    from PIL import Image,ImageOps
    if not torch.cuda.is_available():
        raise RuntimeError('Animate 전처리에 CUDA가 필요합니다.')
    sys.path.insert(0,str(ANIMATE_PREPROCESS_ROOT))
    from pose2d import Pose2d
    from pose2d_utils import AAPoseMeta
    from human_visualization import draw_aapose_by_meta_new
    from utils import get_face_bboxes
    current_original_session=ort.InferenceSession
    def create_cuda_session(*current_session_args,**current_session_kwargs):
        current_session_kwargs['providers']=[('CUDAExecutionProvider',{'device_id':0})]
        current_cuda_session=current_original_session(*current_session_args,**current_session_kwargs)
        if current_cuda_session.get_providers()[0]!='CUDAExecutionProvider':
            raise RuntimeError('ONNX CUDA 전처리 초기화 실패')
        current_cuda_session.disable_fallback()
        return current_cuda_session
    ort.InferenceSession=create_cuda_session
    torch.zeros(1,device='cuda')
    ort.preload_dlls()
    current_request_record=json.loads((current_job_root/'request.json').read_text())
    current_video_path=current_job_root/'driving.mp4'
    if current_request_record['driving_video_file']!='driving.mp4' or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record['driving_video_sha256']:
        raise ValueError('동작 영상 사본 해시 불일치')
    current_output_root=current_attempt_root/'preprocess'
    current_output_root.mkdir()
    current_pose_detector=Pose2d(str(ANIMATE_PREPROCESS_MODELS/'pose2d/vitpose_h_wholebody.onnx'),str(ANIMATE_PREPROCESS_MODELS/'det/yolov10m.onnx'),device='cuda:0')
    current_pose_frames=[]
    current_face_frames=[]
    current_target_size=(current_request_record['width'],current_request_record['height'])
    with imageio.get_reader(str(current_video_path)) as current_video_reader:
        for current_frame_index,current_frame_array in enumerate(current_video_reader):
            if current_frame_index>=current_request_record['source_frames']:
                raise ValueError('동작 영상 프레임 수가 접수 시 기록과 다릅니다.')
            current_frame_array=np.asarray(ImageOps.pad(Image.fromarray(current_frame_array),current_target_size,color='white'))
            current_pose_record=current_pose_detector([current_frame_array])[0]
            current_face_points=current_pose_record['keypoints_face'][:,:2]
            if not np.isfinite(current_face_points).all():
                raise ValueError(f'얼굴 좌표 검출 실패: {current_frame_index+1}')
            current_left_bound,current_right_bound,current_top_bound,current_bottom_bound=get_face_bboxes(current_face_points,scale=1.3,image_shape=current_frame_array.shape[:2])
            current_face_crop=current_frame_array[current_top_bound:current_bottom_bound,current_left_bound:current_right_bound]
            if not current_face_crop.size:
                raise ValueError(f'얼굴 크롭 추출 실패: {current_frame_index+1}')
            current_face_frames.append(cv2.resize(current_face_crop,(512,512)))
            current_pose_frames.append(draw_aapose_by_meta_new(np.zeros_like(current_frame_array),AAPoseMeta.from_humanapi_meta(current_pose_record)))
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/animate/preprocess {current_frame_index+1}/{current_request_record["source_frames"]}',flush=True)
    if len(current_pose_frames)!=current_request_record['source_frames']:
        raise ValueError('동작 영상 프레임 수 불일치')
    for current_output_name,current_output_frames in [('pose',current_pose_frames),('face',current_face_frames)]:
        imageio.mimwrite(str(current_attempt_root/f'{current_output_name}.mp4'),current_output_frames,fps=current_request_record['fps'],codec='libx264',quality=8,macro_block_size=1)
        # 4n+1 잠재 길이 정렬용 끝 프레임 패딩. 생성 후 원래 길이로 잘라낸다.
        current_output_frames.extend([current_output_frames[-1]]*(current_request_record['frames']-len(current_output_frames)))
        for current_frame_index,current_frame_array in enumerate(current_output_frames):
            Image.fromarray(current_frame_array).save(current_output_root/f'{current_output_name}-{current_frame_index:03d}.png')
    (current_output_root/'metadata.json').write_text(json.dumps({'source_frames':current_request_record['source_frames'],'sampling_frames':current_request_record['frames'],'fps':current_request_record['fps'],'retargeting':'none','reference_resize':'비율 유지 흰색 여백','pose_source':'Wan-Video/Wan2.2 official preprocess','padding':'4n+1 정렬 후 출력에서 제거'},ensure_ascii=False))


if __name__=='__main__':
    current_stop_event=threading.Event()
    def report_preprocess_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/animate/preprocess-heartbeat CUDA 포즈·얼굴 추출 진행 중',flush=True)
    threading.Thread(target=report_preprocess_heartbeat,daemon=True).start()
    try:
        prepare_animation_conditions(Path(sys.argv[1]),Path(sys.argv[2]))
    except BaseException:
        traceback.print_exc()
        raise
    finally:
        current_stop_event.set()
