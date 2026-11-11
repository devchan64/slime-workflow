"""겹친 골반 관측을 3D 투영으로 재구성하는 비파괴 시험."""
import numpy as np

HIP_PROJECTION_MINIMUM_TORSO = 1e-8


def reconstruct_projected_hip_pair(current_detected_points, current_reference_points):
    """검출 골반 중심과 다리 벡터를 유지하며 참조 투영 골반 벡터를 옮긴다.

    두 입력은 같은 프레임·방향의 2D BODY18 좌표다. 참조 3D 투영과
    검출 포즈의 몸통 길이로 픽셀 크기를 맞춘다. 신뢰성 판단이나 자동
    생성 적용은 수행하지 않는다.
    """
    current_detected_points=np.asarray(current_detected_points,dtype=float)
    current_reference_points=np.asarray(current_reference_points,dtype=float)
    if current_detected_points.shape != (18,2) or current_reference_points.shape != (18,2) or not np.isfinite(current_detected_points).all() or not np.isfinite(current_reference_points).all():
        raise ValueError('골반 재구성에는 유한한 BODY18 2D 좌표가 필요합니다.')
    current_detected_hip=current_detected_points[[8,11]].mean(axis=0)
    current_detected_shoulder=current_detected_points[[2,5]].mean(axis=0)
    current_reference_hip=current_reference_points[[8,11]].mean(axis=0)
    current_reference_shoulder=current_reference_points[[2,5]].mean(axis=0)
    current_detected_torso=float(np.linalg.norm(current_detected_shoulder-current_detected_hip))
    current_reference_torso=float(np.linalg.norm(current_reference_shoulder-current_reference_hip))
    if min(current_detected_torso,current_reference_torso) <= HIP_PROJECTION_MINIMUM_TORSO:
        raise ValueError('골반 재구성 기준 몸통 길이가 0입니다.')
    current_reference_vectors=(current_reference_points[[8,11]]-current_reference_hip)*(current_detected_torso/current_reference_torso)
    current_new_hips=current_detected_hip+current_reference_vectors
    current_adjusted_points=current_detected_points.copy()
    for current_hip_index,current_chain_indices,current_target_position in ((8,(8,9,10),current_new_hips[0]),(11,(11,12,13),current_new_hips[1])):
        current_adjusted_points[list(current_chain_indices)] += current_target_position-current_detected_points[current_hip_index]
    return current_adjusted_points


def reconstruct_projected_hip_frames(current_detected_frames, current_reference_frames):
    """검출 기록의 다리 벡터와 나머지 포즈를 유지하며 골반 투영을 대입한다."""
    if not isinstance(current_detected_frames, list) or not isinstance(current_reference_frames, list) or not current_detected_frames or len(current_detected_frames) != len(current_reference_frames):
        raise ValueError('검출 포즈와 3D 투영 프레임 수가 같아야 합니다.')
    current_result_frames=[]
    for current_frame_records,current_reference_frame in zip(current_detected_frames,current_reference_frames):
        if not isinstance(current_frame_records,list) or len(current_frame_records)!=1:
            raise ValueError('프레임마다 단일 인체가 필요합니다.')
        current_pose=current_frame_records[0]
        current_points=current_pose.body.keypoints
        if len(current_points)!=18 or any(current_points[current_index] is None for current_index in (2,5,8,9,10,11,12,13)):
            raise ValueError('시험 골반 재구성에는 양 어깨·골반·다리 관절이 필요합니다.')
        current_coordinates=np.array([[current_point.x,current_point.y] if current_point is not None else [0.,0.] for current_point in current_points],dtype=float)
        current_reference=np.asarray(current_reference_frame,dtype=float)
        if current_reference.shape!=(18,3):
            raise ValueError('3D 투영 포즈의 BODY18 좌표 형식 오류')
        current_adjusted=reconstruct_projected_hip_pair(current_coordinates,current_reference[:,:2])
        current_new_points=[current_point._replace(x=float(current_adjusted[current_index,0]),y=float(current_adjusted[current_index,1])) if current_point is not None else None for current_index,current_point in enumerate(current_points)]
        current_result_frames.append([current_pose._replace(body=current_pose.body._replace(keypoints=current_new_points))])
    return current_result_frames
