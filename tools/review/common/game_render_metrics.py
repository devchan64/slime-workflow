"""게임 렌더 크기를 검수 빌드 시 읽어 출처가 있는 정적 사본으로 전달한다."""
import hashlib
import re
import json
from pathlib import Path


WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
GAME_CITY_EXPORT_DIRECTORY = WORKFLOW_REPOSITORY_ROOT / 'assets/world/isloon/game-data'
GAME_CITY_MANIFEST_FILENAME = 'source-manifest.json'


def load_game_city_export_sources():
    game_manifest_path = GAME_CITY_EXPORT_DIRECTORY / GAME_CITY_MANIFEST_FILENAME
    if not game_manifest_path.is_file():
        raise ValueError(f'게임 도시 내보내기 원장 누락: {game_manifest_path}')
    game_manifest_record = json.loads(game_manifest_path.read_text(encoding='utf-8'))
    city_layout_hashes = game_manifest_record.get('cityLayoutSha256')
    game_block_height = game_manifest_record.get('blockHeight')
    if not isinstance(city_layout_hashes, dict) or not city_layout_hashes:
        raise ValueError('게임 도시 내보내기 원장의 도시 해시가 올바르지 않습니다.')
    if not isinstance(game_block_height, (int, float)) or game_block_height <= 0:
        raise ValueError('게임 도시 내보내기 원장의 블록 높이가 올바르지 않습니다.')
    game_source_records = [
        {
            'path': game_manifest_path.relative_to(WORKFLOW_REPOSITORY_ROOT).as_posix(),
            'sha256': hashlib.sha256(game_manifest_path.read_bytes()).hexdigest(),
        }
    ]
    for city_identifier in sorted(city_layout_hashes):
        city_export_path = GAME_CITY_EXPORT_DIRECTORY / f'{city_identifier}.json'
        if not city_export_path.is_file():
            raise ValueError(f'게임 도시 검수 사본 누락: {city_export_path}')
        city_export_record = json.loads(city_export_path.read_text(encoding='utf-8'))
        if city_export_record.get('id') != city_identifier:
            raise ValueError(f'게임 도시 검수 사본 식별자가 일치하지 않습니다: {city_export_path}')
        game_source_records.append(
            {
                'path': city_export_path.relative_to(WORKFLOW_REPOSITORY_ROOT).as_posix(),
                'sha256': hashlib.sha256(city_export_path.read_bytes()).hexdigest(),
            }
        )
    return game_block_height, game_source_records


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
