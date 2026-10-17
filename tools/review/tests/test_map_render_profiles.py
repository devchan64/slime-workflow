"""맵 검수가 렌더링 프로필을 사용하는지 검증한다."""
import json
import hashlib
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.review.build_block_map_review import build_block_map_review, build_registered_map_review
from tools.review.common.map_asset_sources import load_registered_map_review, read_registered_map_data
from tools.review.common.map_tile_assets import load_registered_tiles
from tools.review.common.game_render_metrics import load_game_render_metrics
from tools.review.build_map_review import load_map_render_profiles


WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


def load_exported_game_map(city_identifier):
    return load_registered_map_review(city_identifier)


class MapRenderProfileTests(unittest.TestCase):
    def test_town_billboards_resolve_registered_originals(self):
        from tools.review.build_block_map_review import load_current_texture_records
        current_texture_catalog = load_current_texture_records()
        for current_city_identifier in ('iseulon', 'reedhaven', 'stonewarm', 'grainstead', 'saltford'):
            current_map_record = load_registered_map_review(current_city_identifier)
            self.assertTrue(current_map_record['objects'])
            for current_object_record in current_map_record['objects']:
                current_texture_record = current_texture_catalog[current_object_record['textureKey']]
                self.assertTrue(current_texture_record['source'].startswith('assets/billboards/'))
                self.assertEqual(current_texture_record['repository'], 'slime-assets')

    def assert_ground_texture_selection(self, current_map_identifier, current_material_name, current_expected_texture):
        current_script_source = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text()
        current_mapping_expression = current_script_source.split('const groundTextureNames=', 1)[1].split(';', 1)[0]
        current_node_source = (
            "const assert=require('node:assert/strict'); const isFieldMapReview=false; const currentMapRecord="
            + json.dumps({'id': current_map_identifier}) + '; assert.equal(('
            + current_mapping_expression + ')[ ' + json.dumps(current_material_name) + '], '
            + json.dumps(current_expected_texture) + ');'
        )
        current_test_result = subprocess.run(['node', '-e', current_node_source], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

    def test_texture_alias_reuses_identical_source_and_rejects_conflict(self):
        current_adapter_source = (WORKFLOW_ROOT / 'tools/review/ui/map/field-map-view.js').read_text()
        current_alias_source = current_adapter_source.split(' if(currentTextureRecords){', 1)[1].split('  createTerrainAtlas(currentFieldScene);', 1)[0]
        current_script_source = r"""
const assert = require('node:assert/strict');
const currentOriginalImage = {}, currentOtherImage = {};
const currentTextureImages = {catalog: currentOriginalImage};
const currentTextureRecords = {catalog: {source: 'tile.png'}};
const currentTextureStore = new Map([['existing', currentOriginalImage]]);
const currentFieldScene = {textures: {
 exists: currentTextureName => currentTextureStore.has(currentTextureName),
 get: currentTextureName => ({getSourceImage: () => currentTextureStore.get(currentTextureName)}),
 addImage: (currentTextureName, currentImageValue) => {
  assert.equal(currentTextureStore.has(currentTextureName), false);
  currentTextureStore.set(currentTextureName, currentImageValue);
 }
}};
const collectTerrainTextureSources = () => ({existing: 'tile.png', alias: 'tile.png'});
const registerTextureAliases = () => {ALIAS_SOURCE};
registerTextureAliases();
assert.equal(currentTextureStore.get('alias'), currentOriginalImage);
registerTextureAliases();
currentTextureStore.set('existing', currentOtherImage);
assert.throws(registerTextureAliases, /다른 검수 원본과 충돌/);
""".replace('ALIAS_SOURCE', current_alias_source)
        current_test_result = subprocess.run(['node', '-e', current_script_source], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

    def test_guild_sprite_uses_asset_repository_original(self):
        with TemporaryDirectory(dir=WORKFLOW_ROOT / '.tmp') as current_temporary_directory:
            current_output_directory = build_block_map_review(Path(current_temporary_directory))
            self.assertFalse((current_output_directory / 'block-building-tiles.json').exists())
            exported_texture_records = json.loads((current_output_directory / 'block-textures.json').read_text())
            guild_texture_identifier = 'town-stonewarm-guild-v1'
            guild_texture_record = exported_texture_records[guild_texture_identifier]
            self.assertEqual(guild_texture_record['repository'], 'slime-assets')
            _, current_registered_tiles = load_registered_tiles()
            current_original_record = current_registered_tiles[guild_texture_record['source']]
            self.assertEqual(guild_texture_record['version'], current_original_record['version'])
            self.assertEqual(guild_texture_record['source'], 'assets/sprites/structures/town-stonewarm-guild-v1.png')
            self.assertEqual(guild_texture_record['sha256'], current_original_record['sha256'])
            # 게시된 결계 사본과 공용 렌더러가 실제 manifest의 해시와 일치해야 한다.
            current_safe_records=json.loads((current_output_directory/'field-safe-visuals.json').read_text())
            self.assertEqual(set(current_safe_records),{'tower','aura'})
            for current_safe_record in current_safe_records.values():
                current_image_path=current_output_directory/current_safe_record['image'].split('?')[0]
                self.assertEqual(hashlib.sha256(current_image_path.read_bytes()).hexdigest(),current_safe_record['provenance']['sha256'])
            import yaml
            current_vendor_manifest=yaml.safe_load((WORKFLOW_ROOT/'tools/review/ui/map/vendor/field-renderer/manifest.yaml').read_text())
            current_library_directory=current_output_directory/'vendor/field-renderer'/current_vendor_manifest['version']
            current_library_manifest=yaml.safe_load((current_library_directory/'manifest.yaml').read_text())
            for current_file_name,current_file_hash in current_library_manifest['files'].items():
                self.assertEqual(hashlib.sha256((current_library_directory/current_file_name).read_bytes()).hexdigest(),current_file_hash)
            self.assertTrue((current_output_directory/'field-map-view.js').is_file())

    def test_all_town_reviews_use_the_game_export_as_the_only_layout_snapshot(self):
        self.assertFalse((WORKFLOW_ROOT / 'assets' / 'world').exists())
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

        with self.assertRaisesRegex(ValueError, '로컬 맵 사본'):
            from tools.review.build_map_review import build_map_review
            build_map_review(map_path='old-map.yaml')

    def test_block_map_review_uses_the_shared_eighty_pixel_block_height(self):
        block_review_builder = (WORKFLOW_ROOT / 'tools/review/build_block_map_review.py').read_text(encoding='utf-8')
        block_map_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn("'BUILDING_RENDER_BLOCK_HEIGHT'", block_review_builder)
        self.assertIn("'block-render-profile.json'", block_review_builder)
        self.assertIn("fetchMapReviewRecord('block-render-profile.json')", block_map_script)
        self.assertIn('const TOWN_BLOCK_HEIGHT=blockRenderProfile.blockHeight', block_map_script)

    def test_map_review_uses_game_character_effect_rules(self):
        block_map_script=(WORKFLOW_ROOT/'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')
        field_map_view=(WORKFLOW_ROOT/'tools/review/ui/map/field-map-view.js').read_text(encoding='utf-8')
        map_review_application=(WORKFLOW_ROOT/'tools/review/ui/gradio/map_review_app.py').read_text(encoding='utf-8')

        self.assertNotIn('character-outline',block_map_script)
        self.assertNotIn('캐릭터 외곽 강조',map_review_application)
        self.assertIn('drawCharacterContactShadow',field_map_view)
        self.assertIn('game-render-profile.mjs',field_map_view)
        self.assertIn('attachCharacterOutlineLayers(currentCharacterSprite)',field_map_view)
        self.assertIn('visible=character_review_enabled',map_review_application)
        self.assertIn('캐릭터 시인성 검수',map_review_application)
        self.assertIn('마을 블록 높이 설정이 올바르지 않습니다.', block_map_script)

    def test_city_roads_match_current_game_paving_sources(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'tools/review/ui/map/config/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-gravel-paving', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/road/limestone-road-v3.png', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/road/granite-slab-road-v1.png', tile_catalog_source)
        self.assert_ground_texture_selection('stonewarm', 'paving', 'stonewarm-granite-paving')
        self.assert_ground_texture_selection('saltford', 'paving', 'stonewarm-gravel-paving')

    def test_stonewarm_exposed_rock_ground_uses_the_registered_tile(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'tools/review/ui/map/config/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: stonewarm-exposed-rock-ground', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/non-road/exposed-rock-ground-v2.png', tile_catalog_source)
        self.assert_ground_texture_selection('stonewarm', 'gravel', 'stonewarm-exposed-rock-ground')
        self.assert_ground_texture_selection('iseulon', 'gravel', 'gravel')

    def test_reedhaven_and_grainstead_use_registered_ground_textures(self):
        tile_catalog_source = (WORKFLOW_ROOT / 'tools/review/ui/map/config/tile-catalog.yaml').read_text(encoding='utf-8')
        map_review_script = (WORKFLOW_ROOT / 'tools/review/ui/map/block-map-review.js').read_text(encoding='utf-8')

        self.assertIn('id: reedhaven-dirt-road', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/road/limestone-road-v3.png', tile_catalog_source)
        self.assertIn('assets/tiles/terrain/non-road/dry-soil-grass-v1.png', tile_catalog_source)
        self.assert_ground_texture_selection('reedhaven', 'paving', 'reedhaven-dry-embankment')
        self.assert_ground_texture_selection('grainstead', 'paving', 'reedhaven-dirt-road')

    def test_reedhaven_uses_registered_building_sprites(self):
        current_review_record = build_registered_map_review('reedhaven')
        self.assertNotIn('buildingTileOverrides', current_review_record)
        self.assertEqual(len(current_review_record['buildings']), 5)
        for current_building_record in current_review_record['buildings']:
            self.assertEqual(current_building_record['sprite']['textureKey'], 'town-' + current_building_record['id'] + '-v1')
            self.assertNotIn('blocks', current_building_record)

    def test_reedhaven_guild_has_sprite_collision_footprint(self):
        current_map_record = load_exported_game_map('reedhaven')
        current_building_record = next(item for item in current_map_record['buildings'] if item['id'] == 'reedhaven-guild')
        self.assertEqual((current_building_record['width'], current_building_record['height']), (3, 3))
        self.assertEqual(current_building_record['entrance'], {'column': 5, 'row': 7})

    def test_reedhaven_inn_has_sprite_collision_footprint(self):
        current_map_record = load_exported_game_map('reedhaven')
        current_building_record = next(item for item in current_map_record['buildings'] if item['id'] == 'reedhaven-inn')
        self.assertEqual((current_building_record['width'], current_building_record['height']), (4, 3))
        self.assertEqual(current_building_record['entrance'], {'column': 7, 'row': 17})

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

    def test_stonewarm_uses_registered_building_sprites(self):
        current_review_record = build_registered_map_review('stonewarm')
        self.assertNotIn('buildingTileOverrides', current_review_record)
        for current_building_record in current_review_record['buildings']:
            self.assertTrue(current_building_record['sprite']['textureKey'].startswith('town-stonewarm-'))
            self.assertNotIn('faces', current_building_record)

    def test_stonewarm_review_preserves_registered_terrain_layout(self):
        current_source_provenance = []
        current_source_record = read_registered_map_data('city_layouts/stonewarm.yaml', current_source_provenance)
        current_review_record = build_registered_map_review('stonewarm')
        self.assertEqual(current_review_record['terrainRows'], current_source_record['terrainRows'])
        self.assertEqual(current_review_record['columns'], current_source_record['columns'])
        self.assertEqual(current_review_record['rows'], current_source_record['rows'])
        self.assertTrue(current_source_provenance)
        self.assertIn(current_source_provenance[0], current_review_record['provenance'])

    def test_stonewarm_guild_and_inn_use_the_approved_footprints(self):
        current_map_record = load_exported_game_map('stonewarm')
        current_building_records = {item['id']: item for item in current_map_record['buildings']}
        self.assertEqual(current_building_records['stonewarm-guild']['entrance'], {'column': 7, 'row': 5})
        self.assertEqual(current_building_records['stonewarm-inn']['entrance'], {'column': 7, 'row': 17})

    def test_city_game_and_review_share_flat_sprite_buildings(self):
        for current_city_identifier in ('iseulon', 'reedhaven', 'stonewarm', 'grainstead', 'saltford'):
            current_source_record = load_exported_game_map(current_city_identifier)
            current_review_record = build_registered_map_review(current_city_identifier)
            self.assertEqual(current_source_record['buildings'], current_review_record['buildings'])
            self.assertEqual(current_review_record.get('ramps', []) , [])
            for current_building_record in current_review_record['buildings']:
                self.assertNotIn('blocks', current_building_record)
                self.assertNotIn('faces', current_building_record)
                self.assertGreater(current_building_record['sprite']['contentWidth'], 0)
                self.assertLessEqual(current_building_record['sprite']['contentWidth'], 1)

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
