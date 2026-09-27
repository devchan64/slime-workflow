"""맵 검수가 렌더링 프로필을 사용하는지 검증한다."""
import json
from pathlib import Path
import unittest

from tools.review.build_map_review import load_map_render_profiles


WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


class MapRenderProfileTests(unittest.TestCase):
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

    def test_stonewarm_roads_use_the_marble_paving_texture(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-marble-paving', tile_catalog_source)
        self.assertIn('world/stonewarm/terrain/marble-paving-v1.png', tile_catalog_source)
        self.assertIn("currentMapRecord.id==='stonewarm'?'stonewarm-marble-paving':currentMapRecord.id==='reedhaven'?'reedhaven-dirt-road':'paving'", map_review_script)

    def test_reedhaven_roads_use_the_dirt_road_texture(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: reedhaven-dirt-road', tile_catalog_source)
        self.assertIn('world/reedhaven/terrain/dirt-road-v1.png', tile_catalog_source)
        self.assertIn("currentMapRecord.id==='reedhaven'?'reedhaven-dirt-road':'paving'", map_review_script)

    def test_reedhaven_uses_wood_building_tiles(self):
        reedhaven_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/reedhaven.json').read_text(encoding='utf-8'))

        self.assertEqual(reedhaven_map_record['buildingTileOverrides'], {
            'roof': 'wood_roof',
            'wall': 'wood_plain_wall',
            'window': 'wood_small_window_wall',
            'large_window': 'wood_large_window_wall',
            'door': 'wood_door',
        })

    def test_reedhaven_guild_has_three_by_two_block_footprint(self):
        reedhaven_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/reedhaven.json').read_text(encoding='utf-8'))
        guild_building_record = next(building for building in reedhaven_map_record['buildings'] if building['id'] == 'reedhaven-guild')

        self.assertEqual((guild_building_record['width'], guild_building_record['height']), (3, 2))
        self.assertEqual(guild_building_record['entrance'], {'column': 5, 'row': 5})
        self.assertTrue(all(block['column'] < 3 and block['row'] < 2 for block in guild_building_record['blocks']))

    def test_reedhaven_inn_has_six_by_two_block_footprint(self):
        reedhaven_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/reedhaven.json').read_text(encoding='utf-8'))
        inn_building_record = next(building for building in reedhaven_map_record['buildings'] if building['id'] == 'reedhaven-inn')

        self.assertEqual((inn_building_record['width'], inn_building_record['height']), (6, 2))
        self.assertEqual(inn_building_record['entrance'], {'column': 7, 'row': 16})
        self.assertTrue(all(block['column'] < 6 and block['row'] < 2 for block in inn_building_record['blocks']))

    def test_reedhaven_buildings_have_one_wall_floor(self):
        reedhaven_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/reedhaven.json').read_text(encoding='utf-8'))

        for building_record in reedhaven_map_record['buildings']:
            wall_layer_values = {block['layer'] for block in building_record['blocks'] if block['material'] == 'wall'}
            roof_layer_values = {block['layer'] for block in building_record['blocks'] if block['material'] == 'roof'}
            self.assertEqual(wall_layer_values, {0}, building_record['id'])
            self.assertEqual(roof_layer_values, {1}, building_record['id'])

    def test_reedhaven_entrances_touch_paved_roads(self):
        reedhaven_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/reedhaven.json').read_text(encoding='utf-8'))

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
        stonewarm_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/stonewarm.json').read_text(encoding='utf-8'))
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-stone-wall', tile_catalog_source)
        self.assertIn('world/stonewarm/buildings/stone-wall-v1.png', tile_catalog_source)
        self.assertEqual(stonewarm_map_record['buildingTileOverrides']['wall'], 'stonewarm-stone-wall')
        self.assertIn('id: stonewarm-small-window-wall', tile_catalog_source)
        self.assertIn('world/stonewarm/buildings/stone-small-window-wall-v1.png', tile_catalog_source)
        self.assertEqual(stonewarm_map_record['buildingTileOverrides']['window'], 'stonewarm-small-window-wall')
        self.assertIn('id: stonewarm-large-window-wall', tile_catalog_source)
        self.assertIn('world/stonewarm/buildings/stone-large-window-wall-v1.png', tile_catalog_source)
        self.assertEqual(stonewarm_map_record['buildingTileOverrides']['large_window'], 'stonewarm-large-window-wall')
        self.assertIn('id: stonewarm-stone-door', tile_catalog_source)
        self.assertIn('world/stonewarm/buildings/stone-door-v1.png', tile_catalog_source)
        self.assertEqual(stonewarm_map_record['buildingTileOverrides']['door'], 'stonewarm-stone-door')
        self.assertIn('readBuildingTileSet', map_review_script)

    def test_stonewarm_central_plaza_is_compact(self):
        stonewarm_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/stonewarm.json').read_text(encoding='utf-8'))
        central_plaza_rows = stonewarm_map_record['terrainRows'][9:13]

        self.assertEqual(central_plaza_rows, ['bbvvvvvvvvpppppvvvvvvvbb'] * 4)

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

    def test_town_page_hides_cross_town_selection_controls(self):
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn("isTownSpecificReviewPage", map_review_script)
        self.assertIn("closest('label').hidden=true", map_review_script)
