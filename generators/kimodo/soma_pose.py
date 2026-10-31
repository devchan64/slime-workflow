"""SOMA77 원본 위치를 BODY_18 몸 포즈로 직접 투영한다. 실제 눈 관절만 사용하며 코·귀를 합성하지 않는다."""
import json
from pathlib import Path
import numpy as np
from generators.kimodo.contracts import KIMODO_DIRECTION_RECORDS

# OpenPose 순서: 코·목·오른팔·왼팔·오른다리·왼다리·눈·귀.
SOMA_BODY_JOINT_NAMES = (None,None,'RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand','RightLeg','RightShin','RightFoot','LeftLeg','LeftShin','LeftFoot','RightEye','LeftEye',None,None)
SOMA_POSE_IMAGE_SIZE = 512
SOMA_POSE_FRAME_MARGIN = 32
SOMA_POSE_SCHEMA_VERSION = 'soma-body18-v3'


def project_soma_body_points(current_joint_positions,current_joint_names,current_direction_name,current_ratio_record=None):
    """전체 클립의 고정 배율·중심으로 이동을 보존하는 수평 정사영을 만든다."""
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
        from generators.kimodo.reference_proportions import apply_reference_proportions
        current_body_positions=apply_reference_proportions(current_body_positions,current_ratio_record)
    current_camera_angle=np.deg2rad(KIMODO_DIRECTION_RECORDS[current_direction_name]['angle'])
    current_screen_positions=np.stack((current_body_positions[:,:,0]*np.cos(current_camera_angle)-current_body_positions[:,:,2]*np.sin(current_camera_angle),-current_body_positions[:,:,1]),axis=-1)
    current_frame_bounds=np.stack((current_joint_positions[:,:,0]*np.cos(current_camera_angle)-current_joint_positions[:,:,2]*np.sin(current_camera_angle),-current_joint_positions[:,:,1]),axis=-1)
    if current_ratio_record is not None:
        current_frame_bounds=current_screen_positions[:,1:16]
    current_minimum_bounds=current_frame_bounds.min(axis=(0,1))
    current_maximum_bounds=current_frame_bounds.max(axis=(0,1))
    current_render_scale=(SOMA_POSE_IMAGE_SIZE-2*SOMA_POSE_FRAME_MARGIN)/max(float((current_maximum_bounds-current_minimum_bounds).max()),0.1)
    current_output_points=np.zeros((len(current_joint_positions),18,3),dtype=float)
    current_output_points[:,1:16,:2]=(current_screen_positions[:,1:16]-(current_minimum_bounds+current_maximum_bounds)/2)*current_render_scale+SOMA_POSE_IMAGE_SIZE/2
    current_output_points[:,1:16,2]=1
    return current_output_points


def load_soma_pose_points(current_attempt_root,current_direction_names):
    current_attempt_root=Path(current_attempt_root)
    current_skeleton_record=json.loads((current_attempt_root/'skeleton.json').read_text())
    if current_skeleton_record['skeleton']!='somaskel77' or current_skeleton_record['fps']!=30:
        raise ValueError('SOMA 골격 종류·FPS 오류')
    current_motion_path = current_attempt_root/('motion-in-place.npz' if (current_attempt_root/'motion-in-place.npz').is_file() else 'motion.npz')
    with np.load(current_motion_path,allow_pickle=False) as current_motion_archive:
        current_joint_positions=current_motion_archive['posed_joints']
    current_ratio_path=current_attempt_root/'reference-proportions.json'
    current_ratio_record=json.loads(current_ratio_path.read_text()) if current_ratio_path.is_file() else None
    return {current_direction_name:project_soma_body_points(current_joint_positions,current_skeleton_record['joint_names'],current_direction_name,current_ratio_record) for current_direction_name in current_direction_names}
