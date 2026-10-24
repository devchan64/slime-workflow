"""투명 여백 크롭과 표시 위치 보존을 한 트랜잭션으로 저장한다."""
from tools.review.common.sprite_display_properties import normalize_sprite_property_precision
import hashlib
import io
import json
import os
import uuid
from pathlib import Path

from PIL import Image
import yaml

from tools.review.domains.map_assets.editor import read_editor_snapshot
from tools.review.common.sprite_display_properties import validate_sprite_display_properties
from tools.review.maintenance.sync_billboard_catalog import build_catalog_reference, serialize_billboard_catalog

CROP_HISTORY_DIRECTORY = Path(__file__).resolve().parents[4] / '.tmp/map-asset-crop'
CROP_ALPHA_THRESHOLD = 5
CROP_REFERENCE_TILE_WIDTH = 160
CROP_REFERENCE_TILE_HEIGHT = 80


def prepare_billboard_crop(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'revision', 'texture'}:
        raise ValueError('revision·texture가 필요합니다.')
    current_asset_root, current_source_paths, current_source_bytes, current_revision_hash, current_property_document, current_catalog_document = read_editor_snapshot()
    if current_request_payload['revision'] != current_revision_hash:
        raise ValueError('원본이 변경되었습니다. 목록을 새로고침하고 다시 확인하세요.')
    current_texture_key = current_request_payload['texture']
    current_catalog_entry = next((current_asset_entry for current_asset_entry in current_catalog_document['billboards'] if current_asset_entry['texture_key'] == current_texture_key), None)
    if current_catalog_entry is None:
        raise ValueError('등록된 빌보드를 선택하세요.')
    current_image_path = current_asset_root / current_catalog_entry['source_file']['path']
    if current_catalog_entry.get('metadata_references') or current_image_path.with_suffix('.animation.json').exists():
        raise ValueError('프레임 시트는 크롭할 수 없습니다.')
    current_image_bytes = current_image_path.read_bytes()
    with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
        current_source_image = current_source_image.convert('RGBA')
        current_crop_bounds = current_source_image.getchannel('A').point(lambda current_alpha_value: 255 if current_alpha_value > CROP_ALPHA_THRESHOLD else 0).getbbox()
        if current_crop_bounds is None:
            raise ValueError('알파값 6 이상인 픽셀이 없어 크롭할 대상이 없습니다.')
        current_source_width, current_source_height = current_source_image.size
        current_output_image = current_source_image.crop(current_crop_bounds)
        current_output_stream = io.BytesIO()
        current_output_image.save(current_output_stream, format='PNG')
    current_original_values = current_property_document['data'][current_texture_key]
    if current_original_values.get('billboardAnchorMode') != 'tile-intersection':
        raise ValueError('하단 교차점 방식 빌보드만 크롭할 수 있습니다.')
    current_crop_left, current_crop_top, current_crop_right, current_crop_bottom = current_crop_bounds
    current_pixel_scale = current_original_values['displayHeight'] / current_source_height
    current_updated_values = {**current_original_values,
        'displayHeight': current_output_image.height * current_pixel_scale,
        'anchorX': current_original_values['anchorX'] + ((current_crop_left + current_crop_right - current_source_width) / 2) * current_pixel_scale / CROP_REFERENCE_TILE_WIDTH,
        'anchorY': current_original_values['anchorY'] + (current_crop_bottom - current_source_height) * current_pixel_scale / CROP_REFERENCE_TILE_HEIGHT}
    if current_original_values['groundFootprintColumns'] == current_original_values['groundFootprintRows']:
        current_old_shadow_width = min(current_original_values['displayHeight'] * .76, CROP_REFERENCE_TILE_WIDTH * 1.10)
        current_new_shadow_width = min(current_updated_values['displayHeight'] * .76, CROP_REFERENCE_TILE_WIDTH * 1.10)
        current_shadow_ratio = current_old_shadow_width / current_new_shadow_width
        for current_shadow_field in ('shadowScaleX', 'shadowScaleY'):
            current_updated_values[current_shadow_field] = current_original_values.get(current_shadow_field, 1) * current_shadow_ratio
    current_updated_values = normalize_sprite_property_precision(current_updated_values)
    current_preview_token = hashlib.sha256((json.dumps({**current_request_payload, 'alpha_threshold': CROP_ALPHA_THRESHOLD}, sort_keys=True) + hashlib.sha256(current_image_bytes).hexdigest()).encode()).hexdigest()
    current_preview_result = {'texture': current_texture_key, 'token': current_preview_token,
        'alpha_threshold': CROP_ALPHA_THRESHOLD,
        'changed': current_crop_bounds != (0, 0, current_source_width, current_source_height),
        'before': [current_source_width, current_source_height], 'after': list(current_output_image.size),
        'bounds': list(current_crop_bounds), 'properties': current_updated_values}
    return current_asset_root, current_source_paths, current_source_bytes, current_property_document, current_image_path, current_image_bytes, current_output_stream.getvalue(), current_preview_result


def preview_billboard_crop(current_request_payload):
    return prepare_billboard_crop(current_request_payload)[-1]


def save_billboard_crop(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'revision', 'texture', 'token'}:
        raise ValueError('revision·texture·token이 필요합니다.')
    current_validation_payload = {current_field_name: current_request_payload[current_field_name] for current_field_name in ('revision', 'texture')}
    current_asset_root, current_source_paths, current_source_bytes, current_property_document, current_image_path, current_image_bytes, current_output_bytes, current_preview_result = prepare_billboard_crop(current_validation_payload)
    if current_request_payload['token'] != current_preview_result['token']:
        raise ValueError('확인 이후 원본이 변경되었습니다. 다시 확인하세요.')
    if not current_preview_result['changed']:
        return {**current_preview_result, 'saved': False}
    current_property_document['data'][current_request_payload['texture']] = current_preview_result['properties']
    current_property_bytes = yaml.safe_dump(current_property_document, allow_unicode=True, sort_keys=False).encode()
    current_old_property_hash = hashlib.sha256(current_source_bytes[current_source_paths[0]]).hexdigest()
    current_new_property_hash = hashlib.sha256(current_property_bytes).hexdigest()
    current_registry_document = yaml.safe_load(current_source_bytes[current_source_paths[1]])
    current_relative_path = str(current_image_path.relative_to(current_asset_root))
    current_output_hash = hashlib.sha256(current_output_bytes).hexdigest()
    for current_asset_entry in current_registry_document['assets']:
        if current_asset_entry['path'] == current_relative_path:
            current_asset_entry.update(sha256=current_output_hash, width=current_preview_result['after'][0], height=current_preview_result['after'][1])
        if current_asset_entry['path'] == 'assets/maps/sprite-display-properties.yaml':
            current_asset_entry['sha256'] = current_new_property_hash
    current_backend_text = current_source_bytes[current_source_paths[3]].decode()
    if current_backend_text.count(current_old_property_hash) != 1:
        raise ValueError('공용 속성 소비자 잠금 해시 불일치')
    current_pending_files = {current_image_path: current_output_bytes, current_source_paths[0]: current_property_bytes,
        current_source_paths[1]: yaml.safe_dump(current_registry_document, allow_unicode=True, sort_keys=False).encode(),
        current_source_paths[3]: current_backend_text.replace(current_old_property_hash, current_new_property_hash).encode()}
    current_source_bytes[current_image_path] = current_image_bytes
    current_frontend_root = Path(os.environ.get('SLIME_FRONTEND_ROOT', current_asset_root.parent / 'slime-frontend'))
    current_original_hash = hashlib.sha256(current_image_bytes).hexdigest()
    for current_lock_name in ('map-assets.lock.yaml', 'sprite-assets.lock.yaml'):
        current_lock_path = current_frontend_root / current_lock_name
        current_lock_bytes = current_lock_path.read_bytes()
        current_source_bytes[current_lock_path] = current_lock_bytes
        if current_original_hash in current_lock_bytes.decode():
            current_pending_files[current_lock_path] = current_lock_bytes.decode().replace(current_original_hash, current_output_hash).encode()
    current_history_path = CROP_HISTORY_DIRECTORY / uuid.uuid4().hex
    current_history_path.mkdir(parents=True)
    for current_file_index, (current_file_path, current_file_bytes) in enumerate(current_source_bytes.items()):
        (current_history_path / str(current_file_index)).write_bytes(current_file_bytes)
        if current_file_path.read_bytes() != current_file_bytes:
            raise ValueError('저장 직전에 원본이 변경되었습니다.')
    (current_history_path / 'paths.json').write_text(json.dumps([str(current_file_path) for current_file_path in current_source_bytes]))
    (current_history_path / 'request.json').write_text(json.dumps(current_request_payload))
    try:
        for current_file_path, current_file_bytes in current_pending_files.items():
            current_temporary_path = current_file_path.with_name(current_file_path.name + '.crop-tmp')
            current_temporary_path.write_bytes(current_file_bytes)
            os.replace(current_temporary_path, current_file_path)
        current_source_paths[2].write_text(serialize_billboard_catalog(build_catalog_reference(current_asset_root)))
        current_result_record = {**current_preview_result, 'saved': True, 'history': current_history_path.name}
        (current_history_path / 'result.json').write_text(json.dumps(current_result_record))
        return current_result_record
    except Exception:
        for current_file_path, current_file_bytes in current_source_bytes.items():
            current_file_path.write_bytes(current_file_bytes)
        raise
