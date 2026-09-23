#!/usr/bin/env python3
"""이슬온 YAML 맵을 조립하고 검수 서버용 패키지를 만든다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import json
import shutil
import sys

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_DIRECTORY = WORKFLOW_ROOT / 'assets/world/isloon/maps'
REVIEW_TEMPLATE_PATH = WORKFLOW_ROOT / 'assets/world/isloon/map-review.html'
FRONTEND_ASSET_ROOT = WORKFLOW_ROOT.parent / 'slime-frontend/src/assets'

sys.path.insert(0, str(WORKFLOW_ROOT / 'generators/worldbuilding'))
from isloon_tiles import assemble_isloon_map


def build_isloon_map_review(map_path=None, output_root=None):
    map_paths = [Path(map_path).resolve()] if map_path else sorted(DEFAULT_MAP_DIRECTORY.glob('*.yaml'))
    if not map_paths:
        raise ValueError(f'등록된 이슬온 맵이 없습니다: {DEFAULT_MAP_DIRECTORY}')
    if output_root is None:
        timestamp_text = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
        output_root = WORKFLOW_ROOT / '.tmp' / timestamp_text / 'isloon-map-review'
    output_root = Path(output_root).resolve()
    if not output_root.is_relative_to((WORKFLOW_ROOT / '.tmp').resolve()):
        raise ValueError('검수 결과는 저장소 .tmp 하위여야 합니다.')
    output_root.mkdir(parents=True, exist_ok=False)
    map_output_directory = output_root / 'maps'
    map_output_directory.mkdir()
    from link_review_file import link_or_copy_review_file
    from isloon_tiles import load_yaml_document
    catalog_values = load_yaml_document(WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml')
    tile_output_directory = output_root / 'tiles'
    tile_output_directory.mkdir()
    tile_asset_records = {}
    tile_source_paths = {}
    for tile_record in catalog_values['tiles']:
        source_asset_path = (FRONTEND_ASSET_ROOT / tile_record['asset']).resolve()
        if not source_asset_path.is_file() or not source_asset_path.is_relative_to(FRONTEND_ASSET_ROOT.resolve()):
            raise FileNotFoundError(f'프론트엔드 타일 에셋 누락 또는 범위 밖 경로: {tile_record["asset"]}')
        output_asset_name = f'{tile_record["id"]}{source_asset_path.suffix.lower()}'
        link_or_copy_review_file(source_asset_path, tile_output_directory / output_asset_name)
        tile_asset_records[tile_record['id']] = {'file': f'tiles/{output_asset_name}', 'source': tile_record['asset']}
        tile_source_paths[tile_record['id']] = source_asset_path
    map_records = []
    for current_map_path in map_paths:
        assembled_map_path = map_output_directory / f'{current_map_path.stem}.json'
        assembled_map_values = assemble_isloon_map(current_map_path, assembled_map_path)
        from PIL import Image
        from PIL import ImageDraw
        isometric_tile_width = 64
        isometric_tile_height = 32
        half_tile_width = isometric_tile_width // 2
        half_tile_height = isometric_tile_height // 2
        map_columns = assembled_map_values['grid']['columns']
        map_rows = assembled_map_values['grid']['rows']
        preview_image = Image.new('RGBA', ((map_columns + map_rows) * half_tile_width, (map_columns + map_rows) * half_tile_height + isometric_tile_height), (16, 28, 22, 255))
        isometric_mask = Image.new('L', (isometric_tile_width, isometric_tile_height), 0)
        ImageDraw.Draw(isometric_mask).polygon(((half_tile_width, 0), (isometric_tile_width - 1, half_tile_height), (half_tile_width, isometric_tile_height - 1), (0, half_tile_height)), fill=255)
        tile_images = {}
        for tile_id, tile_path in tile_source_paths.items():
            source_tile_image = Image.open(tile_path).convert('RGBA').resize((128, 128), Image.Resampling.LANCZOS)
            projected_tile_image = source_tile_image.transform((isometric_tile_width, isometric_tile_height), Image.Transform.AFFINE, (1, 2, -half_tile_width, -1, 2, half_tile_width), Image.Resampling.BILINEAR)
            projected_tile_image.putalpha(isometric_mask)
            tile_images[tile_id] = projected_tile_image
        def project_tile_position(cell_values):
            center_x = map_rows * half_tile_width + (cell_values['column'] - cell_values['row']) * half_tile_width
            center_y = (cell_values['column'] + cell_values['row']) * half_tile_height + half_tile_height
            return center_x - half_tile_width, center_y - half_tile_height
        for layer_name in ('ground', 'object', 'roof'):
            for cell_values in sorted(assembled_map_values['layers'][layer_name], key=lambda current_cell: current_cell['column'] + current_cell['row']):
                preview_image.alpha_composite(tile_images[cell_values['tile']], project_tile_position(cell_values))
        start_marker_position = project_tile_position(assembled_map_values['spawn'])
        ImageDraw.Draw(preview_image).polygon(((start_marker_position[0] + half_tile_width, start_marker_position[1] + 8), (start_marker_position[0] + isometric_tile_width - 8, start_marker_position[1] + half_tile_height), (start_marker_position[0] + half_tile_width, start_marker_position[1] + isometric_tile_height - 8), (start_marker_position[0] + 8, start_marker_position[1] + half_tile_height)), outline=(255, 255, 255, 255), width=3)
        preview_path = map_output_directory / f'{current_map_path.stem}.preview.png'
        preview_image.save(preview_path)
        map_records.append({'id': assembled_map_values['map_id'], 'label': assembled_map_values['display_name'], 'file': f'maps/{assembled_map_path.name}', 'preview': f'maps/{preview_path.name}', 'source': str(current_map_path.relative_to(WORKFLOW_ROOT))})
    (output_root / 'map-index.json').write_text(json.dumps({'schema_version': 1, 'maps': map_records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output_root / 'tile-assets.json').write_text(json.dumps({'schema_version': 1, 'tiles': tile_asset_records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(REVIEW_TEMPLATE_PATH, output_root / 'map-review.html')
    (output_root / 'README.txt').write_text('검수 서버: python3 tools/review/serve.py --root "' + str(output_root) + '" --entry map-review.html\n', encoding='utf-8')
    return output_root


def run_isloon_map_review_build_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    print(build_isloon_map_review(arguments.map, arguments.output))


if __name__ == '__main__':
    run_isloon_map_review_build_command()
