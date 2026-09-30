"""맵·타일 원본의 제한된 읽기 전용 HTTP 제공 계약."""
import json
import mimetypes
from urllib.parse import unquote
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_tile


def read_map_asset_response(request_path_value):
    current_request_path = unquote(request_path_value)
    if current_request_path.startswith('/management/map-assets/maps/'):
        from tools.review.build_block_map_review import build_registered_map_review
        current_map_identifier = current_request_path.removeprefix('/management/map-assets/maps/')
        return json.dumps(build_registered_map_review(current_map_identifier),ensure_ascii=False).encode(),'application/json; charset=utf-8'
    if current_request_path.startswith('/management/map-assets/files/'):
        current_asset_relative = current_request_path.removeprefix('/management/map-assets/files/')
        current_asset_root,current_asset_records = load_registered_tiles()
        current_asset_path,_ = resolve_registered_tile(current_asset_relative,current_asset_root,current_asset_records)
        current_content_type = mimetypes.guess_type(current_asset_path.name)[0]
        if current_content_type not in {'image/png','image/webp','image/jpeg'}: raise ValueError('지원하지 않는 타일 형식')
        return current_asset_path.read_bytes(),current_content_type
    raise ValueError('등록되지 않은 맵 에셋 경로')
