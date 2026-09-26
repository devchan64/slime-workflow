"""Qwen 타일 생성 기록을 독립 검수 페이지로 복사한다."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.ui_assets import resolve_review_ui_asset

import hashlib
import json

import yaml
try:
    from .link_review_file import link_or_copy_review_file
except ImportError:
    from link_review_file import link_or_copy_review_file


WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TILE_REVIEW_RECORD_NAME = 'tile-review.json'
TILE_IMAGE_SUFFIXES = {'.png', '.webp'}


def reject_tile_record_duplicates(current_field_pairs):
    parsed_record_values = {}
    for current_field_name, current_field_value in current_field_pairs:
        if current_field_name in parsed_record_values:
            raise ValueError(f'타일 검수 기록 중복 필드: {current_field_name}')
        parsed_record_values[current_field_name] = current_field_value
    return parsed_record_values


def load_tile_review_record(record_file_path: Path) -> dict:
    """생성기가 남긴 타일 검수 기록의 형식과 해시를 검증한다."""
    record_values = json.loads(record_file_path.read_text(encoding='utf-8'), object_pairs_hook=reject_tile_record_duplicates)
    expected_record_fields = {'schemaVersion', 'kind', 'assetId', 'status', 'modelId', 'modelRevision', 'tileSize', 'tileability', 'heightSteps', 'ticket', 'variants', 'preview', 'mapPreview', 'qualityWarnings'}
    if not isinstance(record_values, dict) or set(record_values) != expected_record_fields or record_values['schemaVersion'] != 1 or record_values['kind'] != 'qwen-terrain-tile-review' or record_values['status'] != 'candidate-needs-user-review':
        raise ValueError(f'지원하지 않는 타일 검수 기록: {record_file_path}')
    if not isinstance(record_values['assetId'], str) or not record_values['assetId'] or not isinstance(record_values['tileSize'], list) or len(record_values['tileSize']) != 2 or any(type(current_dimension_value) is not int or current_dimension_value < 16 for current_dimension_value in record_values['tileSize']):
        raise ValueError(f'타일 검수 기본 정보가 올바르지 않습니다: {record_file_path}')
    if record_values['tileability'] not in {'repeat-x', 'repeat-y', 'repeat-both', 'none'} or type(record_values['heightSteps']) is not int or not isinstance(record_values['variants'], list) or not record_values['variants']:
        raise ValueError(f'타일 검수 반복 또는 역할 정보가 올바르지 않습니다: {record_file_path}')
    return record_values


def validate_record_file(record_root_path: Path, file_record: dict, allowed_suffixes: set[str]):
    if not isinstance(file_record, dict) or set(file_record) != {'file', 'sha256'} or not isinstance(file_record['file'], str) or Path(file_record['file']).name != file_record['file'] or Path(file_record['file']).suffix.lower() not in allowed_suffixes or not isinstance(file_record['sha256'], str):
        raise ValueError(f'타일 검수 파일 기록 형식이 올바르지 않습니다: {record_root_path}')
    resolved_file_path = (record_root_path / file_record['file']).resolve()
    if not resolved_file_path.is_relative_to(record_root_path) or not resolved_file_path.is_file() or resolved_file_path.is_symlink() or hashlib.sha256(resolved_file_path.read_bytes()).hexdigest() != file_record['sha256']:
        raise ValueError(f'타일 검수 파일 해시 또는 경로가 올바르지 않습니다: {file_record["file"]}')
    return resolved_file_path


def load_map_preview_record(record_root_path: Path, map_preview_record: dict | None):
    if map_preview_record is None:
        return None
    map_preview_path = validate_record_file(record_root_path, {'file': map_preview_record.get('file'), 'sha256': map_preview_record.get('sha256')} if isinstance(map_preview_record, dict) else {}, {'.yaml'})
    from generators.terrain.qwen_tile.map_preview import read_map_preview_snapshot
    map_preview_values, actual_snapshot_hash = read_map_preview_snapshot(map_preview_path)
    if actual_snapshot_hash != map_preview_record['sha256'] or map_preview_values['mapId'] != map_preview_record.get('mapId') or map_preview_values['targetCells'] != map_preview_record.get('targetCells'):
        raise ValueError('타일 검수 맵 스냅샷 기록이 일치하지 않습니다.')
    return map_preview_path, map_preview_values


def build_tile_review_page(review_data):
    """반복 이음새와 지정 셀 적용 상태를 한 페이지에서 표시한다."""
    template_path = resolve_review_ui_asset('tile-review.html')
    return template_path.read_text(encoding='utf-8').replace('__TILE_REVIEW_DATA__', json.dumps(review_data, ensure_ascii=False).replace('<', '\\u003c'))


def collect_tile_reviews(workflow_repository_root: Path, output_review_directory: Path, emit_review_trace):
    """.tmp 실행 폴더의 검증된 타일 기록만 현재 관리도구에 포함한다."""
    review_page_records = []
    temporary_root_path = workflow_repository_root / '.tmp'
    for record_file_path in sorted(temporary_root_path.glob(f'*/{TILE_REVIEW_RECORD_NAME}'), reverse=True):
        record_root_path = record_file_path.parent
        record_values = load_tile_review_record(record_file_path)
        destination_identifier = 'tile-' + hashlib.sha256(str(record_root_path.relative_to(workflow_repository_root)).encode('utf-8')).hexdigest()[:16]
        destination_root_path = output_review_directory / destination_identifier
        destination_root_path.mkdir()
        copied_variant_records = []
        for current_variant_record in record_values['variants']:
            if not isinstance(current_variant_record, dict) or set(current_variant_record) != {'role', 'file', 'sha256'} or current_variant_record['role'] not in {'ground', 'wall-front', 'wall-side'}:
                raise ValueError(f'타일 역할 기록이 올바르지 않습니다: {record_file_path}')
            source_variant_path = validate_record_file(record_root_path, {'file': current_variant_record['file'], 'sha256': current_variant_record['sha256']}, TILE_IMAGE_SUFFIXES)
            link_or_copy_review_file(source_variant_path, destination_root_path / source_variant_path.name)
            copied_variant_records.append({'role': current_variant_record['role'], 'file': source_variant_path.name})
        preview_path = None
        if record_values['preview'] is not None:
            source_preview_path = validate_record_file(record_root_path, record_values['preview'], {'.png'})
            link_or_copy_review_file(source_preview_path, destination_root_path / source_preview_path.name)
            preview_path = source_preview_path.name
        map_preview_result = load_map_preview_record(record_root_path, record_values['mapPreview'])
        map_preview_values = None
        if map_preview_result is not None:
            source_map_preview_path, map_preview_values = map_preview_result
            link_or_copy_review_file(source_map_preview_path, destination_root_path / source_map_preview_path.name)
        page_data = {'assetId': record_values['assetId'], 'tileSize': record_values['tileSize'], 'tileability': record_values['tileability'], 'heightSteps': record_values['heightSteps'], 'variants': copied_variant_records, 'preview': preview_path, 'mapPreview': map_preview_values, 'qualityWarnings': record_values['qualityWarnings']}
        (destination_root_path / 'tile-review.html').write_text(build_tile_review_page(page_data), encoding='utf-8')
        review_page_records.append({'id': destination_identifier, 'label': record_values['assetId'] + ' · 타일맵 검수', 'path': destination_identifier + '/tile-review.html', 'category': 'tile-review', 'anchorEditor': False, 'description': f'{record_root_path.relative_to(workflow_repository_root)} · {record_values["tileability"]} · {record_values["tileSize"][0]}×{record_values["tileSize"][1]}'})
        emit_review_trace('tile-review', str(record_root_path.relative_to(workflow_repository_root)))
    return review_page_records
