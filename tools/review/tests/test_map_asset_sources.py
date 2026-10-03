"""맵·타일 원본 직접 제공과 잘못된 경로 거절을 검증한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import yaml
from tools.review.common.map_asset_sources import load_review_map_identifiers, normalize_field_surface_data
from tools.review.build_block_map_review import build_block_map_review
from tools.review.common.map_asset_http import read_map_asset_response

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class MapAssetSourceTests(unittest.TestCase):
    def test_field_height_and_stair_api_contract(self):
        current_map_bytes,_ = read_map_asset_response('/management/map-assets/maps/meadow')
        current_map_record = json.loads(current_map_bytes)
        self.assertFalse(current_map_record['safeTown'])
        self.assertEqual(set(current_height for current_row in current_map_record['elevations'] for current_height in current_row),{0,1,2})
        self.assertEqual(len(current_map_record['elevationTiles']),6)
        for current_stair_record in current_map_record['elevationTiles']:
            self.assertEqual(set(current_stair_record['cell']),{'column','row'})

    def test_guard_center_images_match_registered_regions(self):
        current_city_identifiers,current_map_identifiers = load_review_map_identifiers()
        current_guard_count = 0
        for current_map_identifier in current_map_identifiers:
            if current_map_identifier in current_city_identifiers: continue
            current_response_bytes,_ = read_map_asset_response('/management/map-assets/maps/'+current_map_identifier)
            current_map_record = json.loads(current_response_bytes)
            for current_guard_record in current_map_record['guardCenters']:
                current_guard_count += 1
                current_image_bytes,current_content_type = read_map_asset_response(current_guard_record['image'])
                self.assertEqual(current_content_type,'image/png')
                self.assertEqual(hashlib.sha256(current_image_bytes).hexdigest(),current_guard_record['provenance']['sha256'])
                self.assertIn(current_guard_record['cityId'],current_city_identifiers)
                self.assertTrue(0<=current_guard_record['position']['column']<current_map_record['columns'])
                self.assertTrue(0<=current_guard_record['position']['row']<current_map_record['rows'])
        self.assertEqual(current_guard_count,9)

    def test_invalid_height_grid_and_stair_are_rejected(self):
        for current_map_record in (
            dict(columns=2,rows=1,elevations=['0x']),
            dict(columns=2,rows=1,elevations=['0']),
            dict(columns=2,rows=1,elevations=['00'],elevationTiles=[dict(kind='stairs',asset='stone-step-tile',cell=[1,0],lower=[0,0])]),
        ):
            with self.assertRaises(ValueError):
                normalize_field_surface_data(current_map_record)

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

    def test_texture_metadata_is_loaded_on_every_request(self):
        with patch('tools.review.build_block_map_review.load_current_texture_records', side_effect=[{'tile': {'sha256': 'before'}}, {'tile': {'sha256': 'after'}}]):
            first_response_bytes, _ = read_map_asset_response('/management/map-assets/textures')
            second_response_bytes, _ = read_map_asset_response('/management/map-assets/textures')
        self.assertEqual(json.loads(first_response_bytes)['tile']['sha256'], 'before')
        self.assertEqual(json.loads(second_response_bytes)['tile']['sha256'], 'after')

    def test_invalid_source_paths_are_rejected(self):
        for current_request_path in ('/management/map-assets/maps/unknown','/management/map-assets/maps/../../config','/management/map-assets/files/assets/tiles/../../AGENTS.md','/management/map-assets/files/assets/maps/field_tiles/dry-creek.yaml'):
            with self.assertRaises(ValueError):
                read_map_asset_response(current_request_path)


    def test_all_runtime_maps_and_new_city_materials_share_original_hashes(self):
        current_city_identifiers,current_map_identifiers = load_review_map_identifiers()
        self.assertEqual(len(current_city_identifiers),5)
        self.assertEqual(len(current_map_identifiers),31)
        current_asset_root = WORKFLOW_REPOSITORY_ROOT.parent/'slime-assets'
        current_map_lock = yaml.safe_load((WORKFLOW_REPOSITORY_ROOT.parent/'slime-backend/map-data.lock.yaml').read_text())
        current_locked_hashes = {current_file_record['path']:current_file_record['sha256'] for current_file_record in current_map_lock['files']}
        for current_map_identifier in ('grainstead','saltford','windrow-road','granary-flats','mill-ridge','brine-bank','salt-causeway','salt-flat'):
            current_map_bytes,_ = read_map_asset_response('/management/map-assets/maps/'+current_map_identifier)
            current_map_record = json.loads(current_map_bytes)
            self.assertEqual(current_map_record['id'],current_map_identifier)
            for current_source_record in current_map_record['provenance']:
                current_source_path = current_source_record['source']
                self.assertEqual(current_source_record['sha256'],current_locked_hashes[current_source_path])
                self.assertEqual(current_source_record['sha256'],hashlib.sha256((current_asset_root/current_source_path).read_bytes()).hexdigest())
            if current_map_identifier in current_city_identifiers:
                self.assertEqual(len(current_map_record['buildings']),5)
                self.assertEqual(current_map_record['buildingTileOverrides']['roof'],'wood_roof')
