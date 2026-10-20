"""카탈로그 파생 값과 수동 제작 지침 보존을 검증한다."""
from pathlib import Path
import tempfile
import unittest
from tools.review.maintenance.sync_billboard_catalog import build_catalog_reference, load_unique_yaml_document, DEFAULT_ASSET_DIRECTORY

class BillboardCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(current_test_class):
        current_test_class.current_catalog_record=build_catalog_reference(DEFAULT_ASSET_DIRECTORY)
        current_test_class.current_texture_lookup={x['texture_key']:x for x in current_test_class.current_catalog_record['billboards']}

    def test_default_tree_dimensions(self):
        current_tree_record=self.current_texture_lookup['field-grove-broadleaf-tree-1-v1']
        self.assertEqual(current_tree_record['placement']['displayHeight'],300)
        self.assertEqual(current_tree_record['placement']['outdoorDisplayHeight'],150)
        self.assertEqual(current_tree_record['placement']['movement'],'통행 불가')
        self.assertTrue(current_tree_record['source_file']['path'].endswith('.png'))

    def test_legacy_properties_have_generation_evidence(self):
        current_legacy_record=self.current_texture_lookup['orchard-apple-tree-v1']
        self.assertEqual(current_legacy_record['placement']['status'],'공용 속성 등록됨')
        self.assertEqual(current_legacy_record['placement']['displayHeight'],300)
        self.assertIn('생성 요청',current_legacy_record['modeling']['basis'])

    def test_ash_reference_and_footprint(self):
        current_tree_record=self.current_texture_lookup['field-grove-broadleaf-tree-1-v1']
        self.assertIn('assets/maps/field_tiles/ash-edge.yaml',[x['path'] for x in current_tree_record['map_references']])
        current_large_record=self.current_texture_lookup['field-root-trail-rooted-tree-size-large-v1']
        self.assertEqual(current_large_record['placement']['occupied_tile_count'],9)

    def test_duplicate_yaml_key_rejected(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_yaml_path=Path(current_directory_name)/'duplicate.yaml'
            current_yaml_path.write_text('name: one\nname: two\n')
            with self.assertRaisesRegex(ValueError,'중복 YAML 키'):
                load_unique_yaml_document(current_yaml_path)

    def test_synchronized_catalog_matches(self):
        current_saved_record=load_unique_yaml_document(DEFAULT_ASSET_DIRECTORY/'assets/billboards/catalog.yaml')
        self.assertEqual(current_saved_record,self.current_catalog_record)
