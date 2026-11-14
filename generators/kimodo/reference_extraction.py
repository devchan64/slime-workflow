"""선택 참조 이미지의 BODY18 검출을 별도 ROCm 프로세스에서 수행한다."""
from pathlib import Path
import hashlib
import os
import sys,json,threading,time

REFERENCE_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REFERENCE_WORKSPACE_ROOT))
REFERENCE_PERSON_DETECTION_THRESHOLD=0.2


def normalize_reference_keypoints(current_body_points):
    """ViTPose의 비확률 heatmap 최대값을 렌더링용 0~1 점수로 제한한다."""
    import numpy as np
    current_point_values=np.asarray(current_body_points,dtype=float)
    if current_point_values.shape!=(18,3) or not np.isfinite(current_point_values).all():
        raise ValueError('참조 BODY18 좌표 또는 원시 heatmap 점수가 유효하지 않습니다.')
    current_normalized_points=current_point_values.copy()
    current_normalized_points[:,2]=np.clip(current_normalized_points[:,2],0,1)
    return current_normalized_points


def validate_reference_pose_runtime():
    from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON
    from generators.kimodo.prepare_reference_pose import REFERENCE_MODEL_REVISION, REFERENCE_MODEL_ROOT
    current_source_root = REFERENCE_WORKSPACE_ROOT/'.local/wan-reference-source/wan/modules/animate/preprocess'
    current_model_root = REFERENCE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint'
    for current_required_path in (KIMODO_ENVIRONMENT_PYTHON, current_source_root/'pose2d.py', current_source_root/'pose2d_utils.py', current_model_root/'det/yolov10m.onnx', current_model_root/'pose2d/vitpose_h_wholebody.onnx/end2end-rocm.onnx'):
        if not current_required_path.is_file():
            raise ValueError(f'참조 포즈 추출 준비 누락: {current_required_path}')
    current_manifest_path=REFERENCE_MODEL_ROOT/'prepared-reference.json'
    try:
        current_manifest_record=json.loads(current_manifest_path.read_text())
        if current_manifest_record['revision']!=REFERENCE_MODEL_REVISION or len(current_manifest_record['files'])!=395:
            raise ValueError('참조 포즈 준비 기록 불일치')
        for current_file_name,current_file_record in current_manifest_record['files'].items():
            current_file_path=(REFERENCE_MODEL_ROOT/current_file_name).resolve()
            if not current_file_path.is_relative_to(REFERENCE_MODEL_ROOT.resolve()) or current_file_path.stat().st_size!=current_file_record['size']:
                raise ValueError(f'참조 포즈 파일 누락 또는 크기 불일치: {current_file_name}')
    except (OSError,KeyError,TypeError,ValueError) as current_manifest_error:
        raise ValueError('참조 포즈 파일 준비 필요: python -m generators.kimodo.prepare_reference_pose') from current_manifest_error


def extract_reference_body_proportions(current_job_root,current_attempt_root):
    validate_reference_pose_runtime()
    import numpy as np
    import torch,onnxruntime as ort
    from PIL import Image,ImageOps
    from generators.kimodo.reference_proportions import estimate_reference_proportions
    from generators.kimodo.pose_rendering import render_body_pose_image
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('참조 포즈 추출에는 AMD ROCm GPU가 필요합니다.')
    import migraphx
    import onnxruntime_ep_migraphx as current_provider_plugin
    for current_provider_name,current_library_path in zip(current_provider_plugin.get_ep_names(),current_provider_plugin.get_library_paths()):
        if current_provider_name not in ort.get_available_providers():
            ort.register_execution_provider_library(current_provider_name,current_library_path)
    current_gpu_devices=[current_device_record for current_device_record in ort.get_ep_devices() if current_device_record.ep_name=='MIGraphXExecutionProvider' and current_device_record.device.type==ort.OrtHardwareDeviceType.GPU]
    if not current_gpu_devices:
        raise RuntimeError('참조 포즈 MIGraphX GPU 장치를 찾지 못했습니다.')
    from types import SimpleNamespace
    def create_reference_rocm_session(current_model_path, **current_session_options):
        current_options=ort.SessionOptions()
        current_options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        current_options.add_provider_for_devices(current_gpu_devices[:1],{})
        current_session=ort.InferenceSession(current_model_path,sess_options=current_options)
        if current_session.get_providers()[0]!='MIGraphXExecutionProvider':
            raise RuntimeError('참조 포즈 MIGraphX 초기화 실패')
        current_session.disable_fallback()
        return current_session
    sys.path.insert(0,str(REFERENCE_WORKSPACE_ROOT/'.local/wan-reference-source/wan/modules/animate/preprocess'))
    import pose2d
    from pose2d_utils import load_pose_metas_from_kp2ds_seq
    pose2d.onnxruntime=SimpleNamespace(InferenceSession=create_reference_rocm_session)
    current_model_root=REFERENCE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint'
    current_pose_detector=pose2d.Pose2d(str(current_model_root/'pose2d/vitpose_h_wholebody.onnx/end2end-rocm.onnx'),str(current_model_root/'det/yolov10m.onnx'),device='cuda:0')
    current_request_record=json.loads((current_job_root/'request.json').read_text())
    current_reference_records=[]
    current_original_records=[]
    current_observation_sources=[]
    current_pending_edits=list(current_request_record.get('proportion_joint_edits',[]))
    current_applied_edits=[]
    for current_reference_index,current_reference_name in enumerate(current_request_record['references'],1):
        with Image.open(current_job_root/current_reference_name) as current_image_value:
            current_image_value=ImageOps.exif_transpose(current_image_value).convert('RGB')
            current_image_value.thumbnail((1536,1536))
            current_image_array=np.asarray(current_image_value)
        # 문자열 경로는 파일 BGR→RGB 처리를 사용하고 배열 API의 색상 재반전을 피한다.
        current_rgb_path=current_attempt_root/f'reference-normalized-{current_reference_index}.png'
        Image.fromarray(current_image_array).save(current_rgb_path)
        current_image_digest=hashlib.sha256((current_job_root/current_reference_name).read_bytes()).hexdigest()
        # 최대 인물 하나를 고르는 상위 API 대신 모든 검출 상자를 개별 추정한다.
        current_detector_image,current_detector_shape=current_pose_detector.detector.preprocess(current_image_array)
        current_detector_outputs=current_pose_detector.detector.session.run(None,{current_pose_detector.detector.session.get_inputs()[0].name:current_detector_image[None]})[0]
        current_detection_boxes=current_pose_detector.detector.postprocess(current_detector_outputs[0],current_detector_shape,cat_id=current_pose_detector.detector.cat_id)
        current_person_boxes=[current_box_values for current_box_values in current_detection_boxes if int(current_box_values[-1])+1 in current_pose_detector.detector.cat_id and current_box_values[-2]>=REFERENCE_PERSON_DETECTION_THRESHOLD]
        current_person_boxes.sort(key=lambda current_box_values:(float(current_box_values[1]),float(current_box_values[0])))
        if not current_person_boxes:
            raise ValueError(f'참조 {current_reference_index}: 유효한 인물 검출 없음')
        for current_person_index,current_person_box in enumerate(current_person_boxes,1):
            current_pose_input,current_pose_center,current_pose_scale=current_pose_detector.model.preprocess(current_image_array,current_person_box[:5])
            current_pose_keypoints=current_pose_detector.model(current_pose_input[None],current_pose_center[None],current_pose_scale[None])
            current_pose_record=load_pose_metas_from_kp2ds_seq(current_pose_keypoints,width=current_image_array.shape[1],height=current_image_array.shape[0])[0]
            current_body_points=np.asarray(current_pose_record['keypoints_body'][:18],dtype=float).copy()
            current_body_points[:,:2]*=np.array([current_image_array.shape[1],current_image_array.shape[0]])
            current_raw_scores=current_body_points[:,2].tolist()
            if os.environ.get('KIMODO_REFERENCE_DIAGNOSTICS') == '1':
                print('참조 관절 원시값',current_reference_index,current_person_index,current_person_box[:5].tolist(),current_body_points.tolist(),flush=True)
            current_body_points=normalize_reference_keypoints(current_body_points)
            current_original_records.append(current_body_points.copy())
            current_person_edits=[current_edit for current_edit in current_pending_edits if current_edit['image']==current_reference_index and current_edit['person']==current_person_index]
            if current_person_edits:
                if any(current_edit['image_sha256']!=current_image_digest for current_edit in current_person_edits):
                    raise ValueError('관절 수정 대상 참조 이미지가 변경되었습니다.')
                from generators.kimodo.reference_joint_edits import apply_reference_joint_edits
                current_body_points,current_evidence=apply_reference_joint_edits(current_body_points,[{current_key:current_edit[current_key] for current_key in ('joint','original','edited')} for current_edit in current_person_edits],(current_image_array.shape[1],current_image_array.shape[0]))
                current_applied_edits.extend([{'image':current_reference_index,'person':current_person_index,'image_sha256':current_image_digest,**current_item} for current_item in current_evidence])
                for current_edit in current_person_edits: current_pending_edits.remove(current_edit)
            current_reference_records.append(current_body_points)
            current_observation_sources.append({'observation':len(current_reference_records),'image':current_reference_index,'person':current_person_index,'bbox':current_person_box[:4].tolist(),'confidence':float(current_person_box[-2]),'raw_heatmap_scores':current_raw_scores})
            current_preview_points=current_body_points.copy()
            current_preview_points[:,:2]*=512/max(current_image_array.shape[:2])
            render_body_pose_image(current_preview_points).save(current_attempt_root/f'reference-pose-{current_reference_index}-{current_person_index}.png')
        print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/kimodo/reference {current_reference_index}/{len(current_request_record["references"])}',flush=True)
    if current_pending_edits:
        raise ValueError('수정할 참조 인물을 찾을 수 없습니다.')
    current_observation_heights=[float(current_source_record['bbox'][3]-current_source_record['bbox'][1]) for current_source_record in current_observation_sources]
    current_ratio_record=estimate_reference_proportions(current_reference_records,current_observation_heights)
    current_ratio_record['confidence_policy']='ViTPose heatmap 최대값은 확률이 아님. 원시값 보존, 추정·렌더 점수는 [0,1] 제한.'
    current_ratio_record['observation_sources']=current_observation_sources
    current_ratio_record['image_count']=len(current_request_record['references'])
    current_ratio_record['keypoints']=[current_point_values.tolist() for current_point_values in current_reference_records]
    current_ratio_record['original_keypoints']=[current_point_values.tolist() for current_point_values in current_original_records]
    current_ratio_record['manual_joint_edits']=current_applied_edits
    current_ratio_record['reference_image_sha256']=[hashlib.sha256((current_job_root/current_reference_name).read_bytes()).hexdigest() for current_reference_name in current_request_record['references']]
    if 'proportion_reviewed_multiview' in current_request_record:
        from generators.kimodo.multiview_reviewed_bundle import apply_reviewed_multiview_bundle
        current_ratio_record=apply_reviewed_multiview_bundle(current_ratio_record,current_request_record['proportion_reviewed_multiview'],current_ratio_record['reference_image_sha256'])
    elif 'proportion_multiview_angles' in current_request_record:
        from generators.kimodo.multiview_reference_experiment import fit_multiview_reference
        current_multiview_record=fit_multiview_reference(current_ratio_record,current_request_record['proportion_multiview_angles'])
        current_ratio_record['baseline_2d_ratios']=current_ratio_record['ratios']
        current_ratio_record['ratios']=current_multiview_record['ratios']
        current_ratio_record['multiview_experiment']=current_multiview_record
        current_ratio_record['method']='시험: 8방향 공통 3D 관절 정사영 맞춤; 코·어깨 축은 기존 2D 방식 유지'
    (current_attempt_root/'reference-proportions.json').write_text(json.dumps(current_ratio_record,ensure_ascii=False,indent=2))


if __name__=='__main__':
    current_stop_event=threading.Event()
    def report_reference_heartbeat():
        while not current_stop_event.wait(5):
            print(time.strftime('%Y-%m-%dT%H:%M:%S')+'/kimodo/reference-heartbeat ROCm 포즈 추출 중',flush=True)
    threading.Thread(target=report_reference_heartbeat,daemon=True).start()
    try:
        extract_reference_body_proportions(Path(sys.argv[1]),Path(sys.argv[2]))
    finally:
        current_stop_event.set()
