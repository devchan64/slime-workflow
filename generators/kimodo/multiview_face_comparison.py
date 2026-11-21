"""동일 모션의 얼굴 앵커 전후 포즈를 참조 BODY18과 비교한다."""
import hashlib
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_body_face_experiment import FACE_LANDMARK_INDICES
from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash
from generators.kimodo.reference_proportions import REFERENCE_CONFIDENCE_THRESHOLD


def normalize_face_comparison_points(current_body_points):
    """어깨–발목 높이와 골반 중심으로 화면 크기와 위치를 정규화한다."""
    current_points=np.asarray(current_body_points,dtype=float)
    if current_points.shape!=(18,3) or not np.isfinite(current_points).all():
        raise ValueError('얼굴 비교 BODY18 좌표 형식 오류')
    current_height=abs(float(current_points[[2,5],1].mean()-current_points[[10,13],1].mean()))
    if current_height<=1e-8:
        raise ValueError('얼굴 비교 어깨–발목 높이가 0입니다.')
    return (current_points[:,:2]-current_points[[8,11],:2].mean(axis=0))/current_height


def compare_face_anchor_outputs(current_reference_record,current_baseline_record,current_candidate_record,current_direction_mapping):
    """검수 가중치가 유효한 얼굴 관측의 첫 프레임 오차를 구한다."""
    current_reference_ratio=current_baseline_record.get('reference_proportions')
    if not isinstance(current_reference_ratio,dict) or current_reference_ratio!=current_candidate_record.get('reference_proportions'):
        raise ValueError('비교 출력의 참조 비율이 서로 다릅니다.')
    current_skeleton=current_reference_ratio.get('weighted_body_face_candidate')
    if not isinstance(current_skeleton,dict) or current_skeleton.get('observation_sha256')!=calculate_multiview_observation_hash(current_reference_record):
        raise ValueError('비교 참조 관측과 골격의 출처가 다릅니다.')
    current_weights=validate_multiview_joint_weights(current_skeleton['joint_weight_table'])
    current_fit_views=current_skeleton.get('views')
    if not isinstance(current_fit_views,list) or len(current_fit_views)!=8 or any(current_view.get('observation')!=current_index+1 or not isinstance(current_view.get('face_fit_weights'),list) or len(current_view['face_fit_weights'])!=5 for current_index,current_view in enumerate(current_fit_views)):
        raise ValueError('얼굴 가시성 적합 가중치 기록 오류')
    current_baseline_views=current_baseline_record.get('directions',{})
    current_candidate_views=current_candidate_record.get('directions',{})
    if not isinstance(current_direction_mapping,dict) or set(current_direction_mapping)!=set(current_baseline_views) or set(current_direction_mapping)!=set(current_candidate_views) or sorted(current_direction_mapping.values())!=list(range(1,9)):
        raise ValueError('8방향 출력과 참조 관측 대응 오류')
    current_rows=[]
    current_maximum_body_difference=0.0
    for current_direction_name,current_observation in current_direction_mapping.items():
        current_original=np.asarray(current_baseline_views[current_direction_name]['body_points_832x480'],dtype=float)
        current_adjusted=np.asarray(current_candidate_views[current_direction_name]['body_points_832x480'],dtype=float)
        if current_original.ndim!=3 or current_original.shape[1:]!=(18,3) or current_adjusted.shape!=current_original.shape or not len(current_original) or not np.isfinite(current_original).all() or not np.isfinite(current_adjusted).all():
            raise ValueError('방향별 프레임 또는 BODY18 좌표 오류')
        if current_baseline_views[current_direction_name]['source_frames']!=current_candidate_views[current_direction_name]['source_frames']:
            raise ValueError('비교할 원본 프레임 순서가 다릅니다.')
        current_difference=float(np.max(np.abs(current_original[:,2:14,:2]-current_adjusted[:,2:14,:2])))
        current_maximum_body_difference=max(current_maximum_body_difference,current_difference)
        if current_difference>1e-6:
            raise ValueError('얼굴 앵커 외 몸 관절이 변경되어 같은 조건의 비교가 아닙니다.')
        current_reference=current_reference_record['keypoints'][current_observation-1]
        current_reference_xy=normalize_face_comparison_points(current_reference)
        current_original_xy=normalize_face_comparison_points(current_original[0])
        current_adjusted_xy=normalize_face_comparison_points(current_adjusted[0])
        for current_face_offset,current_joint_index in enumerate(FACE_LANDMARK_INDICES):
            current_fit_weight=current_fit_views[current_observation-1]['face_fit_weights'][current_face_offset]
            if type(current_fit_weight) not in (int,float) or not np.isfinite(current_fit_weight) or current_fit_weight<0:
                raise ValueError('얼굴 적합 가중치 값 오류')
            current_score=current_reference[current_joint_index][2]
            current_weight=current_weights[current_observation-1][current_joint_index]
            if current_score<REFERENCE_CONFIDENCE_THRESHOLD or current_weight<=0 or current_fit_weight<=0:
                continue
            current_rows.append({'direction':current_direction_name,'observation':current_observation,'joint':current_joint_index,'detector_score':current_score,'weight':current_weight,'effective_weight':current_fit_weight,'baseline_error':float(np.linalg.norm(current_original_xy[current_joint_index]-current_reference_xy[current_joint_index])),'candidate_error':float(np.linalg.norm(current_adjusted_xy[current_joint_index]-current_reference_xy[current_joint_index]))})
    current_summary={}
    for current_joint_index in FACE_LANDMARK_INDICES:
        current_group=[current_row for current_row in current_rows if current_row['joint']==current_joint_index]
        current_summary[str(current_joint_index)]={'count':len(current_group),'baseline':float(np.mean([current_row['baseline_error'] for current_row in current_group])) if current_group else None,'candidate':float(np.mean([current_row['candidate_error'] for current_row in current_group])) if current_group else None}
    return {'schema':'kimodo-face-anchor-comparison-v1','normalization':'양 어깨 중점–양 발목 중점의 영상 세로 거리; 골반 중심 원점','direction_mapping_assumed':current_direction_mapping,'body_joint_max_difference_px':current_maximum_body_difference,'rows':current_rows,'summary':current_summary,'limitations':['얼굴 앵커와 검수 참조는 동일 데이터에서 얻었으므로 독립 정확도 검증이 아님','참조의 대각 각도와 출력 방향 대응은 가정','참조 가림 관측은 제외하며 출력의 얼굴 가림은 판정하지 않음','단일 참조 자세와 생성 첫 프레임의 차이가 포함됨']}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='동일 모션 얼굴 앵커 전후 8방향 비교')
    for current_name in ('reference','baseline','candidate','mapping','output'):
        current_parser.add_argument(current_name,type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 얼굴 비교 기록을 덮어쓰지 않습니다.')
    current_inputs={current_name:json.loads(getattr(current_arguments,current_name).read_text()) for current_name in ('reference','baseline','candidate','mapping')}
    current_result=compare_face_anchor_outputs(current_inputs['reference'],current_inputs['baseline'],current_inputs['candidate'],current_inputs['mapping'])
    current_result['inputs']={current_name:{'path':str(getattr(current_arguments,current_name)),'sha256':hashlib.sha256(getattr(current_arguments,current_name).read_bytes()).hexdigest()} for current_name in current_inputs}
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'얼굴 앵커 8방향 비교 저장: {current_arguments.output}',flush=True)
