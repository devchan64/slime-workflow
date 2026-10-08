"""ANNY 기준점 후보 검수. 승인·리타기팅 적용은 제공하지 않는다."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid
from zoneinfo import ZoneInfo

import numpy as np
import yaml

from generators.hy_motion.contracts import UniqueConfigLoader
from tools.review.common.management_transport import send_management_json_response

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
LANDMARK_STORAGE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/anny-landmarks'
LANDMARK_ASSET_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / 'assets/animation-models/anny-neutral-v4'
LANDMARK_POINT_LABELS = {
    'shoulder_center': '어깨 관절 중심 후보 · 표면 클릭만으로 확정 불가',
    'elbow_medial': '팔꿈치 내측 기준점 후보',
    'elbow_lateral': '팔꿈치 외측 기준점 후보',
    'radial_styloid': '요골 경상돌기 후보',
    'ulnar_styloid': '척골 경상돌기 후보',
}
LANDMARK_IDENTIFIER_LABELS = {
    f'{current_side_name}_{current_point_name}': f'{current_side_label} · {current_point_label}'
    for current_side_name, current_side_label in (('left', '왼쪽'), ('right', '오른쪽'))
    for current_point_name, current_point_label in LANDMARK_POINT_LABELS.items()
}
LANDMARK_RECORD_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}/[a-f0-9]{32}'
LANDMARK_AXIS_EPSILON = 1e-8


def validate_exact_fields(current_input_record, expected_field_names):
    if not isinstance(current_input_record, dict) or set(current_input_record) != set(expected_field_names):
        raise ValueError(f'필드 불일치: 필요한 필드 {sorted(expected_field_names)}')


def load_landmark_source():
    current_manifest_record = yaml.load((LANDMARK_ASSET_DIRECTORY / 'manifest.yaml').read_text(), Loader=UniqueConfigLoader)
    for current_file_name in ('anny-rest-rig.npz', 'validation.json'):
        current_file_hash = sha256((LANDMARK_ASSET_DIRECTORY / current_file_name).read_bytes()).hexdigest()
        if current_file_hash != current_manifest_record['files'][current_file_name]['sha256']:
            raise ValueError(f'ANNY 원본 해시 불일치: {current_file_name}')
    current_validation_record = json.loads((LANDMARK_ASSET_DIRECTORY / 'validation.json').read_text())
    current_target_height = current_validation_record['height']
    if type(current_target_height) not in (int, float) or not np.isfinite(current_target_height) or current_target_height <= 0:
        raise ValueError('ANNY 검증 높이 오류')
    with np.load(LANDMARK_ASSET_DIRECTORY / 'anny-rest-rig.npz', allow_pickle=False) as current_rig_archive:
        current_vertex_values = current_rig_archive['vertices'].astype(float)
        current_triangle_values = current_rig_archive['faces'].astype(int)
    if current_vertex_values.ndim != 2 or current_vertex_values.shape[1] != 3 or not np.isfinite(current_vertex_values).all():
        raise ValueError('ANNY 정점 형식 오류')
    if current_triangle_values.ndim != 2 or current_triangle_values.shape[1] != 3 or current_triangle_values.min() < 0 or current_triangle_values.max() >= len(current_vertex_values):
        raise ValueError('ANNY 삼각형 형식 오류')
    current_source_height = float(np.ptp(current_vertex_values[:, 2]))
    if current_source_height <= 0:
        raise ValueError('ANNY 원본 높이 오류')
    current_source_floor = float(current_vertex_values[:, 2].min())
    current_scale_value = current_target_height / current_source_height
    current_vertex_values[:, 2] -= current_source_floor
    current_vertex_values *= current_scale_value
    return {
        'source': {'asset_id': current_manifest_record['asset_id'], 'version': current_manifest_record['version'],
                   'npz_sha256': current_manifest_record['files']['anny-rest-rig.npz']['sha256'],
                   'validation_sha256': current_manifest_record['files']['validation.json']['sha256'],
                   'coordinate_system': 'Z-up, +X left, -Y forward, meters',
                   'floor_offset_native': current_source_floor, 'scale_to_meters': current_scale_value},
        'vertices': current_vertex_values.tolist(), 'faces': current_triangle_values.tolist(),
        'landmarks': LANDMARK_IDENTIFIER_LABELS,
    }


def validate_landmark_draft(current_input_record, current_source_record):
    validate_exact_fields(current_input_record, ('source', 'points'))
    if current_input_record['source'] != current_source_record['source']:
        raise ValueError('원본·좌표 변환이 바뀌었습니다. 현재 ANNY 원본으로 다시 검수하세요.')
    current_point_records = current_input_record['points']
    if not isinstance(current_point_records, dict) or set(current_point_records) - set(LANDMARK_IDENTIFIER_LABELS):
        raise ValueError('알 수 없는 기준점')
    current_vertex_values = np.asarray(current_source_record['vertices'])
    for current_point_name, current_point_record in current_point_records.items():
        validate_exact_fields(current_point_record, ('position', 'method', 'evidence'))
        current_position_values = current_point_record['position']
        if not isinstance(current_position_values, list) or len(current_position_values) != 3 or any(type(current_axis_value) not in (int, float) or not np.isfinite(current_axis_value) for current_axis_value in current_position_values):
            raise ValueError(f'{current_point_name}: 유한한 XYZ 3개가 필요합니다.')
        if np.any(current_position_values < current_vertex_values.min(axis=0)) or np.any(current_position_values > current_vertex_values.max(axis=0)):
            raise ValueError(f'{current_point_name}: ANNY 메시 경계 밖 좌표')
        if current_point_record['method'] not in ('surface_pick', 'manual_xyz'):
            raise ValueError('지정 방식 오류')
        if not isinstance(current_point_record['evidence'], str) or not 1 <= len(current_point_record['evidence'].strip()) <= 2000:
            raise ValueError('각 기준점의 지정 근거를 1~2000자로 입력하세요.')
        if current_point_record['method'] == 'surface_pick':
            # 브라우저는 가시 삼각형에 속한 정점을 고른다. 수동 좌표를 표면 선택으로 가장하지 않는다.
            if np.linalg.norm(current_vertex_values - current_position_values, axis=1).min() > 1e-7:
                raise ValueError('표면 선택 좌표가 원본 정점과 일치하지 않습니다.')
    return current_input_record


def build_candidate_axes(current_point_records):
    """기준점의 기하학적 직교성만 검수한다. 임상 관절축으로 해석하지 않는다."""
    current_axis_records, current_warning_values = [], []
    for current_side_name in ('left', 'right'):
        current_required_names = [f'{current_side_name}_{current_point_name}' for current_point_name in LANDMARK_POINT_LABELS]
        current_missing_names = [current_point_name for current_point_name in current_required_names if current_point_name not in current_point_records]
        if current_missing_names:
            current_warning_values.append(f'{current_side_name}: 기준점 누락 {", ".join(current_missing_names)}')
            continue
        current_shoulder_point, current_medial_point, current_lateral_point, current_radial_point, current_ulnar_point = [np.asarray(current_point_records[current_point_name]['position'], dtype=float) for current_point_name in current_required_names]
        current_elbow_center = (current_medial_point + current_lateral_point) / 2
        current_wrist_center = (current_radial_point + current_ulnar_point) / 2
        for current_segment_name, current_origin_point, current_length_vector, current_cross_vector in (
            ('upper_arm', current_elbow_center, current_shoulder_point - current_elbow_center, current_lateral_point - current_medial_point),
            ('forearm', current_wrist_center, current_elbow_center - current_wrist_center, current_radial_point - current_ulnar_point),
        ):
            if np.linalg.norm(current_length_vector) <= LANDMARK_AXIS_EPSILON:
                current_warning_values.append(f'{current_side_name}/{current_segment_name}: 길이축 퇴화')
                continue
            current_length_vector /= np.linalg.norm(current_length_vector)
            current_cross_vector -= np.dot(current_cross_vector, current_length_vector) * current_length_vector
            if np.linalg.norm(current_cross_vector) <= LANDMARK_AXIS_EPSILON:
                current_warning_values.append(f'{current_side_name}/{current_segment_name}: 기준점 중복 또는 공선')
                continue
            current_cross_vector /= np.linalg.norm(current_cross_vector)
            current_axis_records.append({'name': f'{current_side_name}/{current_segment_name}', 'origin': current_origin_point.tolist(),
                                         'axes': [current_length_vector.tolist(), current_cross_vector.tolist(), np.cross(current_length_vector, current_cross_vector).tolist()]})
    current_warning_values.append('후보 축만 표시합니다. 견갑·쇄골·흉곽·손바닥 기준계, 원본 모션 대응 및 가동 범위는 미검증입니다.')
    return {'axes': current_axis_records, 'warnings': current_warning_values, 'status': 'candidate', 'anatomical_verified': False}


def resolve_landmark_record(current_record_identifier):
    if not isinstance(current_record_identifier, str) or re.fullmatch(LANDMARK_RECORD_PATTERN, current_record_identifier) is None:
        raise ValueError('기준점 기록 ID 형식 오류')
    current_record_path = LANDMARK_STORAGE_DIRECTORY / current_record_identifier / 'candidate.json'
    if not current_record_path.resolve().is_relative_to(LANDMARK_STORAGE_DIRECTORY.resolve()):
        raise ValueError('기록 경로 이탈')
    return current_record_path


def execute_landmark_command(current_command_name, current_input_record):
    if current_command_name == 'landmark-history':
        validate_exact_fields(current_input_record, ())
        return {'records': sorted([str(current_record_path.parent.relative_to(LANDMARK_STORAGE_DIRECTORY)) for current_record_path in LANDMARK_STORAGE_DIRECTORY.glob('*/*/candidate.json')], reverse=True)}
    current_source_record = load_landmark_source()
    if current_command_name == 'landmark-source':
        validate_exact_fields(current_input_record, ())
        return current_source_record
    if current_command_name == 'landmark-load':
        validate_exact_fields(current_input_record, ('id',))
        current_saved_record = json.loads(resolve_landmark_record(current_input_record['id']).read_text())
        validate_landmark_draft(current_saved_record['draft'], current_source_record)
        return {**current_saved_record, 'review': build_candidate_axes(current_saved_record['draft']['points'])}
    if current_command_name not in ('landmark-preview', 'landmark-save'):
        raise ValueError('지원하지 않는 기준점 명령')
    current_draft_record = validate_landmark_draft(current_input_record, current_source_record)
    current_result_record = {'draft': current_draft_record, 'review': build_candidate_axes(current_draft_record['points'])}
    if current_command_name == 'landmark-save':
        if not current_draft_record['points']:
            raise ValueError('최소 한 개 기준점을 지정하세요.')
        current_record_time = datetime.now(ZoneInfo('Asia/Seoul'))
        current_record_identifier = current_record_time.strftime('%Y-%m-%d_%H-%M-%S') + '/' + uuid.uuid4().hex
        current_result_record.update(id=current_record_identifier, created_at=current_record_time.isoformat(), status='candidate')
        current_record_path = resolve_landmark_record(current_record_identifier)
        current_record_path.parent.mkdir(parents=True, exist_ok=False)
        current_pending_path = current_record_path.with_suffix('.pending')
        with current_pending_path.open('x') as current_record_stream:
            json.dump(current_result_record, current_record_stream, ensure_ascii=False, indent=2, allow_nan=False)
        current_pending_path.rename(current_record_path)
        (current_record_path.parent / 'worker.log').write_text(f'{current_record_time.isoformat()}/anny-landmarks/saved 후보 저장 · 리타기팅 미적용\n')
    return current_result_record


def handle_landmark_request(current_http_handler):
    current_route_prefix = '/anny-landmarks/'
    if current_http_handler.command != 'POST' or not current_http_handler.path.startswith(current_route_prefix):
        return False
    try:
        current_request_record = json.loads(current_http_handler.rfile.read(int(current_http_handler.headers['Content-Length'])))
        current_result_record = execute_landmark_command(current_http_handler.path.removeprefix(current_route_prefix), current_request_record)
        send_management_json_response(current_http_handler, 200, current_result_record)
    except (ValueError, TypeError, KeyError, OSError) as current_request_error:
        send_management_json_response(current_http_handler, 400, {'error': str(current_request_error)})
    return True
