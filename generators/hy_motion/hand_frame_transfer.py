"""손목·중지·검지·소지 기준점으로 회전 기준계를 맞춘다. 임상 관절축 보정은 아니다."""
import numpy as np
from pathlib import Path
import yaml
from generators.hy_motion.contracts import UniqueConfigLoader

MINIMUM_FRAME_LENGTH = 1e-8
MAXIMUM_FRAME_ERROR = 1e-5
HAND_CALIBRATION_FIELDS = {'schema_version','calibration_kind','anatomical_joint_limits_verified','landmark_order','source_body_rotation_indices','source_joint_names','target_bone_names','source_contract','target_contract'}


def load_hand_calibration(current_profile_path):
    current_profile_record=yaml.load(Path(current_profile_path).read_text(),Loader=UniqueConfigLoader)
    if not isinstance(current_profile_record,dict) or set(current_profile_record)!=HAND_CALIBRATION_FIELDS or type(current_profile_record['schema_version']) is not int or current_profile_record['schema_version']!=1 or current_profile_record['calibration_kind']!='rig_hand_landmark_frame' or current_profile_record['anatomical_joint_limits_verified'] is not False or current_profile_record['landmark_order']!=['wrist','middle_base','index_base','little_base']:
        raise ValueError('손 기준점 보정 프로필 계약 오류')
    for current_field_name in ('source_body_rotation_indices','source_joint_names','target_bone_names'):
        current_mapping_values=current_profile_record[current_field_name]
        if not isinstance(current_mapping_values,dict) or set(current_mapping_values)!={'left','right'}:
            raise ValueError('손 기준점 좌우 대응 필드 오류')
        for current_side_name,current_field_value in current_mapping_values.items():
            if current_field_name=='source_body_rotation_indices':
                if type(current_field_value) is not int or current_field_value!={'left':20,'right':21}[current_side_name]:
                    raise ValueError('HY-Motion 손목 회전 인덱스 오류')
            elif not isinstance(current_field_value,list) or len(current_field_value)!=4 or any(not isinstance(current_point_name,str) or not current_point_name for current_point_name in current_field_value) or len(set(current_field_value))!=4:
                raise ValueError('손 기준점 이름 목록 오류')
    for current_field_name in ('source_contract','target_contract'):
        if not isinstance(current_profile_record[current_field_name],str) or not current_profile_record[current_field_name]:
            raise ValueError('손 기준점 출처가 없습니다.')
    return current_profile_record


def build_hand_frame(current_landmark_points):
    """입력 순서: 손목, 중지 기저, 검지 기저, 소지 기저. 열: 가로·길이·법선."""
    current_landmark_points=np.asarray(current_landmark_points,dtype=np.float64)
    if current_landmark_points.shape!=(4,3) or not np.isfinite(current_landmark_points).all():
        raise ValueError('손 기준점은 유한한 [4,3] 배열이어야 합니다.')
    current_length_axis=current_landmark_points[1]-current_landmark_points[0]
    if np.linalg.norm(current_length_axis)<=MINIMUM_FRAME_LENGTH:
        raise ValueError('손 길이 축이 퇴화했습니다.')
    current_length_axis/=np.linalg.norm(current_length_axis)
    current_width_axis=current_landmark_points[2]-current_landmark_points[3]
    current_width_axis-=current_length_axis*np.dot(current_width_axis,current_length_axis)
    if np.linalg.norm(current_width_axis)<=MINIMUM_FRAME_LENGTH:
        raise ValueError('손 가로 축이 퇴화했습니다.')
    current_width_axis/=np.linalg.norm(current_width_axis)
    return np.column_stack((current_width_axis,current_length_axis,np.cross(current_width_axis,current_length_axis)))


def validate_rotation_frame(current_rotation_matrix):
    current_rotation_matrix=np.asarray(current_rotation_matrix,dtype=np.float64)
    if current_rotation_matrix.shape!=(3,3) or not np.isfinite(current_rotation_matrix).all() or np.max(np.abs(current_rotation_matrix.T@current_rotation_matrix-np.eye(3)))>MAXIMUM_FRAME_ERROR or abs(np.linalg.det(current_rotation_matrix)-1)>MAXIMUM_FRAME_ERROR:
        raise ValueError('회전 기준계는 유한한 오른손 직교 행렬이어야 합니다.')
    return current_rotation_matrix


def transfer_hand_rotation(source_global_rotation,source_reference_frame,target_reference_frame,target_bone_rotation):
    """같은 좌표계에서 원본 손 기준계 방향을 대상 손 기준계로 전달한다."""
    source_global_rotation=validate_rotation_frame(source_global_rotation)
    source_reference_frame=validate_rotation_frame(source_reference_frame)
    target_reference_frame=validate_rotation_frame(target_reference_frame)
    target_bone_rotation=validate_rotation_frame(target_bone_rotation)
    return source_global_rotation@source_reference_frame@target_reference_frame.T@target_bone_rotation
