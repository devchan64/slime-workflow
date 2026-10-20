"""맵·타일 원본 직접 제공과 잘못된 경로 거절을 검증한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import yaml
from tools.review.common.map_asset_sources import load_review_map_identifiers, normalize_field_surface_data, load_registered_map_review
from tools.review.build_block_map_review import build_block_map_review
from tools.review.build_block_map_review import load_current_texture_records
from tools.review.common.map_tile_assets import load_registered_tiles
from tools.review.common.map_asset_http import read_map_asset_response

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class MapAssetSourceTests(unittest.TestCase):
    def test_field_height_movement_contract(self):
        current_map_bytes,_ = read_map_asset_response('/management/map-assets/maps/meadow')
        current_map_record = json.loads(current_map_bytes)
        self.assertFalse(current_map_record['safeTown'])
        self.assertEqual(set(current_height for current_row in current_map_record['elevations'] for current_height in current_row),{0,1,2})
        self.assertEqual(current_map_record['terrainMovementVersion'],2)
        self.assertEqual(current_map_record['elevationTiles'],[])
        self.assertEqual(current_map_record['ramps'],[])

    def test_edge_billboard_obstacles_stay_inside_map(self):
        for current_map_identifier in ('dawn-overlook', 'dry-creek', 'old-orchard'):
            with self.subTest(map=current_map_identifier):
                current_map_record = load_registered_map_review(current_map_identifier)
                self.assertTrue(all(0 <= current_cell_record['column'] < current_map_record['columns'] and
                                    0 <= current_cell_record['row'] < current_map_record['rows']
                                    for current_cell_record in current_map_record['blocked']))

    def test_orchard_billboards_preserve_ground_codes_and_layer_contract(self):
        current_response_bytes, _ = read_map_asset_response('/management/map-assets/maps/old-orchard')
        current_map_record = json.loads(current_response_bytes)
        current_source_path = WORKFLOW_REPOSITORY_ROOT.parent/'slime-assets/assets/maps/field_tiles/old-orchard.yaml'
        current_source_record = yaml.safe_load(current_source_path.read_text())['data']
        self.assertEqual(current_map_record['terrainRows'], current_source_record['rows'])
        self.assertEqual(current_map_record['groundOverrides'], current_source_record['groundOverrides'])
        current_objects_by_identifier = {current_object_record['id']: current_object_record for current_object_record in current_map_record['objects']}
        self.assertEqual(set(current_objects_by_identifier), {current_object_record['id'] for current_object_record in current_source_record['objects']})
        for current_source_object in current_source_record['objects']:
            current_response_object = current_objects_by_identifier[current_source_object['id']]
            for current_property_name, current_property_value in current_source_object.items():
                self.assertEqual(current_response_object[current_property_name], current_property_value)
        self.assertEqual(current_map_record['terrainMovementVersion'], 2)

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
                self.assertTrue(0<current_guard_record['renderPosition']['column']<current_map_record['columns']-1)
                self.assertTrue(0<current_guard_record['renderPosition']['row']<current_map_record['rows']-1)
                self.assertTrue(0<=current_guard_record['position']['column']<current_map_record['columns'])
                self.assertTrue(0<=current_guard_record['position']['row']<current_map_record['rows'])
        self.assertEqual(current_guard_count,9)

    def test_invalid_height_grid_and_stair_are_rejected(self):
        for current_map_record in (
            dict(terrainMovementVersion=1,columns=2,rows=1,elevations=['00']),
            dict(terrainMovementVersion=2,columns=2,rows=1,elevations=['00'],ramps=[{}]),
            dict(columns=2,rows=1,elevations=['0x']),
            dict(columns=2,rows=1,elevations=['0']),
            dict(terrainMovementVersion=2,columns=2,rows=1,elevations=['00'],elevationTiles=[dict(kind='stairs',asset='stone-step-tile',cell=[1,0],lower=[0,0])]),
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
        current_source_path = WORKFLOW_REPOSITORY_ROOT.parent/'slime-assets/assets/maps/field_tiles/dry-creek.yaml'
        current_source_rows = yaml.safe_load(current_source_path.read_text())['data']['rows']
        self.assertEqual(current_map_record['terrainRows'], current_source_rows)
        self.assertTrue(all(record['source'].startswith('assets/maps/') for record in current_map_record['provenance']))

    def test_texture_metadata_is_loaded_on_every_request(self):
        with patch('tools.review.build_block_map_review.load_current_texture_records', side_effect=[{'tile': {'sha256': 'before'}}, {'tile': {'sha256': 'after'}}]):
            first_response_bytes, _ = read_map_asset_response('/management/map-assets/textures')
            second_response_bytes, _ = read_map_asset_response('/management/map-assets/textures')
        self.assertEqual(json.loads(first_response_bytes)['tile']['sha256'], 'before')
        self.assertEqual(json.loads(second_response_bytes)['tile']['sha256'], 'after')

    def test_registered_road_tiles_are_all_listed_by_management_catalog(self):
        current_texture_records = load_current_texture_records()
        current_catalog_road_paths = {
            current_texture_record['source']
            for current_texture_record in current_texture_records.values()
            if current_texture_record['source'].startswith('assets/tiles/terrain/road/')
        }
        _, current_registered_records = load_registered_tiles()
        current_registered_road_paths = {
            current_asset_path
            for current_asset_path in current_registered_records
            if current_asset_path.startswith('assets/tiles/terrain/road/')
            and Path(current_asset_path).suffix.lower() in {'.png','.webp','.jpg','.jpeg'}
        }
        self.assertSetEqual(current_catalog_road_paths, current_registered_road_paths)

    def test_retired_scenery_is_excluded_before_path_resolution(self):
        current_asset_root,current_registered_records=load_registered_tiles()
        current_registered_records=dict(current_registered_records)
        current_registered_records['assets/retired/billboards/test-retired-v1.png']={
            'managementId':'image.scenery.test-retired-v1',
            'source':{'lifecycle_status':'retired'},
        }
        with patch('tools.review.build_block_map_review.load_registered_tiles',return_value=(current_asset_root,current_registered_records)):
            current_texture_records=load_current_texture_records(validate_complete_inventory=False)
        self.assertNotIn('test-retired-v1',current_texture_records)
        self.assertFalse(any(r['source'].startswith('assets/retired/') for r in current_texture_records.values()))

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
                current_city_source = yaml.safe_load((current_asset_root/'assets/maps/city_layouts'/f'{current_map_identifier}.yaml').read_text())['data']
                current_source_buildings = {current_building_record['id']: current_building_record for current_building_record in current_city_source['buildings']}
                self.assertEqual({current_building_record['id'] for current_building_record in current_map_record['buildings']}, set(current_source_buildings))
                for current_building_record in current_map_record['buildings']:
                    current_source_building = current_source_buildings[current_building_record['id']]
                    for current_property_name in ('origin', 'entrance', 'width', 'height', 'floors'):
                        self.assertEqual(current_building_record[current_property_name], current_source_building[current_property_name])
                    self.assertEqual(current_building_record['sprite']['textureKey'], current_source_building['sprite']['textureKey'])


class WorldMapAssetContractTests(unittest.TestCase):
    def test_world_catalog_and_thumbnail_http_use_registered_originals(self):
        current_response_bytes,current_content_type = read_map_asset_response('/management/map-assets/world')
        current_world_catalog = json.loads(current_response_bytes)
        self.assertIn('application/json',current_content_type)
        self.assertEqual(current_world_catalog['version'],3)
        current_world_nodes = {current_world_node['id']:current_world_node for current_world_node in current_world_catalog['maps']}
        self.assertEqual(set(current_world_nodes),set(load_review_map_identifiers()[1]))
        for current_world_node in current_world_nodes.values():
            current_thumbnail_record = current_world_node['thumbnail']
            current_image_bytes,current_image_type = read_map_asset_response(current_thumbnail_record['url'].split('?')[0])
            self.assertEqual(current_image_type,'image/png')
            self.assertEqual(hashlib.sha256(current_image_bytes).hexdigest(),current_thumbnail_record['sha256'])
            for current_world_link in current_world_node['connections']:
                self.assertTrue(any(current_reverse_link['id']==current_world_link['targetWaypointId'] and current_reverse_link['targetWaypointId']==current_world_link['id'] and current_reverse_link['target']==current_world_node['id'] for current_reverse_link in current_world_nodes[current_world_link['target']]['connections']))

    def test_thumbnail_http_rejects_path_escape(self):
        with self.assertRaises(ValueError):
            read_map_asset_response('/management/map-assets/thumbnails/../../../asset-registry.yaml')
