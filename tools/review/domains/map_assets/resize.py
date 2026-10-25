"""등록된 정적 맵 이미지의 원본 크기 변경과 해시 동기화."""
import fcntl
import hashlib
import io
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset

RESIZE_ALLOWED_SIZES = (64, 128, 256, 384, 512)
RESIZE_STORAGE_DIRECTORY = Path(__file__).resolve().parents[4] / '.tmp/map-asset-resize'


def resize_registered_image(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'path', 'sha256', 'size'}:
        raise ValueError('path, sha256, size가 필요합니다.')
    selected_asset_path = current_request_payload['path']
    selected_image_size = current_request_payload['size']
    if type(selected_image_size) is not int or selected_image_size not in RESIZE_ALLOWED_SIZES:
        raise ValueError('크기는 64, 128, 256, 384, 512 중 선택하세요.')
    if not isinstance(selected_asset_path, str):
        raise ValueError('원본 경로는 문자열이어야 합니다.')
    RESIZE_STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with (RESIZE_STORAGE_DIRECTORY / 'resize.lock').open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
        current_asset_root, current_asset_records = load_registered_tiles()
        current_prefix_name = next((current_prefix for current_prefix in ('assets/tiles', 'assets/billboards', 'assets/buildings') if selected_asset_path.startswith(current_prefix + '/')), None)
        if current_prefix_name is None:
            raise ValueError('맵 이미지 원본만 변경할 수 있습니다.')
        current_image_path, current_image_provenance = resolve_registered_asset(selected_asset_path, current_asset_root, current_asset_records, current_prefix_name)
        if current_image_path.suffix != '.png' or current_image_path.with_suffix('.animation.json').exists():
            raise ValueError('정적 PNG만 지원합니다. 애니메이션 시트는 프레임 편집기를 사용하세요.')
        if current_request_payload['sha256'] != current_image_provenance['sha256']:
            raise ValueError('원본이 변경되었습니다. 목록을 다시 읽고 미리보기를 확인하세요.')
        current_original_bytes = current_image_path.read_bytes()
        with Image.open(io.BytesIO(current_original_bytes)) as current_source_image:
            current_source_width, current_source_height = current_source_image.size
            if selected_image_size > max(current_source_image.size):
                raise ValueError('원본보다 확대할 수 없습니다. 축소 전 원본을 복원한 뒤 진행하세요.')
            current_scale_ratio = selected_image_size / max(current_source_image.size)
            current_target_size = (max(1, round(current_source_width * current_scale_ratio)), max(1, round(current_source_height * current_scale_ratio)))
            current_output_stream = io.BytesIO()
            current_source_image.convert('RGBA').resize(current_target_size, Image.Resampling.LANCZOS).save(current_output_stream, format='PNG')
        current_output_bytes = current_output_stream.getvalue()
        current_output_hash = hashlib.sha256(current_output_bytes).hexdigest()
        current_registry_path = current_asset_root / 'asset-registry.yaml'
        current_registry_text = current_registry_path.read_text()
        current_entry_pattern = r'(?m)^- managementId: .*?(?=^- managementId: |\Z)'
        current_entry_count = 0
        def update_registry_entry(current_entry_match):
            nonlocal current_entry_count
            current_entry_text = current_entry_match[0]
            if '\n  path: ' + selected_asset_path + '\n' not in current_entry_text:
                return current_entry_text
            current_entry_count += 1
            current_entry_text = current_entry_text.replace(current_image_provenance['sha256'], current_output_hash)
            for current_dimension_name, current_dimension_value in zip(('width', 'height'), current_target_size):
                current_entry_text, current_dimension_count = re.subn(r'(?m)^  ' + current_dimension_name + r': \d+$', f'  {current_dimension_name}: {current_dimension_value}', current_entry_text)
                if not current_dimension_count:
                    current_entry_text = current_entry_text.replace('\n  path:', f'\n  {current_dimension_name}: {current_dimension_value}\n  path:')
            return current_entry_text
        current_registry_text = re.sub(current_entry_pattern, update_registry_entry, current_registry_text, flags=re.S)
        if current_entry_count != 1:
            raise ValueError('등록부 항목을 유일하게 확인할 수 없습니다.')
        current_pending_files = {current_image_path: current_output_bytes, current_registry_path: current_registry_text.encode()}
        current_frontend_root = Path(os.environ.get('SLIME_FRONTEND_ROOT', current_asset_root.parent / 'slime-frontend'))
        for current_lock_name in ('map-assets.lock.yaml', 'sprite-assets.lock.yaml'):
            current_lock_path = current_frontend_root / current_lock_name
            current_lock_text = current_lock_path.read_text()
            if current_image_provenance['sha256'] in current_lock_text:
                current_pending_files[current_lock_path] = current_lock_text.replace(current_image_provenance['sha256'], current_output_hash).encode()
        current_history_path = RESIZE_STORAGE_DIRECTORY / uuid.uuid4().hex
        current_history_path.mkdir()
        current_original_files = {current_file_path: current_file_path.read_bytes() for current_file_path in current_pending_files}
        (current_history_path / 'original.png').write_bytes(current_original_bytes)
        (current_history_path / 'request.json').write_text(json.dumps(current_request_payload))
        try:
            for current_file_path, current_file_bytes in current_pending_files.items():
                current_temporary_path = current_file_path.with_name(current_file_path.name + '.resize-tmp')
                current_temporary_path.write_bytes(current_file_bytes)
                current_temporary_path.replace(current_file_path)
        except Exception:
            for current_file_path, current_file_bytes in current_original_files.items():
                current_file_path.write_bytes(current_file_bytes)
            raise
        current_result_record = {'path': selected_asset_path, 'size': list(current_target_size), 'sha256': current_output_hash, 'history': current_history_path.name}
        (current_history_path / 'result.json').write_text(json.dumps(current_result_record))
        return current_result_record


def handle_map_resize_request(current_http_handler):
    from tools.review.common.management_transport import send_management_json_response
    if current_http_handler.command != 'POST' or urlsplit(current_http_handler.path).path not in ('/map-assets/resize','/map-assets/anchor-save','/map-assets/editor-list','/map-assets/editor-preview','/map-assets/editor-save','/map-assets/editor-crop-preview','/map-assets/editor-crop','/map-assets/editor-retire-preview','/map-assets/editor-retire','/map-assets/editor-map-edit-load','/map-assets/editor-map-edit-preview','/map-assets/editor-map-edit-save','/map-assets/database-seed','/map-assets/database-status','/map-assets/database-snapshot','/map-assets/database-restore'):
        return False
    try:
        if urlsplit(current_http_handler.path).path.startswith('/map-assets/database-'):
            from tools.review.domains.map_assets.database_commands import execute_content_database_command
            from tools.review.common.management_gateway import parse_management_request_json
            current_request_payload=parse_management_request_json(current_http_handler.rfile.read(int(current_http_handler.headers.get('Content-Length','0'))).decode())
            current_result_record=execute_content_database_command(urlsplit(current_http_handler.path).path.rsplit('/',1)[-1],current_request_payload)
            send_management_json_response(current_http_handler,200,current_result_record)
            return True
        current_request_payload = json.loads(current_http_handler.rfile.read(int(current_http_handler.headers['Content-Length'])))
        if '/editor-' in urlsplit(current_http_handler.path).path:
            from tools.review.domains.map_assets.editor import load_editor_catalog, preview_editor_changes, save_editor_changes
            if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
                from tools.review.domains.map_assets.database_editor import load_database_editor_catalog as load_editor_catalog, preview_database_editor_changes as preview_editor_changes, save_database_editor_changes as save_editor_changes
            from tools.review.domains.map_assets.crop import preview_billboard_crop, save_billboard_crop
            from tools.review.domains.map_assets.retirement import preview_billboard_retirement, execute_billboard_retirement
            if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
                from tools.review.domains.map_assets.database_images import preview_database_image_crop as preview_billboard_crop, save_database_image_change as save_billboard_crop
                from tools.review.domains.map_assets.database_retirement import preview_database_asset_retirement as preview_billboard_retirement, execute_database_asset_retirement as execute_billboard_retirement
            current_editor_handlers={'/map-assets/editor-crop-preview':preview_billboard_crop,'/map-assets/editor-crop':save_billboard_crop,'/map-assets/editor-list':load_editor_catalog,'/map-assets/editor-preview':preview_editor_changes,'/map-assets/editor-save':save_editor_changes,'/map-assets/editor-retire-preview':preview_billboard_retirement,'/map-assets/editor-retire':execute_billboard_retirement}
            from tools.review.domains.map_assets.map_editor import load_map_editor_document, preview_map_editor_changes, save_map_editor_changes
            current_editor_handlers.update({'/map-assets/editor-map-edit-load':load_map_editor_document,'/map-assets/editor-map-edit-preview':preview_map_editor_changes,'/map-assets/editor-map-edit-save':save_map_editor_changes})
            RESIZE_STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
            with (RESIZE_STORAGE_DIRECTORY/'resize.lock').open('a') as current_lock_stream:
                fcntl.flock(current_lock_stream.fileno(),fcntl.LOCK_EX)
                current_result_record=current_editor_handlers[urlsplit(current_http_handler.path).path](current_request_payload)
        elif urlsplit(current_http_handler.path).path.endswith('/anchor-save'):

            from tools.review.domains.map_assets.anchors import save_map_sprite_anchor
            if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
                from tools.review.domains.map_assets.database_editor import save_database_sprite_anchor as save_map_sprite_anchor
            RESIZE_STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
            with (RESIZE_STORAGE_DIRECTORY / 'resize.lock').open('a') as current_lock_stream:
                fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
                current_result_record=save_map_sprite_anchor(current_request_payload)
        else:
            if os.environ.get('SLIME_CONTENT_STORAGE')=='database' and 'texture' in current_request_payload:
                from tools.review.domains.map_assets.database_images import resize_database_asset_image
                current_result_record=resize_database_asset_image(current_request_payload)
            else:
                current_result_record=resize_registered_image(current_request_payload)
        send_management_json_response(current_http_handler, 200, current_result_record)
    except Exception as current_resize_error:
        send_management_json_response(current_http_handler, 400, {'error': str(current_resize_error)})
    return True
