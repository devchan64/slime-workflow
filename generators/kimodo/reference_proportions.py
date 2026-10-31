"""복수 BODY18 관측의 신뢰도 가중 비율과 출력 전용 골격 보정."""
import numpy as np

REFERENCE_CONFIDENCE_THRESHOLD = 0.6
REFERENCE_SYMMETRY_THRESHOLD = 0.65
REFERENCE_SEGMENT_GROUPS = {
    'shoulder_width':((2,5),), 'hip_width':((8,11),),
    'upper_arm':((2,3),(5,6)), 'forearm':((3,4),(6,7)),
    'thigh':((8,9),(11,12)), 'shin':((9,10),(12,13)),
}
REFERENCE_RATIO_SCHEMA = 'body18-reference-ratios-v2'
REFERENCE_UPPER_QUANTILE = 0.8
REFERENCE_LONG_CLUSTER_RATIO = 0.9


def calculate_weighted_median(current_sample_values,current_sample_weights):
    current_sort_indices=np.argsort(current_sample_values)
    current_sorted_weights=np.asarray(current_sample_weights)[current_sort_indices]
    current_median_index=np.searchsorted(np.cumsum(current_sorted_weights),current_sorted_weights.sum()/2)
    return float(np.asarray(current_sample_values)[current_sort_indices[current_median_index]])


def estimate_reference_proportions(current_reference_records):
    current_group_samples={current_group_name:[] for current_group_name in REFERENCE_SEGMENT_GROUPS}
    current_rejection_records=[]
    for current_reference_index,current_reference_points in enumerate(current_reference_records,1):
        current_reference_points=np.asarray(current_reference_points,dtype=float)
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
        for current_group_name,current_segment_pairs in REFERENCE_SEGMENT_GROUPS.items():
            current_group_lengths=[]
            current_group_weights=[]
            for current_parent_index,current_child_index in current_segment_pairs:
                current_segment_weight=float(min(current_reference_points[[current_parent_index,current_child_index],2]))
                if current_segment_weight<REFERENCE_CONFIDENCE_THRESHOLD:
                    continue
                current_segment_length=float(np.linalg.norm(current_reference_points[current_child_index,:2]-current_reference_points[current_parent_index,:2]))
                if current_segment_length<5:
                    continue
                current_group_lengths.append(current_segment_length/current_torso_length)
                current_group_weights.append(min(current_segment_weight,current_anchor_weight))
            if len(current_group_lengths)==2 and min(current_group_lengths)/max(current_group_lengths)<REFERENCE_SYMMETRY_THRESHOLD:
                current_rejection_records.append({'image':current_reference_index,'segment':current_group_name,'reason':'좌우 길이 불일치·원근 단축 가능성'})
                continue
            if current_group_lengths:
                current_group_samples[current_group_name].append((float(np.mean(current_group_lengths)),float(np.mean(current_group_weights)),current_reference_index))
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
            current_upper_limit=current_sorted_values[-2]*1.35
            current_inlier_mask &= current_sample_values<=current_upper_limit
        current_valid_indices=np.flatnonzero(current_inlier_mask)
        current_order_indices=current_valid_indices[np.argsort(current_sample_values[current_valid_indices])]
        current_cumulative_weights=np.cumsum(current_sample_weights[current_order_indices])
        current_target_position=np.searchsorted(current_cumulative_weights,current_cumulative_weights[-1]*REFERENCE_UPPER_QUANTILE)
        current_upper_reference=current_sample_values[current_order_indices[current_target_position]]
        current_inlier_mask &= current_sample_values>=current_upper_reference*REFERENCE_LONG_CLUSTER_RATIO
        current_estimated_ratios[current_group_name]=calculate_weighted_median(current_sample_values[current_inlier_mask],current_sample_weights[current_inlier_mask])
        current_evidence_records[current_group_name]={'accepted_images':[current_sample_rows[current_sample_index][2] for current_sample_index in np.flatnonzero(current_inlier_mask)],'observations':[{'image':current_sample_row[2],'ratio':current_sample_row[0],'confidence':current_sample_row[1],'accepted':bool(current_inlier_mask[current_sample_index])} for current_sample_index,current_sample_row in enumerate(current_sample_rows)]}
    return {'schema':REFERENCE_RATIO_SCHEMA,'ratios':current_estimated_ratios,'evidence':current_evidence_records,'rejected':current_rejection_records,'image_count':len(current_reference_records),'observation_count':len(current_reference_records),'method':'몸통 정규화·과대 이상치 제외·신뢰도 가중 상위 80% 지점의 90% 이상 길이 관측군 중앙값','limitations':'2D 투영 비율 추정이며 실제 3D 체형 복원이 아님. 정면 전신 권장.'}


def apply_reference_proportions(current_body_positions,current_ratio_record):
    current_target_ratios=current_ratio_record['ratios']
    if set(current_target_ratios)!=set(REFERENCE_SEGMENT_GROUPS) or any(not np.isfinite(current_ratio_value) or current_ratio_value<=0 for current_ratio_value in current_target_ratios.values()):
        raise ValueError('참조 신체 비율 계약 오류')
    current_adjusted_positions=current_body_positions.copy()
    current_hip_centers=current_body_positions[:,[8,11]].mean(1)
    current_torso_lengths=np.linalg.norm(current_body_positions[:,1]-current_hip_centers,axis=-1)
    current_base_torso=float(np.median(current_torso_lengths))
    if current_base_torso<=0:
        raise ValueError('SOMA 몸통 길이 오류')
    for current_group_name,current_center_positions,current_joint_pair in [('shoulder_width',current_body_positions[:,1],(2,5)),('hip_width',current_hip_centers,(8,11))]:
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
