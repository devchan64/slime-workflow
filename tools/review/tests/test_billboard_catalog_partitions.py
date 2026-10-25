"""타입별 카탈로그 선택 조회·저장·오염 차단 검증."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from tools.review.maintenance.sync_billboard_catalog import load_billboard_catalog, write_billboard_catalog, serialize_billboard_catalog


class BillboardCatalogPartitionTests(TestCase):
    def setUp(self):
        current_temporary_root=TemporaryDirectory()
        self.addCleanup(current_temporary_root.cleanup)
        self.current_asset_root=Path(current_temporary_root.name)
        self.current_catalog_root=self.current_asset_root/'assets/billboards'
        (self.current_catalog_root/'catalogs').mkdir(parents=True)
        current_index_record={'schema_version':2,'review_categories':{'vegetation':'자연물','props':'소품'},'catalog_files':{'vegetation':'catalogs/vegetation.yaml','props':'catalogs/props.yaml'}}
        (self.current_catalog_root/'catalog.yaml').write_text(serialize_billboard_catalog(current_index_record))
        for current_category_name in current_index_record['review_categories']:
            current_partition_record={'schema_version':1,'category':current_category_name,'families':{current_category_name:{'review_category':current_category_name}},'billboards':[{'texture_key':current_category_name,'family':current_category_name,'modeling':{'note':'수동 기록'}}]}
            (self.current_catalog_root/f'catalogs/{current_category_name}.yaml').write_text(serialize_billboard_catalog(current_partition_record))

    def test_selected_type_does_not_parse_other_partition(self):
        (self.current_catalog_root/'catalogs/props.yaml').write_text('invalid: [')
        current_loaded_record=load_billboard_catalog(self.current_asset_root,'vegetation')
        self.assertEqual(len(current_loaded_record['billboards']),1)
        with self.assertRaises(Exception):load_billboard_catalog(self.current_asset_root)

    def test_write_preserves_other_partition(self):
        current_other_path=self.current_catalog_root/'catalogs/props.yaml'
        current_original_bytes=current_other_path.read_bytes()
        current_loaded_record=load_billboard_catalog(self.current_asset_root)
        current_loaded_record['billboards'][1]['modeling']['note']='변경'
        write_billboard_catalog(self.current_asset_root,current_loaded_record)
        self.assertEqual(current_other_path.read_bytes(),current_original_bytes)
        self.assertEqual(load_billboard_catalog(self.current_asset_root,'vegetation')['billboards'][0]['modeling']['note'],'변경')

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValueError):load_billboard_catalog(self.current_asset_root,'all')

    def test_cross_type_family_rejected(self):
        current_partition_path=self.current_catalog_root/'catalogs/props.yaml'
        current_partition_path.write_text(current_partition_path.read_text().replace('review_category: props','review_category: vegetation'))
        with self.assertRaises(ValueError):load_billboard_catalog(self.current_asset_root)
