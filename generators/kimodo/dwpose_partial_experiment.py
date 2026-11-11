"""미검출 관절을 보존하는 DWPose 고정 비율 보정 시험."""
import numpy as np
from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS, calculate_reference_torso_gain


def adjust_partial_detected_frames(current_detected_frames,current_image_shape,current_segment_gains,current_scale_percent,current_ratio_record):
    """관측 누락을 합성하지 않고 연결 가능한 관절만 보정한다."""
    if not current_detected_frames or set(current_segment_gains)!=set(REFERENCE_SEGMENT_GROUPS) or any(not np.isfinite(current_gain) or current_gain<=0 for current_gain in current_segment_gains.values()):
        raise ValueError('부분 포즈 관절 배율 또는 프레임 오류')
    if len(current_image_shape)!=2 or min(current_image_shape)<=0 or not np.isfinite(current_scale_percent) or not 10<=current_scale_percent<=100:
        raise ValueError('부분 포즈 영상 크기 또는 배율 오류')
    current_axis_frames=[]
    for current_frame in current_detected_frames:
        if len(current_frame)!=1 or len(current_frame[0].body.keypoints)!=18:
            raise ValueError('단일 인체 BODY18 검출이 필요합니다.')
        current_points=current_frame[0].body.keypoints
        if all(current_points[current_index] is not None for current_index in (0,1,2,5,8,11)):
            current_axis_frames.append([[current_point.x,current_point.y] if current_point else [0.,0.] for current_point in current_points])
    if not current_axis_frames:
        raise ValueError('얼굴·몸통 기준 관측이 없습니다.')
    current_torso_gain=calculate_reference_torso_gain(np.asarray(current_axis_frames),current_ratio_record)
    current_center=np.array([current_image_shape[1]/2,current_image_shape[0]/2])
    current_output=[]
    current_missing_rows=[]
    for current_frame_index,current_frame in enumerate(current_detected_frames):
        current_pose=current_frame[0];current_points=current_pose.body.keypoints
        if any(current_points[current_index] is None for current_index in (1,2,5,8,11)):
            raise ValueError(f'{current_frame_index+1}프레임의 몸통 기준 관절이 없습니다.')
        current_original=np.array([[current_point.x,current_point.y] if current_point else [np.nan,np.nan] for current_point in current_points])
        current_adjusted=current_original.copy()
        current_shoulders=current_original[[2,5]].mean(0);current_hips=current_original[[8,11]].mean(0)
        current_shift=(current_shoulders-current_hips)*(current_torso_gain-1)
        current_adjusted[1]=current_original[1]+current_shift
        for current_group in ('shoulder_width','hip_width'):
            current_pair=REFERENCE_SEGMENT_GROUPS[current_group][0]
            current_pair_center=current_original[list(current_pair)].mean(0)
            if current_group=='shoulder_width':current_pair_center+=current_shift
            current_adjusted[list(current_pair)]=current_pair_center+(current_original[list(current_pair)]-current_original[list(current_pair)].mean(0))*current_segment_gains[current_group]*current_torso_gain
        for current_group in ('upper_arm','forearm','thigh','shin'):
            for current_parent,current_child in REFERENCE_SEGMENT_GROUPS[current_group]:
                if np.isfinite(current_original[[current_parent,current_child]]).all() and np.isfinite(current_adjusted[current_parent]).all():
                    current_adjusted[current_child]=current_adjusted[current_parent]+(current_original[current_child]-current_original[current_parent])*current_segment_gains[current_group]*current_torso_gain
                else:
                    current_adjusted[current_child]=np.nan
        current_missing=[current_index for current_index in range(18) if current_points[current_index] is None or not np.isfinite(current_adjusted[current_index]).all()]
        if current_missing:current_missing_rows.append({'frame':current_frame_index+1,'missing_joints':current_missing})
        def transform_pose_points(current_items,current_translation):
            if current_items is None:return None
            return [current_point._replace(x=float((current_point.x+current_translation[0]-current_center[0])*current_scale_percent/100+current_center[0]),y=float((current_point.y+current_translation[1]-current_center[1])*current_scale_percent/100+current_center[1])) if current_point else None for current_point in current_items]
        current_updated=[current_point._replace(x=float(current_adjusted[current_index,0]),y=float(current_adjusted[current_index,1])) if current_point is not None and np.isfinite(current_adjusted[current_index]).all() else None for current_index,current_point in enumerate(current_points)]
        current_left=transform_pose_points(current_pose.left_hand,current_adjusted[7]-current_original[7]) if current_updated[7] is not None else None
        current_right=transform_pose_points(current_pose.right_hand,current_adjusted[4]-current_original[4]) if current_updated[4] is not None else None
        current_output.append([current_pose._replace(body=current_pose.body._replace(keypoints=transform_pose_points(current_updated,[0,0])),left_hand=current_left,right_hand=current_right,face=transform_pose_points(current_pose.face,[0,0]))])
    return current_output,{'torso_gain':current_torso_gain,'axis_valid_frames':len(current_axis_frames),'total_frames':len(current_detected_frames),'incomplete_frames':current_missing_rows,'policy':'미검출과 연결 불가 관절은 합성하지 않고 생략'}
