"""맵·타일 원본 직접 제공과 잘못된 경로 거절을 검증한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.review.build_block_map_review import build_block_map_review
from tools.review.common.map_asset_http import read_map_asset_response

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class MapAssetSourceTests(unittest.TestCase):
    def test_review_has_no_map_or_tile_copies(self):
        with TemporaryDirectory(dir=WORKFLOW_REPOSITORY_ROOT/'.tmp') as temporary_output_path:
            current_output_path = build_block_map_review(Path(temporary_output_path))
            self.assertFalse((current_output_path/'block-map-dry-creek.json').exists())
            self.assertFalse((current_output_path/'textures/cactus.png').exists())
            current_texture_record = json.loads((current_output_path/'block-textures.json').read_text())['cactus']
            current_image_bytes,current_content_type = read_map_asset_response(current_texture_record['path'].split('?')[0])
            self.assertEqual(current_content_type,'image/png')
            self.assertEqual(hashlib.sha256(current_image_bytes).hexdigest(),current_texture_record['sha256'])
        current_map_bytes,_ = read_map_asset_response('/management/map-assets/maps/dry-creek')
        current_map_record = json.loads(current_map_bytes)
        self.assertEqual(sum(row.count('k') for row in current_map_record['terrainRows']),10)
        self.assertTrue(all(record['source'].startswith('assets/maps/') for record in current_map_record['provenance']))

    def test_invalid_source_paths_are_rejected(self):
        for current_request_path in ('/management/map-assets/maps/unknown','/management/map-assets/maps/../../config','/management/map-assets/files/assets/tiles/../../AGENTS.md','/management/map-assets/files/assets/maps/field_tiles/dry-creek.yaml'):
            with self.assertRaises(ValueError):
                read_map_asset_response(current_request_path)
