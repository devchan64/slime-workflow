"""출력 카메라에 대한 프레임별 얼굴 방향 변화를 진단한다."""
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_face_anchor_experiment import validate_face_anchor_calibration


def calculate_head_motion_diagnostics(current_head_rotations,current_face_offsets,current_camera_records):
    """얼굴 앵커의 귀 중점→코 벡터가 카메라에서 회전한 각도를 측정한다."""
    current_head_rotations=np.asarray(current_head_rotations,dtype=float)
    current_face_offsets=np.asarray(current_face_offsets,dtype=float)
    if current_head_rotations.ndim!=3 or current_head_rotations.shape[1:]!=(3,3) or not len(current_head_rotations) or not np.isfinite(current_head_rotations).all() or current_face_offsets.shape!=(5,3) or not np.isfinite(current_face_offsets).all():
        raise ValueError('머리 회전 또는 얼굴 앵커 형식 오류')
    if not np.allclose(np.swapaxes(current_head_rotations,1,2)@current_head_rotations,np.eye(3),atol=1e-5) or not np.allclose(np.linalg.det(current_head_rotations),1,atol=1e-5):
        raise ValueError('머리 회전행렬 오류')
    current_forward_vector=current_face_offsets[0]-current_face_offsets[[3,4]].mean(axis=0)
    if np.linalg.norm(current_forward_vector)<=1e-8:
        raise ValueError('얼굴 방향 기준인 귀 중점과 코가 같습니다.')
    if not isinstance(current_camera_records,dict) or not current_camera_records:
        raise ValueError('진단할 출력 카메라가 없습니다.')
    current_world_vectors=np.einsum('fij,j->fi',current_head_rotations,current_forward_vector)
    current_views=[]
    for current_direction_name,current_camera_record in current_camera_records.items():
        current_camera_matrix=np.asarray(current_camera_record['rotation_matrix'],dtype=float)
        if current_camera_matrix.shape!=(3,3) or not np.isfinite(current_camera_matrix).all() or not np.allclose(current_camera_matrix@current_camera_matrix.T,np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(current_camera_matrix),1,atol=1e-5):
            raise ValueError('진단 카메라 회전행렬 오류')
        current_camera_vectors=current_world_vectors@current_camera_matrix.T
        current_horizontal_lengths=np.linalg.norm(current_camera_vectors[:,[0,2]],axis=1)
        if np.any(current_horizontal_lengths<=1e-8):
            raise ValueError('얼굴 방향이 카메라 수직축과 평행하여 방위각을 구할 수 없습니다.')
        current_angles=np.rad2deg(np.unwrap(np.arctan2(current_camera_vectors[:,0],current_camera_vectors[:,2])))
        current_deltas=current_angles-current_angles[0]
        current_views.append({'direction':current_direction_name,'first_yaw_degrees':float(current_angles[0]),'relative_min_degrees':float(current_deltas.min()),'relative_max_degrees':float(current_deltas.max()),'relative_span_degrees':float(np.ptp(current_deltas)),'yaw_degrees':current_angles.tolist()})
    return {'schema':'kimodo-head-motion-diagnostics-v1','frames':len(current_head_rotations),'views':current_views,'limitations':['귀 중점에서 코로 향하는 앵커를 얼굴 방향의 근사로 사용','머리 기울기와 카메라 고도에 따라 수평 방위각이 달라짐','몸·손·머리 메시의 가림을 판정하지 않음','방향 변화 진단이며 자동 가중치 또는 가시성 판정이 아님']}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='모션 머리 방향 변화 진단')
    current_parser.add_argument('attempt',type=Path)
    current_parser.add_argument('reference_ratio',type=Path)
    current_parser.add_argument('calibration',type=Path)
    current_parser.add_argument('output',type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 머리 방향 진단을 덮어쓰지 않습니다.')
    current_root=current_arguments.attempt.resolve()
    current_render=json.loads((current_root/'soma-render.json').read_text())
    current_names=json.loads((current_root/'skeleton.json').read_text())['joint_names']
    current_reference=json.loads(current_arguments.reference_ratio.read_text())
    current_calibration=json.loads(current_arguments.calibration.read_text())
    current_offsets=validate_face_anchor_calibration(current_calibration,current_reference['weighted_body_face_candidate'],current_names)
    current_motion_path=(current_root/current_render['source']).resolve()
    if current_motion_path.parent!=current_root:
        raise ValueError('모션 기록이 현재 시도 범위를 벗어났습니다.')
    with np.load(current_motion_path,allow_pickle=False) as current_motion:
        current_rotations=current_motion['global_rot_mats'][:,current_names.index('Head')]
    current_result=calculate_head_motion_diagnostics(current_rotations,current_offsets,current_render['cameras'])
    current_result['source_attempt']=str(current_root)
    current_result['calibration_binding']=current_calibration['binding_sha256']
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'머리 방향 변화 진단 저장: {current_arguments.output}',flush=True)
