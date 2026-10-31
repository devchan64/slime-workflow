"""선택 참조 이미지의 BODY18 검출을 별도 CUDA 프로세스에서 수행한다."""
from pathlib import Path
import sys,json,threading,time

REFERENCE_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REFERENCE_WORKSPACE_ROOT))


def validate_reference_pose_runtime():
    import subprocess
    current_runtime_root=REFERENCE_WORKSPACE_ROOT/'.local/wan22-animate'
    current_model_root=REFERENCE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint'
    for current_required_path in (REFERENCE_WORKSPACE_ROOT/'.venv/bin/python',current_runtime_root/'preprocess/pose2d.py',current_runtime_root/'preprocess-deps/onnxruntime/__init__.py',current_model_root/'det/yolov10m.onnx'):
        if not current_required_path.is_file():
            raise ValueError(f'참조 포즈 추출 준비 누락: {current_required_path}')
    current_check_result=subprocess.run([str(REFERENCE_WORKSPACE_ROOT/'.venv/bin/python'),str(REFERENCE_WORKSPACE_ROOT/'generators/wan_animate/model_validation.py'),str(current_model_root/'pose2d/vitpose_h_wholebody.onnx')],capture_output=True,text=True,timeout=30)
    if current_check_result.returncode:
        raise ValueError('참조 포즈 모델 검사 실패: '+current_check_result.stderr)


def extract_reference_body_proportions(current_job_root,current_attempt_root):
    validate_reference_pose_runtime()
    import numpy as np
    import torch,onnxruntime as ort
    from PIL import Image,ImageOps
    from generators.kimodo.reference_proportions import estimate_reference_proportions
    from generators.kimodo.pose_rendering import render_body_pose_image
    if not torch.cuda.is_available(): raise RuntimeError('참조 포즈 추출에는 CUDA가 필요합니다.')
    torch.zeros(1,device='cuda')
    ort.preload_dlls()
    current_session_constructor=ort.InferenceSession
    def create_reference_cuda_session(*current_session_args,**current_session_kwargs):
        current_session_kwargs['providers']=[('CUDAExecutionProvider',{'device_id':0})]
        current_session_value=current_session_constructor(*current_session_args,**current_session_kwargs)
        if current_session_value.get_providers()[0]!='CUDAExecutionProvider': raise RuntimeError('참조 포즈 CUDA 초기화 실패')
        current_session_value.disable_fallback()
        return current_session_value
    ort.InferenceSession=create_reference_cuda_session
    sys.path.insert(0,str(REFERENCE_WORKSPACE_ROOT/'.local/wan22-animate/preprocess'))
    from pose2d import Pose2d
    from pose2d_utils import load_pose_metas_from_kp2ds_seq
    current_model_root=REFERENCE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint'
    current_pose_detector=Pose2d(str(current_model_root/'pose2d/vitpose_h_wholebody.onnx'),str(current_model_root/'det/yolov10m.onnx'),device='cuda:0')
    current_request_record=json.loads((current_job_root/'request.json').read_text())
    current_reference_records=[]
    current_observation_sources=[]
    for current_reference_index,current_reference_name in enumerate(current_request_record['references'],1):
        with Image.open(current_job_root/current_reference_name) as current_image_value:
            current_image_value=ImageOps.exif_transpose(current_image_value).convert('RGB')
            current_image_value.thumbnail((1536,1536))
            current_image_array=np.asarray(current_image_value)
        # 문자열 경로는 파일 BGR→RGB 처리를 사용하고 배열 API의 색상 재반전을 피한다.
        current_rgb_path=current_attempt_root/f'reference-normalized-{current_reference_index}.png'
        Image.fromarray(current_image_array).save(current_rgb_path)
        # 최대 인물 하나를 고르는 상위 API 대신 모든 검출 상자를 개별 추정한다.
        current_detector_image,current_detector_shape=current_pose_detector.detector.preprocess(current_image_array)
        current_detector_outputs=current_pose_detector.detector.session.run(None,{current_pose_detector.detector.session.get_inputs()[0].name:current_detector_image[None]})[0]
        current_detection_boxes=current_pose_detector.detector.postprocess(current_detector_outputs[0],current_detector_shape,cat_id=current_pose_detector.detector.cat_id)
        current_person_boxes=[current_box_values for current_box_values in current_detection_boxes if int(current_box_values[-1])+1 in current_pose_detector.detector.cat_id and current_box_values[-2]>=0.5]
        current_person_boxes.sort(key=lambda current_box_values:(float(current_box_values[1]),float(current_box_values[0])))
        if not current_person_boxes:
            raise ValueError(f'참조 {current_reference_index}: 신뢰도 0.5 이상의 인물 검출 없음')
        for current_person_index,current_person_box in enumerate(current_person_boxes,1):
            current_pose_input,current_pose_center,current_pose_scale=current_pose_detector.model.preprocess(current_image_array,current_person_box[:5])
            current_pose_keypoints=current_pose_detector.model(current_pose_input[None],current_pose_center[None],current_pose_scale[None])
            current_pose_record=load_pose_metas_from_kp2ds_seq(current_pose_keypoints,width=current_image_array.shape[1],height=current_image_array.shape[0])[0]
            current_body_points=np.asarray(current_pose_record['keypoints_body'][:18],dtype=float).copy()
            current_body_points[:,:2]*=np.array([current_image_array.shape[1],current_image_array.shape[0]])
            current_reference_records.append(current_body_points)
            current_observation_sources.append({'observation':len(current_reference_records),'image':current_reference_index,'person':current_person_index,'bbox':current_person_box[:4].tolist(),'confidence':float(current_person_box[-2])})
            current_preview_points=current_body_points.copy()
            current_preview_points[:,:2]*=512/max(current_image_array.shape[:2])
            render_body_pose_image(current_preview_points).save(current_attempt_root/f'reference-pose-{current_reference_index}-{current_person_index}.png')
        print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/kimodo/reference {current_reference_index}/{len(current_request_record["references"])}',flush=True)
    current_ratio_record=estimate_reference_proportions(current_reference_records)
    current_ratio_record['observation_sources']=current_observation_sources
    current_ratio_record['image_count']=len(current_request_record['references'])
    current_ratio_record['keypoints']=[current_point_values.tolist() for current_point_values in current_reference_records]
    (current_attempt_root/'reference-proportions.json').write_text(json.dumps(current_ratio_record,ensure_ascii=False,indent=2))


if __name__=='__main__':
    current_stop_event=threading.Event()
    def report_reference_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/kimodo/reference-heartbeat CUDA 포즈 추출 중',flush=True)
    threading.Thread(target=report_reference_heartbeat,daemon=True).start()
    try:
        extract_reference_body_proportions(Path(sys.argv[1]),Path(sys.argv[2]))
    finally:
        current_stop_event.set()
