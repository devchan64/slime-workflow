"""원본을 보존하면서 SOMA 모션의 수평 이동만 제거한다."""
import numpy as np


def remove_horizontal_translation(current_motion_output,current_joint_names):
    current_joint_positions = np.asarray(current_motion_output['posed_joints'])
    if current_joint_positions.ndim != 3 or current_joint_positions.shape[1:] != (77,3) or not len(current_joint_positions) or not np.isfinite(current_joint_positions).all():
        raise ValueError('수평 보정: SOMA77 관절 위치 오류')
    if len(current_joint_names) != 77 or current_joint_names.count('Hips') != 1:
        raise ValueError('수평 보정: Hips 관절 계약 오류')
    current_root_positions = current_joint_positions[:,current_joint_names.index('Hips')]
    current_translation_offsets = current_root_positions-current_root_positions[:1]
    current_translation_offsets = current_translation_offsets.copy()
    current_translation_offsets[:,1] = 0
    current_corrected_output = dict(current_motion_output)
    current_corrected_output['posed_joints'] = current_joint_positions-current_translation_offsets[:,None,:]
    for current_field_name in ('root_positions','smooth_root_pos'):
        current_field_positions = np.asarray(current_motion_output[current_field_name])
        if current_field_positions.shape != current_root_positions.shape or not np.isfinite(current_field_positions).all():
            raise ValueError(f'수평 보정: {current_field_name} 형식 오류')
        current_corrected_output[current_field_name] = current_field_positions-current_translation_offsets
    return current_corrected_output
