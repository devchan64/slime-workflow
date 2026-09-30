"""게임 렌더 크기를 검수 빌드 시 읽어 출처가 있는 정적 사본으로 전달한다."""
import hashlib
import re
import json
from pathlib import Path


WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def load_game_city_export_sources():
    from tools.review.common.map_asset_sources import MAP_REVIEW_IDENTIFIERS, MAP_SOURCE_BLOCK_HEIGHT, load_registered_map_review
    current_source_records = {}
    for current_map_identifier in MAP_REVIEW_IDENTIFIERS:
        for current_source_record in load_registered_map_review(current_map_identifier)['provenance']:
            current_source_records[current_source_record['source']] = {'repository':'slime-assets','path':current_source_record['source'],'sha256':current_source_record['sha256']}
    return MAP_SOURCE_BLOCK_HEIGHT, list(current_source_records.values())


def load_game_render_metrics(frontend_repository_path):
    metrics_source_path = frontend_repository_path / 'src/game/terrain/renderMetrics.ts'
    actors_source_path = frontend_repository_path / 'src/game/terrain/actors.ts'
    metrics_source_text = metrics_source_path.read_text()
    actors_source_text = actors_source_path.read_text()
    def read_numeric_constant(source_file_text, constant_identifier_text):
        matched_constant_values = re.findall(r'\bconst\s+' + re.escape(constant_identifier_text) + r'\s*=\s*(\d+(?:\.\d+)?)\s*;', source_file_text)
        if len(matched_constant_values) != 1:
            raise ValueError(f'게임 크기 상수 누락 또는 지원하지 않는 선언: {constant_identifier_text}')
        return float(matched_constant_values[0])
    required_metric_names = {'defaultZoom':'MAP_DEFAULT_ZOOM','tileWidth':'MAP_TILE_WIDTH','tileHeight':'MAP_TILE_HEIGHT','townTileWidth':'TOWN_TILE_WIDTH','townTileHeight':'TOWN_TILE_HEIGHT','characterHeight':'CHARACTER_BODY_HEIGHT','elevationHeight':'MAP_ELEVATION_HEIGHT','baseThickness':'MAP_BASE_THICKNESS'}
    current_metric_values = {key:read_numeric_constant(metrics_source_text,name) for key,name in required_metric_names.items()}
    game_block_height, game_source_records = load_game_city_export_sources()
    # 게임 원장의 60px 블록은 검수 화면의 마을 타일 높이(80px)로 정규화한다.
    review_block_height = current_metric_values['townTileHeight']
    if review_block_height <= 0 or game_block_height <= 0:
        raise ValueError('게임 또는 검수 블록 높이는 양수여야 합니다.')
    current_metric_values['wallHeight'] = review_block_height
    current_metric_values['canopyHeight'] = review_block_height
    if any(value <= 0 for value in current_metric_values.values()):
        raise ValueError('게임 렌더 크기는 양수여야 합니다.')
    current_metric_values['restHeightRatio'] = read_numeric_constant(actors_source_text,'HUMAN_REST_HEIGHT_RATIO')
    current_metric_values['sources'] = [{'path':source_file_path.relative_to(frontend_repository_path).as_posix(),'sha256':hashlib.sha256(source_file_path.read_bytes()).hexdigest()} for source_file_path in (metrics_source_path,actors_source_path)]
    current_metric_values['sources'].extend(game_source_records)
    return current_metric_values
