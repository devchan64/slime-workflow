#!/usr/bin/env python3
"""이슬온 YAML 맵을 조립하고 검수 서버용 패키지를 만든다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import shutil
import sys

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_PATH = WORKFLOW_ROOT / 'assets/world/isloon/maps/village-01.yaml'
REVIEW_TEMPLATE_PATH = WORKFLOW_ROOT / 'assets/world/isloon/map-review.html'

sys.path.insert(0, str(WORKFLOW_ROOT / 'generators/worldbuilding'))
from isloon_tiles import assemble_isloon_map


def build_isloon_map_review(map_path, output_root=None):
    map_path = Path(map_path).resolve()
    if output_root is None:
        timestamp_text = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
        output_root = WORKFLOW_ROOT / '.tmp' / timestamp_text / 'isloon-map-review'
    output_root = Path(output_root).resolve()
    if not output_root.is_relative_to((WORKFLOW_ROOT / '.tmp').resolve()):
        raise ValueError('검수 결과는 저장소 .tmp 하위여야 합니다.')
    output_root.mkdir(parents=True, exist_ok=False)
    assemble_isloon_map(map_path, output_root / 'assembled-map.json')
    shutil.copy2(REVIEW_TEMPLATE_PATH, output_root / 'map-review.html')
    (output_root / 'README.txt').write_text('검수 서버: python3 tools/review/serve.py --root "' + str(output_root) + '" --entry map-review.html\n', encoding='utf-8')
    return output_root


def run_isloon_map_review_build_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=DEFAULT_MAP_PATH)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    print(build_isloon_map_review(arguments.map, arguments.output))


if __name__ == '__main__':
    run_isloon_map_review_build_command()
