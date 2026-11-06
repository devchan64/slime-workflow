"""Kimodo 원본 모션에서 사용자 선택 프레임을 독립 사본으로 보존한다."""
import hashlib
import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import numpy as np

from generators.kimodo.contracts import KIMODO_JOB_STORAGE, KIMODO_WORKSPACE_ROOT

KIMODO_KEYFRAME_STORAGE = KIMODO_WORKSPACE_ROOT / '.tmp/manager-current/kimodo-keyframes'
KIMODO_JOB_IDENTIFIER_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
KIMODO_ATTEMPT_IDENTIFIER_PATTERN = re.compile(r'[a-f0-9]{32}')
KIMODO_FRAME_ARRAY_SHAPES = {'local_rot_mats': (77, 3, 3), 'global_rot_mats': (77, 3, 3), 'posed_joints': (77, 3), 'root_positions': (3,), 'smooth_root_pos': (3,), 'global_root_heading': (2,), 'foot_contacts': (6,), 'posed_joints_norootpos': (30, 3)}
KIMODO_KEYFRAME_IDENTIFIER_PATTERN = re.compile(r'[a-f0-9]{32}')
KIMODO_KEYFRAME_LIMIT = 20


def validate_kimodo_keyframe_placements(current_keyframe_placements, current_frame_count):
    """사용자 화면 기준 1부터 시작하는 출력 프레임 배치를 검증한다."""
    if not isinstance(current_keyframe_placements, list) or not 1 <= len(current_keyframe_placements) <= KIMODO_KEYFRAME_LIMIT:
        raise ValueError(f'키프레임은 1~{KIMODO_KEYFRAME_LIMIT}개를 지정하세요.')
    current_seen_frames = set()
    for current_placement_record in current_keyframe_placements:
        if not isinstance(current_placement_record, dict) or set(current_placement_record) != {'id', 'frame'}:
            raise ValueError('키프레임 배치에는 id와 frame이 필요합니다.')
        current_identifier_value = current_placement_record['id']
        current_frame_number = current_placement_record['frame']
        if not isinstance(current_identifier_value, str) or not KIMODO_KEYFRAME_IDENTIFIER_PATTERN.fullmatch(current_identifier_value):
            raise ValueError('키프레임 ID 형식 오류')
        if type(current_frame_number) is not int or not 1 <= current_frame_number <= current_frame_count or current_frame_number in current_seen_frames:
            raise ValueError('출력 프레임은 범위 내의 중복 없는 정수여야 합니다.')
        current_seen_frames.add(current_frame_number)
    return sorted((dict(current_placement_record) for current_placement_record in current_keyframe_placements), key=lambda current_placement_record: current_placement_record['frame'])


def load_kimodo_keyframe_snapshot(current_keyframe_root, current_keyframe_identifier):
    """저장된 키프레임의 메타데이터·해시·배열을 검증한다."""
    if not isinstance(current_keyframe_identifier, str) or not KIMODO_KEYFRAME_IDENTIFIER_PATTERN.fullmatch(current_keyframe_identifier):
        raise ValueError('키프레임 ID 형식 오류')
    current_snapshot_root = current_keyframe_root / current_keyframe_identifier
    if current_snapshot_root.is_symlink() or not current_snapshot_root.resolve().is_relative_to(current_keyframe_root.resolve()) or not current_snapshot_root.is_dir():
        raise ValueError(f'키프레임 경로 오류: {current_keyframe_identifier}')
    current_record_path = current_snapshot_root / 'record.json'
    if current_record_path.is_symlink() or not current_record_path.is_file():
        raise ValueError('키프레임 기록이 없습니다.')
    current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
    if not isinstance(current_record_value, dict) or set(current_record_value) != {'id','tag','source_job','source_attempt','source_frame','source_fps','source_motion','files'} or current_record_value['id'] != current_keyframe_identifier or current_record_value['source_fps'] != 30 or current_record_value['source_motion'] not in ('motion.npz','motion-in-place.npz'):
        raise ValueError('키프레임 기록 형식 오류')
    if not isinstance(current_record_value['files'], dict) or set(current_record_value['files']) != {'motion.npz','skeleton.json','preview.png'}:
        raise ValueError('키프레임 파일 목록 오류')
    for current_file_name, current_expected_digest in current_record_value['files'].items():
        current_file_path = current_snapshot_root / current_file_name
        if current_file_path.is_symlink() or not current_file_path.is_file() or not isinstance(current_expected_digest, str) or hashlib.sha256(current_file_path.read_bytes()).hexdigest() != current_expected_digest:
            raise ValueError(f'키프레임 파일 누락 또는 해시 불일치: {current_file_name}')
    current_skeleton_record = json.loads((current_snapshot_root/'skeleton.json').read_text(encoding='utf-8'))
    if not isinstance(current_skeleton_record, dict) or current_skeleton_record.get('skeleton') != 'somaskel77' or current_skeleton_record.get('fps') != 30 or len(current_skeleton_record.get('joint_names', [])) != 77 or len(current_skeleton_record.get('parents', [])) != 77:
        raise ValueError('키프레임 골격 계약 오류')
    with np.load(current_snapshot_root/'motion.npz', allow_pickle=False) as current_motion_archive:
        if set(current_motion_archive.files) != set(KIMODO_FRAME_ARRAY_SHAPES):
            raise ValueError('키프레임 모션 필드 오류')
        current_motion_arrays = {}
        for current_array_name, current_array_shape in KIMODO_FRAME_ARRAY_SHAPES.items():
            current_array_value = current_motion_archive[current_array_name]
            current_valid_dtype = np.issubdtype(current_array_value.dtype, np.integer) or np.issubdtype(current_array_value.dtype, np.floating) or (current_array_name == 'foot_contacts' and np.issubdtype(current_array_value.dtype, np.bool_))
            if current_array_value.shape != (1, *current_array_shape) or not current_valid_dtype or not np.isfinite(current_array_value).all():
                raise ValueError(f'키프레임 배열 오류: {current_array_name}')
            current_motion_arrays[current_array_name] = current_array_value.copy()
    return current_record_value, current_motion_arrays, current_skeleton_record


def snapshot_kimodo_keyframes(current_job_root, current_keyframe_placements, *, current_keyframe_storage=KIMODO_KEYFRAME_STORAGE):
    """검증된 키프레임을 새 작업의 입력 사본으로 보관한다."""
    current_snapshot_root = current_job_root / 'keyframes'
    current_snapshot_root.mkdir(exist_ok=False)
    current_snapshot_records = []
    for current_placement_record in current_keyframe_placements:
        current_keyframe_identifier = current_placement_record['id']
        current_record_value, _, _ = load_kimodo_keyframe_snapshot(current_keyframe_storage, current_keyframe_identifier)
        current_target_root = current_snapshot_root / current_keyframe_identifier
        if not current_target_root.exists():
            current_target_root.mkdir()
            for current_file_name in ('record.json','motion.npz','skeleton.json','preview.png'):
                shutil.copyfile(current_keyframe_storage/current_keyframe_identifier/current_file_name, current_target_root/current_file_name)
            load_kimodo_keyframe_snapshot(current_snapshot_root, current_keyframe_identifier)
        current_snapshot_records.append({'id':current_keyframe_identifier,'frame':current_placement_record['frame'],'source':current_record_value})
    return current_snapshot_records


def validate_kimodo_job_keyframe_snapshots(current_job_root, current_request_record):
    """재개와 추론 전에 작업별 입력 사본과 출처를 확인한다."""
    current_placements = validate_kimodo_keyframe_placements(current_request_record['keyframes'], current_request_record['frames'])
    current_saved_records = current_request_record.get('keyframe_snapshots')
    if not isinstance(current_saved_records, list) or len(current_saved_records) != len(current_placements):
        raise ValueError('작업의 키프레임 스냅샷 기록이 없습니다.')
    current_snapshots = []
    current_skeleton_signature = None
    for current_placement_record, current_saved_record in zip(current_placements,current_saved_records):
        if not isinstance(current_saved_record, dict) or set(current_saved_record) != {'id','frame','source'} or current_saved_record['id'] != current_placement_record['id'] or current_saved_record['frame'] != current_placement_record['frame']:
            raise ValueError('키프레임 배치와 스냅샷이 일치하지 않습니다.')
        current_source_record,current_motion_arrays,current_skeleton_record = load_kimodo_keyframe_snapshot(current_job_root/'keyframes',current_placement_record['id'])
        if current_source_record != current_saved_record['source']:
            raise ValueError('키프레임 출처 기록이 변경되었습니다.')
        current_signature_value = (current_skeleton_record['joint_names'],current_skeleton_record['parents'])
        if current_skeleton_signature is not None and current_signature_value != current_skeleton_signature:
            raise ValueError('키프레임 골격 구조가 서로 다릅니다.')
        current_skeleton_signature = current_signature_value
        current_snapshots.append(current_motion_arrays)
    return current_placements, current_snapshots


def build_kimodo_keyframe_constraints(current_job_root, current_request_record):
    """작업별 스냅샷을 공식 전신 키프레임 제약으로 변환한다."""
    from scipy.spatial.transform import Rotation
    current_placements, current_snapshots = validate_kimodo_job_keyframe_snapshots(current_job_root, current_request_record)
    current_origin_position = current_snapshots[0]['smooth_root_pos'][0,[0,2]].copy()
    current_constraint_record = {'type':'fullbody','frame_indices':[],'root_positions':[],'smooth_root_2d':[],'local_joints_rot':[]}
    for current_placement_record,current_motion_arrays in zip(current_placements,current_snapshots):
        current_root_position = current_motion_arrays['root_positions'][0].copy()
        current_root_position[[0,2]] -= current_origin_position
        current_smooth_position = current_motion_arrays['smooth_root_pos'][0,[0,2]] - current_origin_position
        current_constraint_record['frame_indices'].append(current_placement_record['frame']-1)
        current_constraint_record['root_positions'].append(current_root_position.tolist())
        current_constraint_record['smooth_root_2d'].append(current_smooth_position.tolist())
        current_constraint_record['local_joints_rot'].append(Rotation.from_matrix(current_motion_arrays['local_rot_mats'][0]).as_rotvec().tolist())
    return [current_constraint_record]


def list_kimodo_keyframe_records(current_keyframe_storage=KIMODO_KEYFRAME_STORAGE):
    """독립 보관된 키프레임 목록을 읽는다."""
    if not current_keyframe_storage.exists():
        return []
    current_keyframe_records = []
    for current_keyframe_root in sorted(current_keyframe_storage.iterdir()):
        if not re.fullmatch(r'[a-f0-9]{32}', current_keyframe_root.name):
            continue
        if current_keyframe_root.is_symlink() or not current_keyframe_root.is_dir():
            raise ValueError(f'키프레임 경로 오류: {current_keyframe_root.name}')
        current_record_path = current_keyframe_root / 'record.json'
        if current_record_path.is_symlink() or not current_record_path.is_file():
            raise ValueError(f'키프레임 기록 누락: {current_keyframe_root.name}')
        current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
        if current_record_value.get('id') != current_keyframe_root.name:
            raise ValueError(f'키프레임 ID 불일치: {current_keyframe_root.name}')
        current_keyframe_records.append(current_record_value)
    return current_keyframe_records


def save_kimodo_keyframe_record(current_job_identifier, current_attempt_identifier, current_frame_number, current_tag_text, *, current_job_storage=KIMODO_JOB_STORAGE, current_keyframe_storage=KIMODO_KEYFRAME_STORAGE):
    """원본 30fps 사용자 프레임(1부터 시작)을 검증하고 원본과 독립 보관한다."""
    if not isinstance(current_job_identifier, str) or not KIMODO_JOB_IDENTIFIER_PATTERN.fullmatch(current_job_identifier):
        raise ValueError('생성 ID 형식 오류')
    if not isinstance(current_attempt_identifier, str) or not KIMODO_ATTEMPT_IDENTIFIER_PATTERN.fullmatch(current_attempt_identifier):
        raise ValueError('시도 ID 형식 오류')
    if type(current_frame_number) is not int or current_frame_number < 1:
        raise ValueError('프레임 번호는 1 이상의 정수여야 합니다.')
    if not isinstance(current_tag_text, str) or not current_tag_text.strip() or len(current_tag_text.strip()) > 80:
        raise ValueError('태그는 1~80자의 문자열이어야 합니다.')
    current_attempt_root = current_job_storage / current_job_identifier / 'attempts' / current_attempt_identifier
    if not current_attempt_root.resolve().is_relative_to(current_job_storage.resolve()) or any(current_path.is_symlink() for current_path in (current_job_storage / current_job_identifier, current_attempt_root.parent, current_attempt_root)):
        raise ValueError('원본 작업 경로 오류')
    current_result_path = current_attempt_root / 'result.json'
    current_skeleton_path = current_attempt_root / 'skeleton.json'
    current_status_path = current_job_storage / current_job_identifier / 'status.json'
    for current_file_path in (current_status_path, current_result_path, current_skeleton_path):
        if current_file_path.is_symlink() or not current_file_path.is_file():
            raise ValueError(f'원본 결과 파일 누락: {current_file_path.name}')
    if json.loads(current_status_path.read_text()).get('status') != 'completed':
        raise ValueError('완료된 작업의 프레임만 저장할 수 있습니다.')
    current_result_record = json.loads(current_result_path.read_text())
    current_skeleton_record = json.loads(current_skeleton_path.read_text())
    if current_result_record.get('attempt') != current_attempt_identifier or current_result_record.get('fps') != 30 or current_skeleton_record.get('skeleton') != 'somaskel77' or current_skeleton_record.get('fps') != 30 or len(current_skeleton_record.get('joint_names', [])) != 77 or len(current_skeleton_record.get('parents', [])) != 77:
        raise ValueError('원본 시도 또는 SOMA 골격 계약 오류')
    current_frame_count = current_result_record.get('frames')
    if type(current_frame_count) is not int or not 1 <= current_frame_number <= current_frame_count:
        raise ValueError('원본 프레임 범위를 벗어났습니다.')
    current_horizontal_removed = current_result_record.get('remove_horizontal_motion', False)
    if type(current_horizontal_removed) is not bool:
        raise ValueError('원본 수평 이동 제거 기록 오류')
    current_motion_name = 'motion-in-place.npz' if current_horizontal_removed else 'motion.npz'
    current_motion_path = current_attempt_root / current_motion_name
    if current_motion_path.is_symlink() or not current_motion_path.is_file():
        raise ValueError(f'표시된 원본 모션 파일 누락: {current_motion_name}')
    current_preview_path = current_attempt_root / f'output-{current_frame_number-1:03d}.png'
    current_frame_hashes = current_result_record.get('frame_sha256')
    if current_preview_path.is_symlink() or not current_preview_path.is_file() or not isinstance(current_frame_hashes, list) or len(current_frame_hashes) != current_frame_count:
        raise ValueError('원본 프레임 미리보기 또는 해시 기록이 없습니다.')
    current_preview_bytes = current_preview_path.read_bytes()
    if not isinstance(current_frame_hashes[current_frame_number-1], str) or hashlib.sha256(current_preview_bytes).hexdigest() != current_frame_hashes[current_frame_number-1]:
        raise ValueError('원본 프레임 미리보기 해시가 일치하지 않습니다.')
    with np.load(current_motion_path, allow_pickle=False) as current_motion_archive:
        if set(current_motion_archive.files) != set(KIMODO_FRAME_ARRAY_SHAPES):
            raise ValueError('원본 모션 필드 오류')
        current_frame_arrays = {}
        for current_array_name, current_array_shape in KIMODO_FRAME_ARRAY_SHAPES.items():
            current_array_value = current_motion_archive[current_array_name]
            current_valid_dtype = np.issubdtype(current_array_value.dtype, np.integer) or np.issubdtype(current_array_value.dtype, np.floating) or (current_array_name == 'foot_contacts' and np.issubdtype(current_array_value.dtype, np.bool_))
            if current_array_value.shape != (current_frame_count, *current_array_shape) or not current_valid_dtype or not np.isfinite(current_array_value).all():
                raise ValueError(f'원본 모션 배열 오류: {current_array_name}')
            current_frame_arrays[current_array_name] = current_array_value[current_frame_number-1:current_frame_number].copy()
    current_keyframe_storage.mkdir(parents=True, exist_ok=True)
    current_keyframe_identifier = uuid.uuid4().hex
    current_temporary_root = Path(tempfile.mkdtemp(prefix='.keyframe-', dir=current_keyframe_storage))
    try:
        np.savez_compressed(current_temporary_root / 'motion.npz', **current_frame_arrays)
        shutil.copyfile(current_skeleton_path, current_temporary_root / 'skeleton.json')
        (current_temporary_root / 'preview.png').write_bytes(current_preview_bytes)
        current_file_hashes = {current_file_name: hashlib.sha256((current_temporary_root / current_file_name).read_bytes()).hexdigest() for current_file_name in ('motion.npz', 'skeleton.json','preview.png')}
        current_keyframe_record = {'id': current_keyframe_identifier, 'tag': current_tag_text.strip(), 'source_job': current_job_identifier, 'source_attempt': current_attempt_identifier, 'source_frame': current_frame_number, 'source_fps': 30, 'source_motion':current_motion_name, 'files': current_file_hashes}
        (current_temporary_root / 'record.json').write_text(json.dumps(current_keyframe_record, ensure_ascii=False), encoding='utf-8')
        current_temporary_root.rename(current_keyframe_storage / current_keyframe_identifier)
        return current_keyframe_record
    except BaseException:
        shutil.rmtree(current_temporary_root, ignore_errors=True)
        raise
