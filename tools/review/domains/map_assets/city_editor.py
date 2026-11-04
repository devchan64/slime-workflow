"""도시맵 원장의 초안 검증과 조건부 저장."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.domains.map_assets.city_layout_validation import validate_content_city_document
from tools.review.common.sprite_display_properties import validate_sprite_display_properties

CITY_EDITOR_STORAGE_ROOT = Path(__file__).resolve().parents[4] / '.tmp/city-layout-editor'


def read_city_editor_snapshot(current_request_payload):
    if os.environ.get('SLIME_CONTENT_STORAGE') != 'database':
        raise ValueError('도시맵 편집에는 콘텐츠 DB가 필요합니다.')
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map'}:
        raise ValueError('map ID만 지정하세요.')
    current_city_identifier = current_request_payload['map']
    if not isinstance(current_city_identifier, str) or not re.fullmatch(r'[a-z0-9-]+', current_city_identifier):
        raise ValueError('도시맵 ID 오류')
    current_document_path = f'city_layouts/{current_city_identifier}.yaml'
    current_database_bundle = execute_content_api_request('GET', '/internal/v1/content/review-bundle?' + urlencode({'map': current_city_identifier}))
    if current_document_path not in current_database_bundle['documents']:
        raise ValueError('등록되지 않은 도시맵입니다.')
    return {'map': current_city_identifier, 'generation': current_database_bundle['generation'],
            'revision': current_database_bundle['revisions'][current_document_path],
            'document': current_database_bundle['documents'][current_document_path],
            'properties': current_database_bundle['documents']['sprite-display-properties.yaml']['data']}


def load_city_editor_document(current_request_payload):
    current_snapshot_record = read_city_editor_snapshot(current_request_payload)
    return {current_field_name: current_field_value for current_field_name, current_field_value in current_snapshot_record.items() if current_field_name != 'properties'}


def preview_city_editor_changes(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map', 'generation', 'revision', 'document'}:
        raise ValueError('map·generation·revision·document가 필요합니다.')
    current_original_record = read_city_editor_snapshot({'map': current_request_payload['map']})
    if (current_original_record['generation'], current_original_record['revision']) != (current_request_payload['generation'], current_request_payload['revision']):
        raise ValueError('도시 원장이 변경되었습니다. 다시 불러오세요.')
    current_document_record = current_request_payload['document']
    if not isinstance(current_document_record, dict) or current_document_record.get('managementId') != 'config.city-layouts.' + current_request_payload['map'] or current_document_record.get('data', {}).get('cityId') != current_request_payload['map']:
        raise ValueError('도시 원장의 ID가 일치하지 않습니다.')
    current_validation_record = validate_content_city_document(validate_sprite_display_properties(current_original_record['properties']), current_document_record)
    current_preview_token = hashlib.sha256(json.dumps(current_request_payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    CITY_EDITOR_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    (CITY_EDITOR_STORAGE_ROOT / (current_preview_token + '.json')).write_text(json.dumps(current_request_payload, ensure_ascii=False, allow_nan=False))
    return {**current_validation_record, 'changed': current_document_record != current_original_record['document'], 'token': current_preview_token}


def save_city_editor_changes(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map', 'generation', 'revision', 'document', 'token'}:
        raise ValueError('검증된 도시 초안과 token이 필요합니다.')
    current_validation_payload = {current_field_name: current_field_value for current_field_name, current_field_value in current_request_payload.items() if current_field_name != 'token'}
    current_preview_token = hashlib.sha256(json.dumps(current_validation_payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if current_request_payload['token'] != current_preview_token or not (CITY_EDITOR_STORAGE_ROOT / (current_preview_token + '.json')).is_file():
        raise ValueError('변경 내용을 먼저 검증하세요.')
    current_original_record = read_city_editor_snapshot({'map': current_request_payload['map']})
    if (current_original_record['generation'], current_original_record['revision']) != (current_request_payload['generation'], current_request_payload['revision']):
        raise ValueError('도시 원장이 변경되었습니다. 다시 불러오세요.')
    validate_content_city_document(validate_sprite_display_properties(current_original_record['properties']), current_request_payload['document'])
    current_database_payload = {'requestId': 'city-editor:' + current_preview_token, 'expectedGeneration': current_request_payload['generation'],
        'documents': [{'path': 'city_layouts/' + current_request_payload['map'] + '.yaml', 'revision': current_request_payload['revision'], 'document': current_request_payload['document']}]}
    return execute_content_api_request('POST', '/internal/v1/content/map-changes', current_database_payload)
