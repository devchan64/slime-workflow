"""Git으로 관리하는 SOMA 기준 자세 세트와 공식 양 끝 제약."""
import hashlib
import re
import shutil
from pathlib import Path

import numpy as np
import yaml

KIMODO_POSE_LIBRARY_ROOT = Path(__file__).with_name('pose-library')
KIMODO_POSE_FILE_NAMES = {'motion.npz', 'skeleton.yaml', 'render.yaml', 'render-front-left.png'}


def load_soma_pose_catalog():
    from generators.kimodo.contracts import UniqueConfigLoader
    current_catalog_record = yaml.load((KIMODO_POSE_LIBRARY_ROOT/'index.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_catalog_record, dict) or set(current_catalog_record) != {'schema_version', 'poses'} or current_catalog_record['schema_version'] != 1 or not isinstance(current_catalog_record['poses'], list):
        raise ValueError('SOMA 기준 자세 목록 계약 오류')
    current_pose_mapping = {}
    for current_pose_record in current_catalog_record['poses']:
        if not isinstance(current_pose_record, dict) or set(current_pose_record) != {'id','label','source_job','source_attempt','frame_index','heading_degrees','files'}:
            raise ValueError('SOMA 기준 자세 필드 오류')
        current_pose_identifier = current_pose_record['id']
        if not isinstance(current_pose_identifier,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',current_pose_identifier) or current_pose_identifier in current_pose_mapping:
            raise ValueError('SOMA 기준 자세 ID 오류')
        if not isinstance(current_pose_record['label'],str) or not current_pose_record['label'].strip() or type(current_pose_record['frame_index']) is not int or current_pose_record['frame_index'] < 0 or type(current_pose_record['heading_degrees']) not in (int,float) or not -180 <= current_pose_record['heading_degrees'] <= 180:
            raise ValueError('SOMA 기준 자세 설명·프레임·방향 오류')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_pose_record['source_job']) or not re.fullmatch(r'[a-f0-9]{32}',current_pose_record['source_attempt']):
            raise ValueError('SOMA 기준 자세 출처 오류')
        if not isinstance(current_pose_record['files'],dict) or set(current_pose_record['files']) != KIMODO_POSE_FILE_NAMES:
            raise ValueError('SOMA 기준 자세 구성 파일 오류')
        for current_file_name,current_file_digest in current_pose_record['files'].items():
            current_file_path = KIMODO_POSE_LIBRARY_ROOT/current_pose_identifier/current_file_name
            if not current_file_path.resolve().is_relative_to(KIMODO_POSE_LIBRARY_ROOT.resolve()) or current_file_path.is_symlink() or not current_file_path.is_file() or hashlib.sha256(current_file_path.read_bytes()).hexdigest() != current_file_digest:
                raise ValueError(f'SOMA 기준 자세 파일 누락·해시 불일치: {current_file_path}')
        current_pose_mapping[current_pose_identifier] = current_pose_record
    return current_pose_mapping


def load_soma_pose_arrays(current_pose_identifier):
    from generators.kimodo.contracts import UniqueConfigLoader
    current_pose_record = load_soma_pose_catalog().get(current_pose_identifier)
    if current_pose_record is None:
        raise ValueError('등록되지 않은 SOMA 기준 자세')
    current_pose_directory = KIMODO_POSE_LIBRARY_ROOT/current_pose_identifier
    current_skeleton_record = yaml.load((current_pose_directory/'skeleton.yaml').read_text(),Loader=UniqueConfigLoader)
    if set(current_skeleton_record) != {'skeleton','fps','parents','joint_names'} or current_skeleton_record['skeleton'] != 'somaskel77' or current_skeleton_record['fps'] != 30 or len(current_skeleton_record['parents']) != 77 or len(set(current_skeleton_record['joint_names'])) != 77:
        raise ValueError('SOMA 기준 스켈레톤 계약 오류')
    with np.load(current_pose_directory/'motion.npz',allow_pickle=False) as current_motion_archive:
        current_motion_arrays = {current_field_name:current_motion_archive[current_field_name] for current_field_name in current_motion_archive.files}
    current_required_shapes = {'local_rot_mats':(1,77,3,3),'global_rot_mats':(1,77,3,3),'posed_joints':(1,77,3),'root_positions':(1,3),'smooth_root_pos':(1,3),'global_root_heading':(1,2),'foot_contacts':(1,6),'posed_joints_norootpos':(1,30,3)}
    if set(current_motion_arrays) != set(current_required_shapes) or any(current_motion_arrays[current_field_name].shape != current_field_shape or not np.isfinite(current_motion_arrays[current_field_name]).all() for current_field_name,current_field_shape in current_required_shapes.items()):
        raise ValueError('SOMA 기준 자세 좌표·회전 계약 오류')
    return current_pose_record,current_motion_arrays


def build_soma_endpoint_records(current_pose_identifier,current_frame_count):
    from scipy.spatial.transform import Rotation
    if type(current_frame_count) is not int or not 30 <= current_frame_count <= 300:
        raise ValueError('SOMA 양 끝 제약 프레임 수 오류')
    current_pose_record,current_motion_arrays = load_soma_pose_arrays(current_pose_identifier)
    current_root_position = current_motion_arrays['root_positions'][0].copy()
    current_root_position[[0,2]] -= current_motion_arrays['smooth_root_pos'][0,[0,2]]
    current_rotation_vectors = Rotation.from_matrix(current_motion_arrays['local_rot_mats'][0]).as_rotvec().tolist()
    return [{'type':'fullbody','frame_indices':[0,current_frame_count-1], 'root_positions':[current_root_position.tolist()]*2,'smooth_root_2d':[[0.0,0.0]]*2,'local_joints_rot':[current_rotation_vectors]*2}]


def prepare_soma_endpoint_constraints(current_request_record,current_attempt_root,current_model_skeleton):
    from kimodo.constraints import load_constraints_lst
    from tools.review.common.generation_records import write_record_atomically
    current_pose_identifier = current_request_record.get('endpoint_pose_id')
    if not current_pose_identifier:
        return []
    current_pose_record,current_motion_arrays = load_soma_pose_arrays(current_pose_identifier)
    current_constraint_records = build_soma_endpoint_records(current_pose_identifier,current_request_record['frames'])
    current_snapshot_directory = current_attempt_root/'endpoint-pose'
    current_snapshot_directory.mkdir(exist_ok=True)
    for current_file_name in KIMODO_POSE_FILE_NAMES:
        shutil.copy2(KIMODO_POSE_LIBRARY_ROOT/current_pose_identifier/current_file_name,current_snapshot_directory/current_file_name)
    write_record_atomically(current_snapshot_directory/'source.json',current_pose_record)
    write_record_atomically(current_attempt_root/'endpoint-constraints.json',current_constraint_records)
    from datetime import datetime, timezone
    print(f'{datetime.now(timezone.utc).isoformat()}/kimodo/endpoint-constraints SOMA 양 끝 자세 적용: {current_pose_identifier} · 프레임 0/{current_request_record["frames"]-1}',flush=True)
    return load_constraints_lst(current_constraint_records,current_model_skeleton,device='cuda')
