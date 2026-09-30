"""맵 검수가 렌더링 프로필을 사용하는지 검증한다."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.review.build_block_map_review import build_block_map_review, build_registered_map_review
from tools.review.common.map_asset_sources import load_registered_map_review
from tools.review.common.map_tile_assets import load_registered_tiles
from tools.review.common.game_render_metrics import load_game_render_metrics
from tools.review.build_map_review import load_map_render_profiles


WORKFLOW_ROOT = Path(__file__).resolve().parents[3]
GAME_MAP_DIRECTORY = WORKFLOW_ROOT / 'assets/world/isloon/game-data'


def load_exported_game_map(city_identifier):
    return load_registered_map_review(city_identifier)


class MapRenderProfileTests(unittest.TestCase):
    def test_guild_roof_uses_asset_repository_original(self):
        with TemporaryDirectory(dir=WORKFLOW_ROOT / '.tmp') as current_temporary_directory:
            current_output_directory = build_block_map_review(Path(current_temporary_directory))
            building_texture_records = json.loads((current_output_directory / 'block-building-tiles.json').read_text())
            exported_texture_records = json.loads((current_output_directory / 'block-textures.json').read_text())
            guild_texture_identifier = building_texture_records['stonewarm-guild']['roof']
            guild_texture_record = exported_texture_records[guild_texture_identifier]
            self.assertEqual(guild_texture_record['repository'], 'slime-assets')
            _, current_registered_tiles = load_registered_tiles()
            current_original_record = current_registered_tiles[guild_texture_record['source']]
            self.assertEqual(guild_texture_record['version'], current_original_record['version'])
            self.assertEqual(guild_texture_record['source'], 'assets/tiles/buildings/red-stone/red-stone-roof-v2.png')
            self.assertEqual(guild_texture_record['sha256'], current_original_record['sha256'])

    def test_all_town_reviews_use_the_game_export_as_the_only_layout_snapshot(self):
        self.assertFalse(GAME_MAP_DIRECTORY.exists())
        for current_map_identifier in ('iseulon','reedhaven','stonewarm','dry-creek'):
            current_map_record = load_registered_map_review(current_map_identifier)
            self.assertTrue(current_map_record['provenance'])
            self.assertTrue(all(record['repository']=='slime-assets' for record in current_map_record['provenance']))

    def test_game_render_metrics_identify_every_game_city_export_source(self):
        game_render_metrics = load_game_render_metrics(WORKFLOW_ROOT.parent / 'slime-frontend')
        metric_source_paths = {current_source_record['path'] for current_source_record in game_render_metrics['sources']}

        self.assertEqual(game_render_metrics['wallHeight'], 80)
        for current_city_identifier in ('iseulon', 'reedhaven', 'stonewarm', 'grainstead', 'saltford'):
            self.assertIn(f'assets/maps/city_layouts/{current_city_identifier}.yaml', metric_source_paths)

    def test_building_review_templates_use_shared_profile_values(self):
        render_profile_values = load_map_render_profiles()
        self.assertEqual(render_profile_values['wall_height'], 80)
        self.assertEqual(render_profile_values['block_height'], 80)

        map_review_source = (WORKFLOW_ROOT / 'assets/world/isloon/map-review.html').read_text(encoding='utf-8')
        self.assertNotIn('VOLUME_FLOOR_HEIGHT_PIXELS', map_review_source)
        self.assertIn('currentVolumeRenderProfile.wall_height', map_review_source)

    def test_block_map_review_uses_the_shared_eighty_pixel_block_height(self):
        block_review_builder = (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8')
        block_map_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('TOWN_BLOCK_HEIGHT=80', block_review_builder)
        self.assertIn("'block-render-profile.json'", block_review_builder)
        self.assertIn("fetchMapReviewRecord('block-render-profile.json')", block_map_script)
        self.assertIn('const TOWN_BLOCK_HEIGHT=blockRenderProfile.blockHeight', block_map_script)
        self.assertIn('마을 블록 높이 설정이 올바르지 않습니다.', block_map_script)

    def test_city_roads_match_current_game_paving_sources(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-gravel-paving', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/road/gravel-paving-v1.png', tile_catalog_source)
        self.assertIn("currentMapRecord.id==='stonewarm'?'stonewarm-marble-paving':currentMapRecord.id==='saltford'?'stonewarm-gravel-paving'", map_review_script)

    def test_stonewarm_exposed_rock_ground_uses_the_registered_tile(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-exposed-rock-ground', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/non-road/exposed-rock-ground-v1.png', tile_catalog_source)
        self.assertIn("gravel:currentMapRecord.id==='stonewarm'?'stonewarm-exposed-rock-ground':'gravel'", map_review_script)

    def test_reedhaven_roads_use_the_dirt_road_texture(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: reedhaven-dirt-road', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/road/dirt-road-v1.png', tile_catalog_source)
        self.assertIn("['reedhaven','grainstead'].includes(currentMapRecord.id)?'reedhaven-dirt-road':'paving'", map_review_script)

    def test_reedhaven_uses_wood_building_tiles(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        building_prefab_source = (WORKFLOW_ROOT / 'assets/world/isloon/building-prefabs.yaml').read_text(encoding='utf-8')
        block_review_builder = (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: wood_roof', tile_catalog_source)
        self.assertEqual(tile_catalog_source.count('id: wood_wall,'), 1)
        self.assertIn('assets/tiles/buildings/wood/wood-wall-v2.png', tile_catalog_source)
        self.assertIn('roof_underlay_wall_tile: wood_crossbar_wall', building_prefab_source)
        self.assertIn("'roof_underlay':current_prefab_record.get('roof_underlay_wall_tile'", block_review_builder)
        self.assertIn('readBuildingTileSet', map_review_script)
        self.assertIn("return 'roof_underlay'", map_review_script)

        with TemporaryDirectory(dir=WORKFLOW_ROOT / '.tmp') as current_temporary_directory:
            current_output_directory = build_block_map_review(Path(current_temporary_directory))
            reviewed_reedhaven_record = build_registered_map_review('reedhaven')
        self.assertEqual(
            reviewed_reedhaven_record['buildingTileOverrides'],
            {
                'roof': 'wood_roof',
                'wall': 'wood_wall',
                'window': 'wood_window_wall',
                'large_window': 'wood_window_wall',
                'roof_underlay': 'wood_crossbar_wall',
                'door': 'wood_door_wall',
            },
        )

    def test_reedhaven_guild_has_two_by_two_block_footprint(self):
        reedhaven_map_record = load_exported_game_map('reedhaven')
        guild_building_record = next(building for building in reedhaven_map_record['buildings'] if building['id'] == 'reedhaven-guild')

        self.assertEqual((guild_building_record['width'], guild_building_record['height']), (2, 2))
        self.assertEqual(guild_building_record['entrance'], {'column': 5, 'row': 6})
        self.assertTrue(all(block['column'] < 2 and block['row'] < 2 for block in guild_building_record['blocks']))

    def test_reedhaven_inn_has_two_by_six_block_footprint(self):
        reedhaven_map_record = load_exported_game_map('reedhaven')
        inn_building_record = next(building for building in reedhaven_map_record['buildings'] if building['id'] == 'reedhaven-inn')

        self.assertEqual((inn_building_record['width'], inn_building_record['height']), (2, 6))
        self.assertEqual(inn_building_record['entrance'], {'column': 7, 'row': 18})
        self.assertTrue(all(block['column'] < 2 and block['row'] < 6 for block in inn_building_record['blocks']))

    def test_reedhaven_buildings_have_one_wall_floor(self):
        reedhaven_map_record = load_exported_game_map('reedhaven')

        for building_record in reedhaven_map_record['buildings']:
            self.assertEqual(building_record['floors'], 1, building_record['id'])

    def test_reedhaven_entrances_touch_paved_roads(self):
        reedhaven_map_record = load_exported_game_map('reedhaven')

        for building_record in reedhaven_map_record['buildings']:
            entrance_record = building_record['entrance']
            self.assertEqual(reedhaven_map_record['terrainRows'][entrance_record['row']][entrance_record['column']], 'p', building_record['id'])
            column_minimum = building_record['origin']['column']
            column_maximum = column_minimum + building_record['width'] - 1
            row_minimum = building_record['origin']['row']
            row_maximum = row_minimum + building_record['height'] - 1
            entrance_distance = min(abs(entrance_record['column'] - current_column) + abs(entrance_record['row'] - current_row) for current_column in range(column_minimum, column_maximum + 1) for current_row in range(row_minimum, row_maximum + 1))
            self.assertEqual(entrance_distance, 1, building_record['id'])

    def test_stonewarm_uses_registered_stone_wall(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-stone-wall', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-wall-v1.png', tile_catalog_source)
        self.assertIn('id: stonewarm-small-window-wall', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-small-window-wall-v1.png', tile_catalog_source)
        self.assertIn('id: stonewarm-large-window-wall', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-large-window-wall-v1.png', tile_catalog_source)
        self.assertIn('id: stonewarm-stone-wall-crossbar', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-wall-crossbar-v1.png', tile_catalog_source)
        self.assertIn('id: stonewarm-stone-roof', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-roof-v1.png', tile_catalog_source)
        self.assertIn('id: stonewarm-stone-door', tile_catalog_source)
        self.assertIn('assets/tiles/buildings/stone/stone-door-v1.png', tile_catalog_source)
        self.assertIn("'roof':'stonewarm-stone-roof'", (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8'))
        self.assertIn("'roof_underlay':'stonewarm-stone-wall-crossbar'", (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8'))
        self.assertIn('readBuildingTileSet', map_review_script)

        with TemporaryDirectory(dir=WORKFLOW_ROOT / '.tmp') as current_temporary_directory:
            current_output_directory = build_block_map_review(Path(current_temporary_directory))
            reviewed_stonewarm_record = build_registered_map_review('stonewarm')
        self.assertEqual(reviewed_stonewarm_record['buildingTileOverrides']['roof_underlay'], 'stonewarm-stone-wall-crossbar')
        self.assertEqual(reviewed_stonewarm_record['buildingTileOverrides']['roof'], 'stonewarm-stone-roof')

    def test_stonewarm_central_plaza_is_compact(self):
        stonewarm_map_record = load_exported_game_map('stonewarm')
        central_plaza_rows = stonewarm_map_record['terrainRows'][9:13]

        self.assertEqual(central_plaza_rows, ['bbvvvvvpppppppppvpvvvvbb'] * 4)

    def test_stonewarm_guild_and_inn_use_the_approved_footprints(self):
        stonewarm_map_record = load_exported_game_map('stonewarm')
        guild_building_record = next(building for building in stonewarm_map_record['buildings'] if building['id'] == 'stonewarm-guild')
        inn_building_record = next(building for building in stonewarm_map_record['buildings'] if building['id'] == 'stonewarm-inn')

        self.assertEqual((guild_building_record['width'], guild_building_record['height']), (2, 4))
        self.assertEqual(guild_building_record['entrance'], {'column': 5, 'row': 6})
        self.assertTrue(all(block['column'] < 2 and block['row'] < 4 for block in guild_building_record['blocks']))
        self.assertEqual((inn_building_record['width'], inn_building_record['height']), (2, 3))
        self.assertEqual(inn_building_record['entrance'], {'column': 5, 'row': 19})
        self.assertTrue(all(block['column'] < 2 and block['row'] < 3 for block in inn_building_record['blocks']))

    def test_iseulon_game_snapshot_and_review_output_keep_the_new_building_floors(self):
        iseulon_map_record = load_exported_game_map('iseulon')
        guild_building_record = next(building for building in iseulon_map_record['buildings'] if building['id'] == 'iseulon-guild')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertEqual((guild_building_record['width'], guild_building_record['height'], guild_building_record['floors']), (2, 3, 2))
        self.assertTrue(all(building['floors'] == 1 for building in iseulon_map_record['buildings'] if building['id'] != 'iseulon-guild'))
        for current_building_record in iseulon_map_record['buildings']:
            if current_building_record['id'] == 'iseulon-guild':
                continue
            self.assertGreaterEqual(len(current_building_record['blocks']), current_building_record['width'] * current_building_record['height'] * 2)
        with TemporaryDirectory(dir=WORKFLOW_ROOT / '.tmp') as current_temporary_directory:
            current_output_directory = build_block_map_review(Path(current_temporary_directory))
            reviewed_map_record = build_registered_map_review('iseulon')
        reviewed_guild_record = next(building for building in reviewed_map_record['buildings'] if building['id'] == 'iseulon-guild')
        self.assertEqual((reviewed_guild_record['width'], reviewed_guild_record['height'], reviewed_guild_record['floors']), (2, 3, 2))
        self.assertTrue(all(block['height'] == 80 for block in reviewed_guild_record['blocks']))
        reviewed_bookshop_record = next(building for building in reviewed_map_record['buildings'] if building['id'] == 'iseulon-bookshop')
        self.assertEqual({block['height'] for block in reviewed_bookshop_record['blocks'] if block['material'] == 'roof'}, {80})
        self.assertTrue(any(not face['top'] for face in reviewed_bookshop_record['faces'] if face['material'] == 'roof'))
        self.assertEqual({vertex['height'] for face in reviewed_bookshop_record['faces'] if face['material'] == 'roof' for vertex in face['vertices']}, {80, 160})
        reviewed_inn_record = next(building for building in reviewed_map_record['buildings'] if building['id'] == 'iseulon-inn')
        self.assertEqual({block['layer'] for block in reviewed_inn_record['blocks'] if block['material'] == 'roof'}, {1, 2})
        self.assertEqual({block['layer'] for block in reviewed_inn_record['blocks'] if block['material'] == 'wall'}, {0, 1})
        self.assertEqual(len([face for face in reviewed_inn_record['faces'] if face['material'] == 'roof' and not face['top']]), 14)
        self.assertIn("currentRoofHeightSummary", map_review_script)
        self.assertIn('currentBuildingFloorSummary', map_review_script)

    def test_map_review_lists_applied_sources_and_normalization_warnings(self):
        map_review_template = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.html').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')
        block_review_builder = (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8')

        self.assertIn('적용 타일 원본', map_review_template)
        self.assertIn('<details class="applied-tile-sources">', map_review_template)
        self.assertIn('tile-source-warning', map_review_template)
        self.assertIn('applied-tile-sources img', map_review_template)
        self.assertIn('renderAppliedTileSourceList', map_review_script)
        self.assertIn('원본 썸네일', map_review_script)
        self.assertIn('normalization_warning', map_review_script)
        self.assertIn("'normalization_warning'", block_review_builder)

    def test_map_review_groups_controls_and_supports_keyboard_navigation(self):
        map_review_template = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.html').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('map-toolbar-group', map_review_template)
        self.assertIn('시점 도구', map_review_template)
        self.assertIn('검수 대상', map_review_template)
        self.assertIn('표시 옵션', map_review_template)
        self.assertIn('role="status"', map_review_template)
        self.assertIn('tabindex="0"', map_review_template)
        self.assertIn('MAP_KEYBOARD_PAN_DISTANCE', map_review_script)
        self.assertIn('currentMapCanvas.onkeydown', map_review_script)

    def test_ground_texture_boundaries_align_to_block_edges(self):
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('groundTextureOffset=currentFaceRecord.ground?0.5:0', map_review_script)
        self.assertIn('ground:true', map_review_script)
        self.assertIn("const BLOCK_BOUNDARY_COLOR='#dce5ef'", map_review_script)
        self.assertEqual(map_review_script.count('strokeStyle=BLOCK_BOUNDARY_COLOR'), 2)

    def test_roof_texture_frames_are_mapped_to_each_block_boundary(self):
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn("const isRoofTileSurface=currentFaceRecord.top&&currentFaceRecord.material==='roof'", map_review_script)
        self.assertIn('currentVertexPoint.column-roofTileMinimumColumn', map_review_script)
        self.assertIn('roofTileMaximumRow-currentVertexPoint.row', map_review_script)

    def test_town_page_hides_cross_town_selection_controls(self):
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn("isTownSpecificReviewPage", map_review_script)
        self.assertIn("closest('label').hidden=true", map_review_script)
