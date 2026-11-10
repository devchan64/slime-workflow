"""복수 BODY18 관측의 신뢰도 가중 비율과 출력 전용 골격 보정."""
import numpy as np

REFERENCE_CONFIDENCE_THRESHOLD = 0.6
REFERENCE_SEGMENT_GROUPS = {
    'shoulder_width':((2,5),), 'hip_width':((8,11),),
    'upper_arm':((2,3),(5,6)), 'forearm':((3,4),(6,7)),
    'thigh':((8,9),(11,12)), 'shin':((9,10),(12,13)),
}
REFERENCE_RATIO_SCHEMA = 'body18-reference-ratios-v4'
REFERENCE_OUTLIER_MULTIPLIER = 1.35
REFERENCE_AXIS_GAIN_MINIMUM = 0.5
REFERENCE_AXIS_GAIN_MAXIMUM = 1.5
# 양쪽 위팔의 어깨와 팔꿈치가 모두 위팔 길이의 1/4 이내면 영상에서 겹친 관측이다.
REFERENCE_ARM_OVERLAP_FRACTION = 0.25


def calculate_weighted_median(current_sample_values,current_sample_weights):
    current_sort_indices=np.argsort(current_sample_values)
    current_sorted_weights=np.asarray(current_sample_weights)[current_sort_indices]
    current_median_index=np.searchsorted(np.cumsum(current_sorted_weights),current_sorted_weights.sum()/2)
    return float(np.asarray(current_sample_values)[current_sort_indices[current_median_index]])


def estimate_reference_proportions(current_reference_records,current_observation_heights=None):
    if current_observation_heights is not None and (len(current_observation_heights)!=len(current_reference_records) or any(type(current_height_value) not in (int,float) or not np.isfinite(current_height_value) or current_height_value<=0 for current_height_value in current_observation_heights)):
        raise ValueError('인물 검출 상자 높이 형식 오류')
    current_torso_height_ratios=[]
    if current_observation_heights is not None:
        for current_points_value,current_height_value in zip(current_reference_records,current_observation_heights):
            current_points_array=np.asarray(current_points_value,dtype=float)
            if current_points_array.shape!=(18,3) or not np.isfinite(current_points_array).all():
                raise ValueError('참조 BODY18 좌표·신뢰도 형식 오류')
            if current_points_array[[2,5,8,11],2].min()>=REFERENCE_CONFIDENCE_THRESHOLD:
                current_torso_value=float(np.linalg.norm(current_points_array[[2,5],:2].mean(0)-current_points_array[[8,11],:2].mean(0)))
                if current_torso_value>=10:
                    current_torso_height_ratios.append(current_torso_value/current_height_value)
        if not current_torso_height_ratios:
            raise ValueError('높이 기준 몸통 정규화에 유효한 어깨·골반 관측이 없습니다.')
    current_common_torso_height=float(np.median(current_torso_height_ratios)) if current_torso_height_ratios else None
    current_group_samples={current_group_name:[] for current_group_name in REFERENCE_SEGMENT_GROUPS}
    current_rejection_records=[]
    current_head_observations=[]
    for current_reference_index,current_reference_points in enumerate(current_reference_records,1):
        current_reference_points=np.asarray(current_reference_points,dtype=float)
        current_box_height=current_observation_heights[current_reference_index-1] if current_observation_heights is not None else None
        if current_reference_points.shape!=(18,3) or not np.isfinite(current_reference_points).all():
            raise ValueError('참조 BODY18 좌표·신뢰도 형식 오류')
        current_anchor_indices=[2,5,8,11]
        if current_reference_points[current_anchor_indices,2].min()<REFERENCE_CONFIDENCE_THRESHOLD:
            current_rejection_records.append({'image':current_reference_index,'reason':'어깨·골반 기준 관절 신뢰도 부족'})
            continue
        current_neck_center=current_reference_points[[2,5],:2].mean(0)
        current_hip_center=current_reference_points[[8,11],:2].mean(0)
        current_torso_length=float(np.linalg.norm(current_neck_center-current_hip_center))
        if current_torso_length<10:
            current_rejection_records.append({'image':current_reference_index,'reason':'몸통 관측 길이 부족'})
            continue
        current_anchor_weight=float(current_reference_points[current_anchor_indices,2].min())
        current_normalization_length=current_box_height*current_common_torso_height if current_box_height is not None else current_torso_length
        if current_reference_points[0,2]>=REFERENCE_CONFIDENCE_THRESHOLD:
            current_head_length=float(np.linalg.norm(current_reference_points[0,:2]-current_neck_center))
            if current_head_length>=5:
                current_head_observations.append((current_head_length/current_normalization_length,min(current_anchor_weight,float(current_reference_points[0,2])),current_reference_index,abs(float(current_reference_points[0,1]-current_neck_center[1]))/current_normalization_length,current_head_length,(current_head_length/current_box_height if current_box_height is not None else None)))
        for current_group_name,current_segment_pairs in REFERENCE_SEGMENT_GROUPS.items():
            current_group_lengths=[]
            current_group_weights=[]
            current_group_pairs=[]
            current_segment_scores=[]
            for current_parent_index,current_child_index in current_segment_pairs:
                current_segment_weight=float(min(current_reference_points[[current_parent_index,current_child_index],2]))
                if current_segment_weight<REFERENCE_CONFIDENCE_THRESHOLD:
                    continue
                current_segment_length=float(np.linalg.norm(current_reference_points[current_child_index,:2]-current_reference_points[current_parent_index,:2]))
                if current_segment_length<5:
                    continue
                current_group_lengths.append(current_segment_length/current_normalization_length)
                current_group_weights.append(min(current_segment_weight,current_anchor_weight))
                current_segment_scores.append(current_segment_weight)
                current_group_pairs.append([current_parent_index,current_child_index])
            if current_group_lengths:
                current_arms_overlap=False
                if current_group_name=='upper_arm' and len(current_group_lengths)==2:
                    current_mean_arm_length=float(np.mean(current_group_lengths))*current_normalization_length
                    current_arms_overlap=all(np.linalg.norm(current_reference_points[current_first_index,:2]-current_reference_points[current_second_index,:2]) <= REFERENCE_ARM_OVERLAP_FRACTION*current_mean_arm_length for current_first_index,current_second_index in ((2,5),(3,6)))
                current_longest_index=int(np.argmax(current_segment_scores if current_arms_overlap else current_group_lengths))
                current_group_samples[current_group_name].append((current_group_lengths[current_longest_index],current_group_weights[current_longest_index],current_reference_index,current_group_pairs[current_longest_index],[{'joint_pair':current_group_pairs[current_candidate_index],'ratio':current_group_lengths[current_candidate_index],'length_px':current_group_lengths[current_candidate_index]*current_normalization_length,'height_ratio':(current_group_lengths[current_candidate_index]*current_normalization_length/current_box_height if current_box_height is not None else None),'confidence':current_group_weights[current_candidate_index],'segment_confidence':current_segment_scores[current_candidate_index],'selected_for_observation':current_candidate_index==current_longest_index,'selection_reason':('겹친 양팔 중 관절 점수 우선' if current_arms_overlap else '관측 내 최장 유효 관절 쌍')} for current_candidate_index in range(len(current_group_lengths))]))
    current_estimated_ratios={}
    current_evidence_records={}
    for current_group_name,current_sample_rows in current_group_samples.items():
        if not current_sample_rows:
            raise ValueError(f'참조에서 {current_group_name} 비율을 추정할 수 없습니다. 관절이 보이는 정면 전신 이미지를 추가하세요.')
        current_sample_values=np.array([current_sample_row[0] for current_sample_row in current_sample_rows])
        current_sample_weights=np.array([current_sample_row[1] for current_sample_row in current_sample_rows])
        # 투영 단축은 짧은 쪽 편향이다. 중앙값이 아닌 상위 관측군을 사용한다.
        # 단일 오검출의 과대 길이는 두 번째로 긴 관측과의 차이로 먼저 제외한다.
        current_inlier_mask=np.ones(len(current_sample_values),dtype=bool)
        if len(current_sample_values)>=3:
            current_sorted_values=np.sort(current_sample_values)
            current_upper_limit=current_sorted_values[-2]*REFERENCE_OUTLIER_MULTIPLIER
            current_inlier_mask &= current_sample_values<=current_upper_limit
        current_valid_indices=np.flatnonzero(current_inlier_mask)
        current_longest_index=int(current_valid_indices[np.argmax(current_sample_values[current_valid_indices])])
        current_estimated_ratios[current_group_name]=float(current_sample_values[current_longest_index])
        current_evidence_records[current_group_name]={'accepted_images':[current_sample_rows[current_longest_index][2]],'observations':[{'image':current_sample_row[2],'ratio':current_sample_row[0],'confidence':current_sample_row[1],'joint_pair':current_sample_row[3],'candidates':current_sample_row[4],'accepted':current_sample_index==current_longest_index,'reason':('최장 유효 관측' if current_sample_index==current_longest_index else '과대 이상치' if not current_inlier_mask[current_sample_index] else '더 긴 유효 관측 존재')} for current_sample_index,current_sample_row in enumerate(current_sample_rows)]}
    if not current_head_observations:
        raise ValueError('참조에서 얼굴과 양쪽 어깨가 보이는 관측을 찾을 수 없습니다.')
    current_head_values=np.array([current_row[3] for current_row in current_head_observations])
    current_head_valid=np.ones(len(current_head_values),dtype=bool)
    if len(current_head_values)>=3:
        current_head_valid &= current_head_values <= np.sort(current_head_values)[-2]*REFERENCE_OUTLIER_MULTIPLIER
    current_head_index=int(np.flatnonzero(current_head_valid)[np.argmax(current_head_values[current_head_valid])])
    current_head_ratio=float(current_head_values[current_head_index])
    current_axis_record={'nose_shoulder_to_torso':current_head_ratio,'vertical_nose_shoulder_to_torso':current_head_ratio,'accepted_observations':[current_head_observations[current_head_index][2]],'observations':[{'observation':current_row[2],'ratio':current_row[0],'vertical_ratio':current_row[3],'length_px':current_row[4],'height_ratio':current_row[5],'confidence':current_row[1],'accepted':current_index==current_head_index,'reason':('최장 유효 관측' if current_index==current_head_index else '과대 이상치' if not current_head_valid[current_index] else '더 긴 유효 관측 존재')} for current_index,current_row in enumerate(current_head_observations)],'anchor':'코·어깨 중심·골반 중심의 2D 거리 비율; 목뼈 길이 아님'}
    return {'schema':REFERENCE_RATIO_SCHEMA,'ratios':current_estimated_ratios,'body_axis':current_axis_record,'evidence':current_evidence_records,'rejected':current_rejection_records,'image_count':len(current_reference_records),'observation_count':len(current_reference_records),'normalization':{'method':'bbox_height_common_torso' if current_common_torso_height is not None else 'per_observation_torso','common_torso_to_height':current_common_torso_height},'method':'검출 상자 높이와 공통 몸통 기준 정규화·과대 이상치 제외·부위별 최장 유효 관측','limitations':'2D 몸통 정규화 비율은 몸통의 투영 단축에 영향을 받으며 실제 3D 체형 복원이 아님.'}


def calculate_reference_torso_gain(current_body_positions,current_ratio_record):
    """얼굴과 골반을 고정하고 참조의 코·어깨·골반 관계로 몸통 배율을 추정한다."""
    current_axis_record=current_ratio_record.get('body_axis')
    if current_axis_record is None:
        if current_ratio_record.get('schema') != 'body18-reference-ratios-v2':
            raise ValueError('참조 몸통 축 비율이 없습니다.')
        return 1.0
    current_vertical_axis=current_ratio_record.get('schema') == 'body18-reference-ratios-v4'
    current_target_ratio=current_axis_record.get('vertical_nose_shoulder_to_torso') if current_vertical_axis else current_axis_record.get('nose_shoulder_to_torso')
    if type(current_target_ratio) not in (int,float) or not np.isfinite(current_target_ratio) or current_target_ratio<=0:
        raise ValueError('참조 얼굴·몸통 비율 오류')
    current_positions=np.asarray(current_body_positions,dtype=float)
    if current_positions.ndim!=3 or current_positions.shape[1]!=18 or current_positions.shape[2] not in (2,3) or not np.isfinite(current_positions).all():
        raise ValueError('몸통 축 보정 관절 형식 오류')
    current_shoulder_centers=current_positions[:,[2,5]].mean(1)
    current_hip_centers=current_positions[:,[8,11]].mean(1)
    current_torso_lengths=np.abs(current_shoulder_centers[:,1]-current_hip_centers[:,1]) if current_vertical_axis else np.linalg.norm(current_shoulder_centers-current_hip_centers,axis=-1)
    current_head_lengths=np.abs(current_positions[:,0,1]-current_shoulder_centers[:,1]) if current_vertical_axis else np.linalg.norm(current_positions[:,0]-current_shoulder_centers,axis=-1)
    if np.any(current_torso_lengths<=0) or np.any(current_head_lengths<=0):
        raise ValueError('얼굴·몸통 기준 길이가 0입니다.')
    current_source_ratio=float(np.median(current_head_lengths/current_torso_lengths))
    current_torso_gain=(1+current_source_ratio)/(1+current_target_ratio)
    if not REFERENCE_AXIS_GAIN_MINIMUM<=current_torso_gain<=REFERENCE_AXIS_GAIN_MAXIMUM:
        raise ValueError('참조 몸통 축 보정 배율이 허용 범위를 벗어났습니다.')
    return current_torso_gain


def apply_reference_proportions(current_body_positions,current_ratio_record):
    current_target_ratios=current_ratio_record['ratios']
    if set(current_target_ratios)!=set(REFERENCE_SEGMENT_GROUPS) or any(not np.isfinite(current_ratio_value) or current_ratio_value<=0 for current_ratio_value in current_target_ratios.values()):
        raise ValueError('참조 신체 비율 계약 오류')
    current_adjusted_positions=current_body_positions.copy()
    current_hip_centers=current_body_positions[:,[8,11]].mean(1)
    current_torso_gain=calculate_reference_torso_gain(current_body_positions,current_ratio_record)
    current_original_shoulder_center=current_body_positions[:,[2,5]].mean(1)
    current_shoulder_center=current_hip_centers+(current_original_shoulder_center-current_hip_centers)*current_torso_gain
    current_adjusted_positions[:,1]+=current_shoulder_center-current_original_shoulder_center
    current_torso_lengths=np.linalg.norm(current_shoulder_center-current_hip_centers,axis=-1)
    current_base_torso=float(np.median(current_torso_lengths))
    if current_base_torso<=0:
        raise ValueError('SOMA 몸통 길이 오류')
    for current_group_name,current_center_positions,current_joint_pair in [('shoulder_width',current_shoulder_center,(2,5)),('hip_width',current_hip_centers,(8,11))]:
        current_direction_vectors=current_body_positions[:,current_joint_pair[1]]-current_body_positions[:,current_joint_pair[0]]
        current_vector_lengths=np.linalg.norm(current_direction_vectors,axis=-1,keepdims=True)
        if np.any(current_vector_lengths<=0): raise ValueError('SOMA 너비 관절 길이 오류')
        current_half_vectors=current_direction_vectors/current_vector_lengths*current_target_ratios[current_group_name]*current_base_torso/2
        current_adjusted_positions[:,current_joint_pair[0]]=current_center_positions-current_half_vectors
        current_adjusted_positions[:,current_joint_pair[1]]=current_center_positions+current_half_vectors
    for current_group_name in ('upper_arm','forearm','thigh','shin'):
        for current_parent_index,current_child_index in REFERENCE_SEGMENT_GROUPS[current_group_name]:
            current_direction_vectors=current_body_positions[:,current_child_index]-current_body_positions[:,current_parent_index]
            current_vector_lengths=np.linalg.norm(current_direction_vectors,axis=-1,keepdims=True)
            if np.any(current_vector_lengths<=0): raise ValueError('SOMA 팔다리 길이 오류')
            current_adjusted_positions[:,current_child_index]=current_adjusted_positions[:,current_parent_index]+current_direction_vectors/current_vector_lengths*current_target_ratios[current_group_name]*current_base_torso
    return current_adjusted_positions
