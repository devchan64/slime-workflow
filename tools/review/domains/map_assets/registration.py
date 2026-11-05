"""등록부에서 검증한 신규 빌보드를 공용 콘텐츠 서비스에 전달한다."""
import hashlib
from pathlib import Path
from PIL import Image
from tools.review.common.map_tile_assets import load_registered_tiles
from tools.review.domains.map_assets.database_client import execute_content_api_request


def register_billboard_asset(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'requestId', 'expectedGeneration', 'asset'}:
        raise ValueError('requestId·expectedGeneration·asset이 필요합니다.')
    current_asset_record = current_request_payload['asset']
    current_image_record = current_asset_record['image']
    current_asset_root, current_registry_entries = load_registered_tiles()
    current_asset_root = Path(current_asset_root).resolve()
    current_image_path = (current_asset_root / current_image_record['path']).resolve()
    if not current_image_path.is_relative_to(current_asset_root / 'assets/billboards') or current_image_path.suffix != '.png':
        raise ValueError('빌보드 PNG 원본 경로 오류')
    current_image_hash = hashlib.sha256(current_image_path.read_bytes()).hexdigest()
    current_registered_image = current_registry_entries.get(current_image_record['path'])
    if not current_registered_image or any(current_registered_image[current_registry_key] != current_image_record[current_payload_key] for current_registry_key, current_payload_key in [('managementId', 'imageId'), ('version', 'version'), ('sha256', 'sha256'), ('width', 'width'), ('height', 'height')]):
        raise ValueError('빌보드 등록부와 입력 불일치')
    if current_image_hash != current_image_record['sha256']:
        raise ValueError('빌보드 원본 해시 불일치')
    with Image.open(current_image_path) as current_image_value:
        if current_image_value.size != (current_image_record['width'], current_image_record['height']) or 'A' not in current_image_value.getbands():
            raise ValueError('투명 PNG 원본 크기 오류')
    return execute_content_api_request('POST', '/internal/v1/content/billboards', current_request_payload)
