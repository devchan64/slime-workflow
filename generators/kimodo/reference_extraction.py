"""선택 참조 이미지의 BODY18 검출을 별도 ROCm 프로세스에서 수행한다."""
from pathlib import Path
import hashlib
import sys,json,threading,time

REFERENCE_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REFERENCE_WORKSPACE_ROOT))
REFERENCE_PERSON_DETECTION_THRESHOLD=0.2


def normalize_reference_keypoints(current_body_points):
    """DWPose의 비확률 관절 최대값을 렌더링용 0~1 점수로 제한한다."""
    import numpy as np
    current_point_values=np.asarray(current_body_points,dtype=float)
    if current_point_values.shape!=(18,3) or not np.isfinite(current_point_values).all():
        raise ValueError('참조 BODY18 좌표 또는 원시 관절 점수가 유효하지 않습니다.')
    current_normalized_points=current_point_values.copy()
    current_normalized_points[:,2]=np.clip(current_normalized_points[:,2],0,1)
    return current_normalized_points


def validate_reference_pose_runtime():
    from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON
    from generators.kimodo.dwpose_runtime import validate_fun_pose_assets
    if not KIMODO_ENVIRONMENT_PYTHON.is_file():
        raise ValueError('Kimodo ROCm 실행 환경을 준비하세요.')
    validate_fun_pose_assets()


def extract_reference_body_proportions(current_job_root,current_attempt_root):
    validate_reference_pose_runtime()
    import numpy as np
    from PIL import Image,ImageOps
    from generators.kimodo.reference_proportions import estimate_reference_proportions
    from generators.kimodo.pose_rendering import render_body_pose_image
    from generators.kimodo.dwpose_runtime import create_fun_pose_detector
    from generators.wan_fun.vendor.videox_fun.dwpose_utils.onnxdet import inference_detector
    current_pose_detector=create_fun_pose_detector()
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
        # 참조 영상과 검출 결과를 같은 RGB 좌표계에 보존한다.
        current_rgb_path=current_attempt_root/f'reference-normalized-{current_reference_index}.png'
        Image.fromarray(current_image_array).save(current_rgb_path)
        current_image_digest=hashlib.sha256((current_job_root/current_reference_name).read_bytes()).hexdigest()
        current_detected_boxes=inference_detector(current_pose_detector.session_det,current_image_array)
        if current_detected_boxes is None or not len(current_detected_boxes):
            raise ValueError(f'참조 {current_reference_index}: 유효한 인물 검출 없음')
        current_detected_points=current_pose_detector(current_image_array)
        if current_detected_points is None or len(current_detected_boxes)!=len(current_detected_points):
            raise ValueError(f'참조 {current_reference_index}: 인물·관절 검출 수 불일치')
        current_person_records=sorted(zip(current_detected_boxes,current_detected_points),key=lambda current_person_record:(float(current_person_record[0][1]),float(current_person_record[0][0])))
        for current_person_index,(current_person_box,current_person_points) in enumerate(current_person_records,1):
            current_body_points=np.asarray(current_person_points[:18],dtype=float).copy()
            current_raw_scores=current_body_points[:,2].tolist()
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
            current_observation_sources.append({'observation':len(current_reference_records),'image':current_reference_index,'person':current_person_index,'bbox':current_person_box[:4].tolist(),'confidence':None,'raw_heatmap_scores':current_raw_scores})
            current_preview_points=current_body_points.copy()
            current_preview_points[:,:2]*=512/max(current_image_array.shape[:2])
            render_body_pose_image(current_preview_points).save(current_attempt_root/f'reference-pose-{current_reference_index}-{current_person_index}.png')
        print(time.strftime('%Y-%m-%dT%H:%M:%S')+f'/kimodo/reference {current_reference_index}/{len(current_request_record["references"])}',flush=True)
    if current_pending_edits:
        raise ValueError('수정할 참조 인물을 찾을 수 없습니다.')
    current_observation_heights=[float(current_source_record['bbox'][3]-current_source_record['bbox'][1]) for current_source_record in current_observation_sources]
    current_ratio_record=estimate_reference_proportions(current_reference_records,current_observation_heights)
    current_ratio_record['reference_pose_model']='VideoX-Fun DWPose (YOLOX-L + DW-LL) · MIGraphX'
    current_ratio_record['confidence_policy']='DWPose 관절 점수는 확률이 아님. 원시값 보존, 추정·렌더 점수는 [0,1] 제한.'
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
