"""SOMA77 원본 위치를 BODY_18 몸 포즈로 직접 투영한다. 실제 눈 관절만 사용하며 코·귀를 합성하지 않는다."""
import json
from pathlib import Path
import numpy as np
from generators.kimodo.contracts import KIMODO_DIRECTION_RECORDS

# OpenPose 순서: 코·목·오른팔·왼팔·오른다리·왼다리·눈·귀.
SOMA_BODY_JOINT_NAMES = (None,None,'RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand','RightLeg','RightShin','RightFoot','LeftLeg','LeftShin','LeftFoot','RightEye','LeftEye',None,None)
SOMA_POSE_IMAGE_SIZE = 512
SOMA_POSE_LEGACY_PERCENT = 100.0
SOMA_POSE_FRAME_MARGIN = 32
SOMA_POSE_SCHEMA_VERSION = 'soma-body18-v3'


def project_soma_body_points(current_joint_positions,current_joint_names,current_direction_name,current_ratio_record=None,current_scale_percent=SOMA_POSE_LEGACY_PERCENT,current_elevation_angle=0):
    """전체 클립의 고정 배율·중심으로 이동을 보존하는 수평 정사영을 만든다."""
    if type(current_scale_percent) not in (int,float) or not np.isfinite(current_scale_percent) or not 10<=current_scale_percent<=100:
        raise ValueError('OpenPose 크기 비율은 10~100% 숫자여야 합니다.')
    if len(current_joint_names)!=77 or len(set(current_joint_names))!=77:
        raise ValueError('SOMA77 관절 이름 계약 오류')
    if current_joint_positions.ndim!=3 or current_joint_positions.shape[1:]!=(77,3) or not len(current_joint_positions) or not np.isfinite(current_joint_positions).all():
        raise ValueError('SOMA77 관절 위치 계약 오류')
    if current_direction_name not in KIMODO_DIRECTION_RECORDS:
        raise ValueError('SOMA 포즈 방향 오류')
    current_body_positions=np.zeros((len(current_joint_positions),18,3),dtype=float)
    for current_point_index,current_joint_name in enumerate(SOMA_BODY_JOINT_NAMES):
        if current_joint_name is not None:
            current_body_positions[:,current_point_index]=current_joint_positions[:,current_joint_names.index(current_joint_name)]
    current_body_positions[:,1]=(current_body_positions[:,2]+current_body_positions[:,5])/2
    if current_ratio_record is not None:
        if current_ratio_record.get('body_axis') is not None:
            current_body_positions[:,0]=current_joint_positions[:,current_joint_names.index('Head')]
        from generators.kimodo.reference_proportions import apply_reference_proportions
        current_body_positions=apply_reference_proportions(current_body_positions,current_ratio_record)
    from generators.kimodo.soma_render import build_soma_camera_rotation
    current_rotation_matrix=build_soma_camera_rotation(KIMODO_DIRECTION_RECORDS[current_direction_name]['angle'],current_elevation_angle)
    current_rotated_body=current_body_positions @ current_rotation_matrix.T
    current_rotated_joints=current_joint_positions @ current_rotation_matrix.T
    current_screen_positions=np.stack((current_rotated_body[:,:,0],-current_rotated_body[:,:,1]),axis=-1)
    current_frame_bounds=np.stack((current_rotated_joints[:,:,0],-current_rotated_joints[:,:,1]),axis=-1)
    if current_ratio_record is not None:
        current_frame_bounds=current_screen_positions[:,1:16]
    current_minimum_bounds=current_frame_bounds.min(axis=(0,1))
    current_maximum_bounds=current_frame_bounds.max(axis=(0,1))
    current_render_scale=((SOMA_POSE_IMAGE_SIZE-2*SOMA_POSE_FRAME_MARGIN)*current_scale_percent/100)/max(float((current_maximum_bounds-current_minimum_bounds).max()),0.1)
    current_output_points=np.zeros((len(current_joint_positions),18,3),dtype=float)
    current_output_points[:,1:16,:2]=(current_screen_positions[:,1:16]-(current_minimum_bounds+current_maximum_bounds)/2)*current_render_scale+SOMA_POSE_IMAGE_SIZE/2
    current_output_points[:,1:16,2]=1
    return current_output_points


def load_soma_pose_points(current_attempt_root,current_direction_names,current_scale_percent=SOMA_POSE_LEGACY_PERCENT):
    current_attempt_root=Path(current_attempt_root)
    current_skeleton_record=json.loads((current_attempt_root/'skeleton.json').read_text())
    if current_skeleton_record['skeleton']!='somaskel77' or current_skeleton_record['fps']!=30:
        raise ValueError('SOMA 골격 종류·FPS 오류')
    current_motion_path = current_attempt_root/('motion-in-place.npz' if (current_attempt_root/'motion-in-place.npz').is_file() else 'motion.npz')
    with np.load(current_motion_path,allow_pickle=False) as current_motion_archive:
        current_joint_positions=current_motion_archive['posed_joints']
    current_ratio_path=current_attempt_root/'reference-proportions.json'
    current_ratio_record=json.loads(current_ratio_path.read_text()) if current_ratio_path.is_file() else None
    current_render_path=current_attempt_root/'soma-render.json'
    current_camera_records=json.loads(current_render_path.read_text()).get('cameras',{}) if current_render_path.is_file() else {}
    return {current_direction_name:project_soma_body_points(current_joint_positions,current_skeleton_record['joint_names'],current_direction_name,current_ratio_record,current_scale_percent,current_camera_records.get(current_direction_name,{}).get('elevation_degrees',0)) for current_direction_name in current_direction_names}


def project_recorded_camera_points(current_joint_positions, current_camera_record):
    """SOMA 메시 렌더의 정사영 카메라를 동일하게 적용한다. 결과는 원본 영상 픽셀이다."""
    current_rotation_matrix = np.asarray(current_camera_record['rotation_matrix'], dtype=float)
    current_center_position = np.asarray(current_camera_record['center_position'], dtype=float)
    current_half_height = current_camera_record['half_height']
    current_image_width = current_camera_record['width']
    current_image_height = current_camera_record['height']
    if current_rotation_matrix.shape != (3,3) or current_center_position.shape != (3,) or not np.isfinite(current_rotation_matrix).all() or not np.isfinite(current_center_position).all():
        raise ValueError('기록된 SOMA 카메라 행렬 형식 오류')
    if not np.allclose(current_rotation_matrix @ current_rotation_matrix.T, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(current_rotation_matrix),1):
        raise ValueError('SOMA 카메라 회전행렬 오류')
    if type(current_half_height) not in (int,float) or not np.isfinite(current_half_height) or current_half_height <= 0 or any(type(current_dimension_value) is not int or current_dimension_value <= 0 for current_dimension_value in (current_image_width,current_image_height)):
        raise ValueError('SOMA 카메라 배율·해상도 오류')
    current_joint_positions = np.asarray(current_joint_positions, dtype=float)
    if current_joint_positions.ndim < 2 or current_joint_positions.shape[-1] != 3 or not np.isfinite(current_joint_positions).all():
        raise ValueError('투영 관절 좌표 형식 오류')
    current_camera_positions = current_joint_positions @ current_rotation_matrix.T-current_center_position
    current_pixel_scale = current_image_height/(2*current_half_height)
    return np.stack((current_camera_positions[...,0]*current_pixel_scale+current_image_width/2, -current_camera_positions[...,1]*current_pixel_scale+current_image_height/2),axis=-1)
