"""참조 8방향의 관절 가중치를 카메라 방향에 따라 보간해 검수한다."""
import hashlib
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights


def interpolate_direction_joint_weights(current_reference_views,current_weight_record,current_output_angles,current_angle_offset):
    """원형 각도에서 인접한 두 관측의 판단 가중치를 선형 보간한다."""
    current_weight_rows=np.asarray(validate_multiview_joint_weights(current_weight_record),dtype=float)
    if not isinstance(current_reference_views,list) or len(current_reference_views)!=8 or any(current_view.get('observation')!=current_index+1 for current_index,current_view in enumerate(current_reference_views)):
        raise ValueError('참조 카메라 8개와 관측 순서가 필요합니다.')
    current_reference_angles=np.asarray([current_view['fitted_yaw_degrees'] for current_view in current_reference_views],dtype=float)
    current_output_angles=np.asarray(current_output_angles,dtype=float)
    if current_reference_angles.shape!=(8,) or not np.isfinite(current_reference_angles).all() or current_output_angles.ndim!=1 or not len(current_output_angles) or not np.isfinite(current_output_angles).all() or type(current_angle_offset) not in (int,float) or not np.isfinite(current_angle_offset):
        raise ValueError('참조·출력 방향 각도 형식 오류')
    current_reference_angles=np.mod(current_reference_angles,360.)
    current_order=np.argsort(current_reference_angles)
    current_reference_angles=current_reference_angles[current_order]
    current_weight_rows=current_weight_rows[current_order]
    current_circular_gaps=np.diff(np.r_[current_reference_angles,current_reference_angles[0]+360.])
    if np.any(current_circular_gaps<1e-6):
        raise ValueError('같은 방향의 참조 각도를 보간할 수 없습니다.')
    current_frames=[]
    for current_frame_index,current_raw_angle in enumerate(current_output_angles):
        current_angle=(float(current_raw_angle)+current_angle_offset)%360.
        current_right_index=int(np.searchsorted(current_reference_angles,current_angle,side='right'))%8
        current_left_index=(current_right_index-1)%8
        current_gap=(current_reference_angles[current_right_index]-current_reference_angles[current_left_index])%360.
        current_fraction=((current_angle-current_reference_angles[current_left_index])%360.)/current_gap
        current_result=(1-current_fraction)*current_weight_rows[current_left_index]+current_fraction*current_weight_rows[current_right_index]
        current_frames.append({'frame':current_frame_index,'input_yaw_degrees':float(current_raw_angle),'aligned_yaw_degrees':current_angle,'left_observation':int(current_order[current_left_index]+1),'right_observation':int(current_order[current_right_index]+1),'fraction':float(current_fraction),'weights':current_result.tolist()})
    return {'schema':'kimodo-direction-weight-diagnostics-v1','angle_offset_degrees':float(current_angle_offset),'frames':current_frames,'limitations':['기준 각도 부호·영점의 정합은 사용자가 제공한 가정','관측 가중치는 사람의 판단이며 보간값은 검출 점수나 가시성 확률이 아님','머리 방향을 몸 관절 방향이나 손·몸에 의한 실제 가림으로 간주할 수 없음','진단용이며 생성 포즈에 자동 적용하지 않음']}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='프레임별 방향 관절 가중치 검수')
    current_parser.add_argument('skeleton',type=Path)
    current_parser.add_argument('head_motion',type=Path)
    current_parser.add_argument('direction')
    current_parser.add_argument('angle_offset',type=float,help='출력 각도를 참조 각도에 맞추는 가정 보정값')
    current_parser.add_argument('output',type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 방향 가중치 진단을 덮어쓰지 않습니다.')
    current_skeleton=json.loads(current_arguments.skeleton.read_text())
    current_motion=json.loads(current_arguments.head_motion.read_text())
    current_views=[current_view for current_view in current_motion['views'] if current_view['direction']==current_arguments.direction]
    if len(current_views)!=1:
        raise ValueError('선택한 출력 방향이 없거나 중복되었습니다.')
    current_result=interpolate_direction_joint_weights(current_skeleton['views'],current_skeleton['joint_weight_table'],current_views[0]['yaw_degrees'],current_arguments.angle_offset)
    current_result['direction']=current_arguments.direction
    current_result['inputs']={current_name:{'path':str(getattr(current_arguments,current_name)),'sha256':hashlib.sha256(getattr(current_arguments,current_name).read_bytes()).hexdigest()} for current_name in ('skeleton','head_motion')}
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'프레임별 방향 가중치 진단 저장: {current_arguments.output}',flush=True)
