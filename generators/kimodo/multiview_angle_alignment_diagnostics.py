"""참조와 SOMA의 8방향 방위각 부호·영점 정합을 검수한다."""
import hashlib
import json
from pathlib import Path

import numpy as np


def wrap_angle_difference(current_degrees):
    """각도 차이를 −180도 이상 180도 미만으로 정규화한다."""
    return (np.asarray(current_degrees,dtype=float)+180.)%360.-180.


def fit_circular_angle_alignment(current_source_angles,current_target_angles):
    """부호 후보와 원형 평균 영점을 비교하여 최소 오차를 찾는다."""
    current_source=np.asarray(current_source_angles,dtype=float)
    current_target=np.asarray(current_target_angles,dtype=float)
    if current_source.ndim!=1 or current_target.shape!=current_source.shape or len(current_source)<3 or not np.isfinite(current_source).all() or not np.isfinite(current_target).all():
        raise ValueError('각도 정합에는 3개 이상의 유한한 대응 각도가 필요합니다.')
    current_candidates=[]
    for current_sign in (1,-1):
        current_offsets=np.deg2rad(current_target-current_sign*current_source)
        current_mean=np.mean(np.exp(1j*current_offsets))
        if abs(current_mean)<1e-8:
            continue
        current_offset=float(np.rad2deg(np.angle(current_mean)))
        current_residual=wrap_angle_difference(current_target-(current_sign*current_source+current_offset))
        current_candidates.append({'sign':current_sign,'offset_degrees':current_offset,'mae_degrees':float(np.mean(np.abs(current_residual)))})
    if not current_candidates:
        raise ValueError('각도 정합의 원형 평균이 모호합니다.')
    return min(current_candidates,key=lambda current_item:current_item['mae_degrees'])


def diagnose_multiview_angle_alignment(current_skeleton,current_motion,current_mapping):
    """고정 8방향 대응과 각 방향 제외 재정합의 오차를 기록한다."""
    current_reference_views=current_skeleton.get('views')
    current_motion_views=current_motion.get('views')
    if not isinstance(current_reference_views,list) or len(current_reference_views)!=8 or any(current_view.get('observation')!=current_index+1 for current_index,current_view in enumerate(current_reference_views)) or not isinstance(current_motion_views,list) or len(current_motion_views)!=8:
        raise ValueError('8방향 참조와 출력이 필요합니다.')
    if not isinstance(current_mapping,dict) or len(current_mapping)!=8 or any(type(current_value) is not int for current_value in current_mapping.values()) or sorted(current_mapping.values())!=list(range(1,9)):
        raise ValueError('출력 방향과 참조 관측의 일대일 대응이 필요합니다.')
    current_names=[current_view.get('direction') for current_view in current_motion_views]
    if len(set(current_names))!=8 or set(current_names)!=set(current_mapping):
        raise ValueError('출력 방향과 대응표의 방향이 일치하지 않습니다.')
    current_source=np.asarray([current_view['first_yaw_degrees'] for current_view in current_motion_views],dtype=float)
    current_target=np.asarray([current_reference_views[current_mapping[current_name]-1]['fitted_yaw_degrees'] for current_name in current_names],dtype=float)
    current_fit=fit_circular_angle_alignment(current_source,current_target)
    current_residual=wrap_angle_difference(current_target-(current_fit['sign']*current_source+current_fit['offset_degrees']))
    current_rows=[]
    for current_index,current_name in enumerate(current_names):
        current_subset=np.arange(8)!=current_index
        current_heldout=fit_circular_angle_alignment(current_source[current_subset],current_target[current_subset])
        current_error=float(wrap_angle_difference(current_target[current_index]-(current_heldout['sign']*current_source[current_index]+current_heldout['offset_degrees'])))
        current_rows.append({'direction':current_name,'observation':current_mapping[current_name],'output_yaw_degrees':float(current_source[current_index]),'reference_yaw_degrees':float(current_target[current_index]),'fitted_residual_degrees':float(current_residual[current_index]),'heldout_residual_degrees':current_error,'heldout_sign':current_heldout['sign'],'heldout_offset_degrees':current_heldout['offset_degrees']})
    return {'schema':'kimodo-angle-alignment-diagnostics-v1','fit':current_fit,'heldout_mae_degrees':float(np.mean([abs(current_row['heldout_residual_degrees']) for current_row in current_rows])),'views':current_rows,'limitations':['참조 각도는 같은 8방향 2D 관측으로 추정한 값이며 실제 카메라 정답이 아님','방향 대응과 같은 자세라는 가정에 의존','머리 앵커와 몸 추정의 축 불확실성이 포함됨','각도 정합은 가림 판정이나 관절 정확도 보장이 아님']}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='8방향 참조와 출력 각도 정합 검수')
    for current_name in ('skeleton','motion','mapping','output'):
        current_parser.add_argument(current_name,type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 각도 정합 검수 결과를 덮어쓰지 않습니다.')
    current_inputs={current_name:json.loads(getattr(current_arguments,current_name).read_text()) for current_name in ('skeleton','motion','mapping')}
    current_result=diagnose_multiview_angle_alignment(current_inputs['skeleton'],current_inputs['motion'],current_inputs['mapping'])
    current_result['inputs']={current_name:{'path':str(getattr(current_arguments,current_name)),'sha256':hashlib.sha256(getattr(current_arguments,current_name).read_bytes()).hexdigest()} for current_name in current_inputs}
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'8방향 각도 정합 검수 저장: {current_arguments.output}',flush=True)
