"""격리된 맵 편집 저장과 실패 시 원본 보존 검사."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from tools.review.domains.map_assets import map_editor
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES

class MapLayoutEditorTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_root=tempfile.TemporaryDirectory();self.addCleanup(self.current_temp_root.cleanup)
        self.current_asset_root=Path(self.current_temp_root.name)/'slime-assets'
        self.current_source_paths=[self.current_asset_root/'assets/maps/field_tiles/sample.yaml',self.current_asset_root/'assets/maps/terrain/maps/sample.yaml']
        self.current_map_documents=[{'managementId':'tiles','data':{'rows':['KKK','KKK','KKK'],'objects':[{'id':'tower','kind':'ward-tower','position':{'column':1,'row':1}}]}},{'managementId':'terrain','data':{'terrainMovementVersion':2,'columns':3,'rows':3,'elevations':[[0]*3 for current_row_index in range(3)],'blocked':[]}}]
        for current_source_path,current_document_value in zip(self.current_source_paths,self.current_map_documents):current_source_path.parent.mkdir(parents=True,exist_ok=True);current_source_path.write_text(yaml.safe_dump(current_document_value))
        (self.current_asset_root/'assets/maps/field_tiles/codes.yaml').write_text('data: {K: angular-quarry-scree, H: dirt-road}\n')
        self.current_property_path=self.current_asset_root/'assets/maps/sprite-display-properties.yaml';self.current_property_path.write_text('data: {}\n')
        self.current_metadata_paths=[self.current_asset_root/'asset-registry.yaml',self.current_asset_root.parent/'slime-backend/map-data.lock.yaml',self.current_asset_root/'assets/billboards/catalog.yaml']
        for current_metadata_path in self.current_metadata_paths:current_metadata_path.parent.mkdir(parents=True,exist_ok=True);current_metadata_path.write_text('\n'.join('sha256: '+hashlib.sha256(current_source_path.read_bytes()).hexdigest() for current_source_path in self.current_source_paths))
        self.current_render_record={'id':'sample','startPoint':{'column':1,'row':1},'terrainCodes':{'K':'angular-quarry-scree','H':'dirt-road'},'connections':[{'direction':'east','column':2,'row':1}]}
        self.current_input_payload={'map':'sample','revision':'revision','cells':[{'column':0,'row':0,'tile':'H','height':1,'blocked':False}],'objects':[]}
        for current_patch_value in [patch.object(map_editor,'read_map_editor_snapshot',side_effect=self.read_test_snapshot),patch.object(map_editor,'load_registered_map_review',side_effect=lambda current_map_identifier:copy.deepcopy(self.current_render_record)),patch.object(map_editor,'MAP_EDITOR_STORAGE_ROOT',Path(self.current_temp_root.name)/'history'),patch.object(map_editor,'build_catalog_reference',return_value={'billboards':[]})]:current_patch_value.start();self.addCleanup(current_patch_value.stop)
    def read_test_snapshot(self,current_map_identifier):
        current_source_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in self.current_source_paths+[self.current_property_path]}
        return self.current_asset_root,self.current_source_paths,[yaml.safe_load(current_source_path.read_text()) for current_source_path in self.current_source_paths],current_source_bytes,'revision'
    def test_save_updates_both_hashes_and_preserves_tower(self):
        current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        current_saved_record=map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_record['token']})
        self.assertTrue(current_saved_record['saved'])
        self.assertEqual(yaml.safe_load(self.current_source_paths[0].read_text())['data']['rows'][0],'HKK')
        self.assertEqual(yaml.safe_load(self.current_source_paths[0].read_text())['data']['objects'][0]['id'],'tower')
        for current_source_path in self.current_source_paths:
            for current_metadata_path in self.current_metadata_paths[:2]:self.assertIn(hashlib.sha256(current_source_path.read_bytes()).hexdigest(),current_metadata_path.read_text())
    def test_stale_revision_and_changed_token_rejected(self):
        with self.assertRaisesRegex(ValueError,'변경되었습니다'):map_editor.preview_map_editor_changes({**self.current_input_payload,'revision':'stale'})
        current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        with self.assertRaisesRegex(ValueError,'먼저 검증'):map_editor.save_map_editor_changes({**self.current_input_payload,'cells':[],'token':current_preview_record['token']})
    def test_exit_block_and_isolated_height_rejected(self):
        for current_cell_record in [{'column':2,'row':1,'tile':'K','height':0,'blocked':True},{'column':0,'row':0,'tile':'K','height':20,'blocked':False}]:
            with self.assertRaises(ValueError):map_editor.preview_map_editor_changes({**self.current_input_payload,'cells':[current_cell_record]})
    def test_invalid_coordinate_and_texture_rejected(self):
        with self.assertRaisesRegex(ValueError,'좌표'):map_editor.preview_map_editor_changes({**self.current_input_payload,'cells':[{**self.current_input_payload['cells'][0],'column':-1}]})
        with self.assertRaisesRegex(ValueError,'등록된'):map_editor.preview_map_editor_changes({**self.current_input_payload,'objects':[{'id':'bad','kind':'decoration','textureKey':'missing','tileAnchor':'center','position':{'column':0,'row':0}}]})
    def test_write_failure_restores_originals(self):
        current_original_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in self.current_source_paths+self.current_metadata_paths}
        current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        with patch.object(map_editor,'build_catalog_reference',side_effect=ValueError('검증 실패')):
            with self.assertRaisesRegex(ValueError,'검증 실패'):map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_record['token']})
        for current_source_path,current_original_value in current_original_bytes.items():self.assertEqual(current_source_path.read_bytes(),current_original_value)
    def test_gateway_commands_have_routes(self):
        for current_command_name in map_editor.MAP_EDITOR_ALLOWED_COMMANDS:
            self.assertIn(current_command_name,MANAGEMENT_SERVICE_COMMANDS['map-assets'])
            self.assertEqual(MANAGEMENT_COMMAND_ROUTES[current_command_name],('POST','/editor-'+current_command_name))
