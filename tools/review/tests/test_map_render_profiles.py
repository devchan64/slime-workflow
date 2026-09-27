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

        map_review_source = (WORKFLOW_ROOT / 'assets/world/isloon/map-review.html').read_text(encoding='utf-8')
        self.assertNotIn('VOLUME_FLOOR_HEIGHT_PIXELS', map_review_source)
        self.assertIn('currentVolumeRenderProfile.wall_height', map_review_source)

    def test_stonewarm_roads_use_the_marble_paving_texture(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-marble-paving', tile_catalog_source)
        self.assertIn('world/stonewarm/terrain/marble-paving-v1.png', tile_catalog_source)
        self.assertIn("currentMapRecord.id==='stonewarm'?'stonewarm-marble-paving':'paving'", map_review_script)

    def test_stonewarm_uses_registered_stone_wall(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml').read_text(encoding='utf-8')
        stonewarm_map_record = json.loads((WORKFLOW_ROOT / 'assets/world/isloon/blocks/stonewarm.json').read_text(encoding='utf-8'))
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-stone-wall', tile_catalog_source)
        self.assertIn('world/stonewarm/buildings/stone-wall-v1.png', tile_catalog_source)
        self.assertEqual(stonewarm_map_record['buildingTileOverrides']['wall'], 'stonewarm-stone-wall')
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
