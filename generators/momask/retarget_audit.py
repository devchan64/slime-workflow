"""리그 애니메이션 적용 전 좌표 변환과 관절 대응의 수치 기록."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def write_coordinate_audit(output_directory_path, source_joint_frames, profile_record_values,
                           rest_bone_positions, motion_scale_value, source_manifest_record):
    """관측 좌표와 기준 골격의 차이를 기록하며 자세를 수정하지 않는다."""
    output_directory_path = Path(output_directory_path)
    coordinate_matrix_value = np.asarray(profile_record_values['coordinate_matrix'], dtype=float)
    source_joint_frames = np.asarray(source_joint_frames, dtype=float)
    converted_joint_frames = source_joint_frames @ coordinate_matrix_value.T
    source_reference_record = profile_record_values['source_reference']
    reference_joint_points = np.asarray(source_reference_record['joint_positions'], dtype=float) @ coordinate_matrix_value.T
    if not np.isfinite(converted_joint_frames).all():
        raise ValueError('좌표 변환 기록에 유한하지 않은 관절이 있습니다.')
    root_joint_index = profile_record_values['root_joint']
    root_translation_frames = (converted_joint_frames[:, root_joint_index] - converted_joint_frames[0, root_joint_index]) * motion_scale_value
    segment_audit_records = []
    for current_segment_record in profile_record_values['segments']:
        direction_audit_records = {}
        for current_direction_name in ('primary', 'secondary'):
            source_joint_pair = current_segment_record['source_' + current_direction_name]
            target_bone_pair = current_segment_record['target_' + current_direction_name]
            if source_joint_pair is None:
                continue
            source_direction_frames = converted_joint_frames[:, source_joint_pair[1]] - converted_joint_frames[:, source_joint_pair[0]]
            source_length_frames = np.linalg.norm(source_direction_frames, axis=1)
            target_rest_direction = np.asarray(rest_bone_positions[target_bone_pair[1]], dtype=float) - np.asarray(rest_bone_positions[target_bone_pair[0]], dtype=float)
            target_rest_length = float(np.linalg.norm(target_rest_direction))
            if np.any(source_length_frames <= 1e-8) or target_rest_length <= 1e-8:
                raise ValueError(f"좌표 변환 기록의 길이가 0인 구간: {current_segment_record['segment_id']}")
            source_unit_directions = source_direction_frames / source_length_frames[:, None]
            target_unit_direction = target_rest_direction / target_rest_length
            alignment_angle_frames = np.degrees(np.arctan2(np.linalg.norm(np.cross(source_unit_directions, target_unit_direction), axis=1), source_unit_directions @ target_unit_direction))
            reference_direction_value = reference_joint_points[source_joint_pair[1]] - reference_joint_points[source_joint_pair[0]]
            if np.linalg.norm(reference_direction_value) <= 1e-8:
                raise ValueError('원본 기준 골격의 구간 길이가 0입니다.')
            reference_direction_value /= np.linalg.norm(reference_direction_value)
            motion_angle_frames = np.degrees(np.arctan2(np.linalg.norm(np.cross(source_unit_directions, reference_direction_value), axis=1), source_unit_directions @ reference_direction_value))
            direction_audit_records[current_direction_name] = {
                'source_joint_pair': source_joint_pair, 'target_bone_pair': target_bone_pair,
                'target_rest_direction': target_rest_direction.tolist(),
                'target_rest_length': target_rest_length,
                'source_directions': source_direction_frames.tolist(),
                'source_lengths': source_length_frames.tolist(),
                'rest_alignment_degrees': alignment_angle_frames.tolist(),
                'rest_alignment_mean_degrees': float(alignment_angle_frames.mean()),
                'rest_alignment_max_degrees': float(alignment_angle_frames.max()),
                'source_reference_direction': reference_direction_value.tolist(),
                'source_reference_delta_degrees': motion_angle_frames.tolist(),
            }
        segment_audit_records.append({'segment_id': current_segment_record['segment_id'],
                                      'transfer_mode': current_segment_record['transfer_mode'],
                                      'target_bones': current_segment_record['target_bones'],
                                      'directions': direction_audit_records})
    coordinate_archive_path = output_directory_path / 'coordinate-transform.npz'
    np.savez_compressed(coordinate_archive_path, source_joints=source_joint_frames,
                        converted_joints=converted_joint_frames, root_translations=root_translation_frames)
    audit_record_values = {
        'schema_version': 1, 'stage': 'before_animation_application',
        'source': source_manifest_record, 'profile': profile_record_values,
        'coordinate_convention': 'converted = source @ coordinate_matrix.T',
        'motion_scale': float(motion_scale_value), 'scale_scope': 'root_translation_only',
        'frame_count': len(source_joint_frames), 'frame_index_base': 0,
        'source_rest_pose_available': True, 'source_reference': source_reference_record,
        'interpretation': 'rest_alignment는 대상 기준과의 차이, source_reference_delta는 고정 원본 기준과의 차이입니다. 동작 첫 프레임을 중립 자세로 사용하지 않습니다.',
        'rest_bone_positions': {current_bone_name: list(current_bone_position) for current_bone_name, current_bone_position in rest_bone_positions.items()},
        'coordinate_archive': coordinate_archive_path.name,
        'coordinate_archive_sha256': hashlib.sha256(coordinate_archive_path.read_bytes()).hexdigest(),
        'segments': segment_audit_records,
    }
    audit_record_path = output_directory_path / 'coordinate-transform.json'
    audit_record_path.write_text(json.dumps(audit_record_values, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/coordinate-audit 기록={audit_record_path} 프레임={len(source_joint_frames)} 루트배율={motion_scale_value:.6f}', flush=True)
    for current_segment_record in segment_audit_records:
        current_direction_record = current_segment_record['directions']['primary']
        print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/reference-delta 구간={current_segment_record["segment_id"]} 방식={current_segment_record["transfer_mode"]} 원본기준대비_평균={np.mean(current_direction_record["source_reference_delta_degrees"]):.3f}', flush=True)
        print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/coordinate-audit 구간={current_segment_record["segment_id"]} 원본={current_direction_record["source_joint_pair"]} 대상={current_direction_record["target_bone_pair"]} 기준방향차이_평균={current_direction_record["rest_alignment_mean_degrees"]:.3f} 최대={current_direction_record["rest_alignment_max_degrees"]:.3f}', flush=True)
    return audit_record_values
