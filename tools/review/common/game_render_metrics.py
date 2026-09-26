"""게임 렌더 크기를 검수 빌드 시 읽어 출처가 있는 정적 사본으로 전달한다."""
import hashlib
import re


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
    if any(value <= 0 for value in current_metric_values.values()):
        raise ValueError('게임 렌더 크기는 양수여야 합니다.')
    current_metric_values['restHeightRatio'] = read_numeric_constant(actors_source_text,'HUMAN_REST_HEIGHT_RATIO')
    current_metric_values['sources'] = [{'path':source_file_path.relative_to(frontend_repository_path).as_posix(),'sha256':hashlib.sha256(source_file_path.read_bytes()).hexdigest()} for source_file_path in (metrics_source_path,actors_source_path)]
    return current_metric_values
