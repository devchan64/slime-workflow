"""SOMA 투영 벡터로 DWPose 미검출 팔다리 관절을 보완한다."""
import numpy as np

# 부모에서 자식 순서. 중간 관절은 다음 관절도 검출됐다면 양쪽 끝에 맞춘다.
BODY_LIMB_CHAINS = ((2, 3, 4), (5, 6, 7), (8, 9, 10), (11, 12, 13))


def complete_occluded_body_joints(current_detected_frames, current_projected_frames, current_coordinate_scale):
    """검출된 좌표는 유지하고 미검출 관절만 같은 프레임 SOMA 투영으로 추정한다."""
    current_projection_array = np.asarray(current_projected_frames, dtype=float)
    current_scale_array = np.asarray(current_coordinate_scale, dtype=float)
    if (current_projection_array.shape != (len(current_detected_frames), 18, 3)
            or not np.isfinite(current_projection_array).all() or (current_projection_array[:, :, 2] <= 0).any()
            or current_scale_array.shape != (2,) or not np.isfinite(current_scale_array).all()
            or (current_scale_array <= 0).any()):
        raise ValueError('SOMA 투영 프레임 또는 좌표 변환이 올바르지 않습니다.')
    current_completed_frames = []
    current_completion_records = []
    for current_frame_index, current_frame_records in enumerate(current_detected_frames):
        if len(current_frame_records) != 1:
            raise ValueError('관절 보완에는 프레임마다 단일 인체가 필요합니다.')
        current_pose_record = current_frame_records[0]
        current_body_points = list(current_pose_record.body.keypoints)
        if len(current_body_points) != 18:
            raise ValueError('관절 보완에는 BODY18 좌표가 필요합니다.')
        current_reference_points = current_projection_array[current_frame_index, :, :2] * current_scale_array
        current_filled_joints = []
        for current_parent_index, current_middle_index, current_end_index in BODY_LIMB_CHAINS:
            current_parent_point = current_body_points[current_parent_index]
            if current_parent_point is None:
                continue
            if current_body_points[current_middle_index] is None:
                current_parent_xy = np.array([current_parent_point.x, current_parent_point.y], dtype=float)
                current_first_vector = current_reference_points[current_middle_index] - current_reference_points[current_parent_index]
                current_middle_xy = current_parent_xy + current_first_vector
                current_end_point = current_body_points[current_end_index]
                if current_end_point is not None:
                    current_second_vector = current_reference_points[current_end_index] - current_reference_points[current_middle_index]
                    current_total_length = np.linalg.norm(current_first_vector) + np.linalg.norm(current_second_vector)
                    if current_total_length <= 1e-8:
                        raise ValueError('SOMA 투영 관절 벡터 길이가 0입니다.')
                    current_end_xy = np.array([current_end_point.x, current_end_point.y], dtype=float)
                    current_middle_xy += (current_end_xy - (current_parent_xy + current_first_vector + current_second_vector)) * (np.linalg.norm(current_first_vector) / current_total_length)
                current_body_points[current_middle_index] = current_parent_point._replace(x=float(current_middle_xy[0]), y=float(current_middle_xy[1]), score=0.0, id=current_middle_index)
                current_filled_joints.append(current_middle_index)
            if current_body_points[current_end_index] is None and current_body_points[current_middle_index] is not None:
                current_middle_point = current_body_points[current_middle_index]
                current_end_xy = np.array([current_middle_point.x, current_middle_point.y]) + current_reference_points[current_end_index] - current_reference_points[current_middle_index]
                current_body_points[current_end_index] = current_middle_point._replace(x=float(current_end_xy[0]), y=float(current_end_xy[1]), score=0.0, id=current_end_index)
                current_filled_joints.append(current_end_index)
        if current_filled_joints:
            current_completion_records.append({'frame': current_frame_index+1, 'joints': current_filled_joints})
        current_completed_frames.append([current_pose_record._replace(body=current_pose_record.body._replace(keypoints=current_body_points))])
    return current_completed_frames, current_completion_records
