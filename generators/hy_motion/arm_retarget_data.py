"""실측 리그 계약을 수집한다. 해부학 기준점이나 비틀림 분배를 추측하지 않는다."""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import yaml
from generators.hy_motion.contracts import UniqueConfigLoader, SOURCE_BUNDLE_DIRECTORY, WORKFLOW_ROOT_DIRECTORY, load_generation_defaults

ARM_CONTRACT_PATH = Path(__file__).parent / 'config/arm-retarget-contract.yaml'
ARM_CONTRACT_FIELDS = {'schema_version', 'status', 'source_revision', 'target_asset', 'source_to_target_basis', 'source_joint_chains', 'target_bone_chains', 'target_segment_endpoints', 'policy'}


def load_arm_contract():
    current_contract_record = yaml.load(ARM_CONTRACT_PATH.read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_contract_record, dict) or set(current_contract_record) != ARM_CONTRACT_FIELDS or type(current_contract_record['schema_version']) is not int or current_contract_record['schema_version'] != 1 or current_contract_record['status'] != 'evidence_collection':
        raise ValueError('팔 리타기팅 수집 계약 필드 오류')
    if current_contract_record['source_revision'] != load_generation_defaults()['source_revision'] or current_contract_record['target_asset'] != 'assets/animation-models/anny-neutral-v4':
        raise ValueError('원본 revision 또는 ANNY 자산 계약 불일치')
    current_basis_matrix = np.asarray(current_contract_record['source_to_target_basis'], dtype=float)
    if current_basis_matrix.shape != (3, 3) or not np.isfinite(current_basis_matrix).all() or not np.allclose(current_basis_matrix.T @ current_basis_matrix, np.eye(3)) or not np.isclose(np.linalg.det(current_basis_matrix), 1):
        raise ValueError('좌표 변환은 오른손 직교 행렬이어야 합니다.')
    for current_field_name, current_list_length in (('source_joint_chains', 4), ('target_bone_chains', 7), ('target_segment_endpoints', 3)):
        current_side_records = current_contract_record[current_field_name]
        if not isinstance(current_side_records, dict) or set(current_side_records) != {'left', 'right'}:
            raise ValueError('좌우 체인 계약 오류')
        for current_name_values in current_side_records.values():
            if not isinstance(current_name_values, list) or len(current_name_values) != current_list_length or any(not isinstance(current_name_value, str) or not current_name_value for current_name_value in current_name_values) or len(set(current_name_values)) != current_list_length:
                raise ValueError('체인 이름·길이·중복 오류')
    if current_contract_record['policy'] != {'preserve_target_lengths': True, 'automatic_wrist_offset': False, 'anatomical_limits': None, 'intermediate_bone_twist_distribution': None, 'clinical_axes_verified': False}:
        raise ValueError('미검증 기준을 수집 계약에서 활성화할 수 없습니다.')
    return current_contract_record


def measure_arm_segments(current_segment_points):
    current_segment_points = np.asarray(current_segment_points, dtype=float)
    if current_segment_points.shape != (3, 3) or not np.isfinite(current_segment_points).all():
        raise ValueError('어깨·팔꿈치·손목은 유한한 [3,3] 배열이어야 합니다.')
    current_segment_vectors = np.diff(current_segment_points, axis=0)
    current_segment_lengths = np.linalg.norm(current_segment_vectors, axis=1)
    if np.any(current_segment_lengths <= 1e-8):
        raise ValueError('팔 세그먼트 길이 퇴화')
    current_direction_values = current_segment_vectors / current_segment_lengths[:, None]
    return {'lengths_m': current_segment_lengths.tolist(), 'directions': current_direction_values.tolist(),
            'bend_degrees': float(np.degrees(np.arccos(np.clip(np.dot(*current_direction_values), -1, 1))))}


def validate_named_chain(current_name_values, current_parent_values, current_chain_names):
    if any(current_bone_name not in current_name_values for current_bone_name in current_chain_names):
        raise ValueError('수집 계약의 본이 원본에 없습니다.')
    for current_parent_name, current_child_name in zip(current_chain_names, current_chain_names[1:]):
        if current_parent_values[current_name_values.index(current_child_name)] != current_name_values.index(current_parent_name):
            raise ValueError(f'체인 부모 불일치: {current_parent_name} → {current_child_name}')


def collect_arm_evidence():
    current_contract_record = load_arm_contract()
    current_source_directory = SOURCE_BUNDLE_DIRECTORY / 'scripts/gradio/static/assets/dump_wooden'
    current_target_directory = WORKFLOW_ROOT_DIRECTORY / current_contract_record['target_asset']
    current_source_names = json.loads((current_source_directory / 'joint_names.json').read_text())
    current_source_points = np.fromfile(current_source_directory / 'j_template.bin', dtype='<f4').reshape(-1, 3).astype(float)
    current_source_parents = np.fromfile(current_source_directory / 'kintree.bin', dtype='<i4')
    if not isinstance(current_source_names, list) or len(current_source_names) != 52 or len(set(current_source_names)) != 52 or current_source_points.shape != (52, 3) or current_source_parents.shape != (52,) or not np.isfinite(current_source_points).all():
        raise ValueError('HY-Motion Wooden 스켈레톤 계약 오류')
    current_manifest_record = yaml.load((current_target_directory / 'manifest.yaml').read_text(), Loader=UniqueConfigLoader)
    current_file_hashes = {}
    for current_file_name in ('anny-rest-rig.npz', 'validation.json'):
        current_file_hashes[current_file_name] = sha256((current_target_directory / current_file_name).read_bytes()).hexdigest()
        if current_file_hashes[current_file_name] != current_manifest_record['files'][current_file_name]['sha256']:
            raise ValueError('ANNY 자산 해시 불일치')
    with np.load(current_target_directory / 'anny-rest-rig.npz', allow_pickle=False) as current_target_archive:
        current_target_names = current_target_archive['bone_names'].tolist()
        current_target_parents = current_target_archive['bone_parents'].copy()
        current_target_matrices = current_target_archive['bone_matrices'].astype(float)
        current_target_vertices = current_target_archive['vertices'].astype(float)
    current_target_height = json.loads((current_target_directory / 'validation.json').read_text())['height']
    if len(set(current_target_names)) != len(current_target_names) or current_target_matrices.shape != (len(current_target_names), 4, 4) or current_target_parents.shape != (len(current_target_names),) or not np.isfinite(current_target_matrices).all() or current_target_vertices.ndim != 2 or current_target_vertices.shape[1] != 3 or not np.isfinite(current_target_vertices).all():
        raise ValueError('ANNY 기준 자세 배열 계약 오류')
    if type(current_target_height) not in (int, float) or not np.isfinite(current_target_height) or current_target_height <= 0 or np.ptp(current_target_vertices[:, 2]) <= 0:
        raise ValueError('ANNY 기준 높이 오류')
    current_target_floor = float(current_target_vertices[:, 2].min())
    current_target_scale = current_target_height / float(np.ptp(current_target_vertices[:, 2]))
    current_target_matrices[:, 2, 3] -= current_target_floor
    current_target_matrices[:, :3, 3] *= current_target_scale
    current_basis_matrix = np.asarray(current_contract_record['source_to_target_basis'])
    current_source_points = current_source_points @ current_basis_matrix.T
    current_side_results = {}
    for current_side_name in ('left', 'right'):
        current_source_chain = current_contract_record['source_joint_chains'][current_side_name]
        current_target_chain = current_contract_record['target_bone_chains'][current_side_name]
        validate_named_chain(current_source_names, current_source_parents, current_source_chain)
        validate_named_chain(current_target_names, current_target_parents, current_target_chain)
        current_source_metrics = measure_arm_segments([current_source_points[current_source_names.index(current_joint_name)] for current_joint_name in current_source_chain[1:]])
        current_target_metrics = measure_arm_segments([current_target_matrices[current_target_names.index(current_joint_name), :3, 3] for current_joint_name in current_contract_record['target_segment_endpoints'][current_side_name]])
        current_side_results[current_side_name] = {'source_metrics': current_source_metrics, 'target_metrics': current_target_metrics,
            'target_source_length_ratios': (np.asarray(current_target_metrics['lengths_m']) / current_source_metrics['lengths_m']).tolist(),
            'source_chain': [{'name': current_joint_name, 'index': current_source_names.index(current_joint_name), 'position': current_source_points[current_source_names.index(current_joint_name)].tolist()} for current_joint_name in current_source_chain],
            'target_chain': [{'name': current_joint_name, 'index': current_target_names.index(current_joint_name), 'bind_matrix': current_target_matrices[current_target_names.index(current_joint_name)].tolist()} for current_joint_name in current_target_chain]}
    for current_file_name in ('joint_names.json', 'j_template.bin', 'kintree.bin'):
        current_file_hashes['source/' + current_file_name] = sha256((current_source_directory / current_file_name).read_bytes()).hexdigest()
    current_file_hashes['source/body_model.py'] = sha256((SOURCE_BUNDLE_DIRECTORY / 'hymotion/pipeline/body_model.py').read_bytes()).hexdigest()
    current_file_hashes['contract'] = sha256(ARM_CONTRACT_PATH.read_bytes()).hexdigest()
    return {'schema_version': 1, 'kind': 'rig_evidence_not_anatomical_calibration', 'configured_source_revision': current_contract_record['source_revision'],
            'sha256': current_file_hashes, 'source_to_target_basis': current_contract_record['source_to_target_basis'],
            'target_floor_native': current_target_floor, 'target_scale_to_meters': current_target_scale,
            'sides': current_side_results, 'policy': current_contract_record['policy'],
            'blockers': ['GH/EL/EM/RS/US의 양쪽 리그 해부학 대응 미검증', '견갑·흉곽 기준계 미확보', 'ANNY 중간 본의 축 회전 분배 미검증', '관절 한도 프로필 미확보']}
