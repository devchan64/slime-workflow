"""격리된 원본에서 일괄 편집·변경 잠금·원복을 확인한다."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from tools.review.domains.map_assets import editor
from tools.review.ui.gradio.asset_editor_app import build_asset_editor_payload

class MapAssetEditorTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_asset_root=Path(self.current_temp_directory.name)/'slime-assets'
        self.current_property_path=self.current_asset_root/'assets/maps/sprite-display-properties.yaml'
        self.current_property_path.parent.mkdir(parents=True)
        self.current_property_values={'anchorX':.5,'anchorY':1,'groundFootprintColumns':1,'groundFootprintRows':1,'displayHeight':70,'billboardPlacementAnchor':'bottom','billboardBlocksMovement':False}
        self.current_property_path.write_text(yaml.safe_dump({'data':{'sample':self.current_property_values}}))
        self.current_original_hash=hashlib.sha256(self.current_property_path.read_bytes()).hexdigest()
        (self.current_asset_root/'asset-registry.yaml').write_text('sha256: '+self.current_original_hash)
        self.current_catalog_path=self.current_asset_root/'assets/billboards/catalog.yaml'
        self.current_catalog_path.parent.mkdir(parents=True);self.current_catalog_path.write_text('original: true\n')
        self.current_backend_path=self.current_asset_root.parent/'slime-backend/map-data.lock.yaml'
        self.current_backend_path.parent.mkdir();self.current_backend_path.write_text('sha256: '+self.current_original_hash)
        self.current_catalog_record={'billboards':[{'texture_key':'sample'}]}
        self.current_catalog_patch=patch.object(editor,'build_catalog_reference',return_value=self.current_catalog_record)
        self.current_catalog_patch.start();self.addCleanup(self.current_catalog_patch.stop)
        self.current_storage_patch=patch.object(editor,'EDITOR_STORAGE_DIRECTORY',self.current_asset_root.parent/'receipts')
        self.current_storage_patch.start();self.addCleanup(self.current_storage_patch.stop)
        self.current_request_payload={'revision':editor.read_editor_snapshot(self.current_asset_root)[3],'changes':[{'texture':'sample','values':{'displayHeight':100}}]}

    def test_map_conflict_warns_without_blocking_save(self):
        current_map_path=self.current_property_path.parent/'sample-map.yaml'
        current_map_path.write_text(yaml.safe_dump({'data':{'objects':[{'id':'sample-object','kind':'decoration','textureKey':'sample','position':{'column':1,'row':0}}],'elevations':[[0,1],[0,0]]}}))
        self.current_request_payload['changes'][0]['values']['groundFootprintRows']=2
        current_preview_result=editor.preview_editor_changes(self.current_request_payload,self.current_asset_root)
        self.assertIn('고도 불일치',current_preview_result['map_warnings'][0]['message'])
        current_saved_result=editor.save_editor_changes({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)
        self.assertTrue(current_saved_result['saved'])
        self.assertEqual(current_saved_result['map_warnings'],current_preview_result['map_warnings'])

    def test_preview_save_hash_catalog_and_repeat(self):
        current_preview_result=editor.preview_editor_changes(self.current_request_payload,self.current_asset_root)
        self.assertEqual(hashlib.sha256(self.current_property_path.read_bytes()).hexdigest(),self.current_original_hash)
        self.assertFalse(current_preview_result['changes'][0]['after']['billboardBlocksMovement'])
        current_save_payload={**self.current_request_payload,'token':current_preview_result['token']}
        current_saved_result=editor.save_editor_changes(current_save_payload,self.current_asset_root)
        self.assertEqual(current_saved_result['count'],1)
        self.assertEqual(yaml.safe_load(self.current_catalog_path.read_text()),self.current_catalog_record)
        self.assertIn(current_saved_result['sha256'],self.current_backend_path.read_text())
        self.assertEqual(editor.save_editor_changes(current_save_payload,self.current_asset_root),current_saved_result)

    def test_stale_and_unreviewed_and_changed_requests_rejected(self):
        with self.assertRaises(ValueError):editor.save_editor_changes({**self.current_request_payload,'token':'wrong'},self.current_asset_root)
        current_preview_result=editor.preview_editor_changes(self.current_request_payload,self.current_asset_root)
        self.current_property_path.write_text(self.current_property_path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'원본이 변경'):editor.save_editor_changes({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)

    def test_invalid_size_and_top_anchor_rejected(self):
        for current_invalid_values in ({'groundFootprintColumns':1.5},{'billboardBlocksMovement':'true'},{'displayHeight':float('nan')},{'unexpected':3}):
            with self.assertRaises(ValueError):editor.prepare_editor_changes({**self.current_request_payload,'changes':[{'texture':'sample','values':current_invalid_values}]},self.current_asset_root)

    def test_catalog_failure_rolls_back_all_sources(self):
        current_preview_result=editor.preview_editor_changes(self.current_request_payload,self.current_asset_root)
        current_source_paths=editor.read_editor_snapshot(self.current_asset_root)[1]
        current_original_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in current_source_paths}
        with patch.object(editor,'build_catalog_reference',side_effect=[self.current_catalog_record,RuntimeError('카탈로그 실패')]):
            with self.assertRaises(RuntimeError):editor.save_editor_changes({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)
        self.assertEqual({current_source_path:current_source_path.read_bytes() for current_source_path in current_source_paths},current_original_bytes)

    def test_ui_payload_rejects_fractional_occupancy(self):
        current_catalog_record={'revision':'r','assets':[{'texture':'sample','properties':self.current_property_values}]}
        current_table_values=[['sample','샘플',.5,1,1.5,1,100,'bottom',0,0,1,1,False,0]]
        with self.assertRaises(ValueError):build_asset_editor_payload(current_catalog_record,current_table_values)
        current_table_values[0][4]=1
        self.assertEqual(build_asset_editor_payload(current_catalog_record,current_table_values)['changes'],[{'texture':'sample','values':{'displayHeight':100}}])

    def test_ui_save_refreshes_baseline_for_second_edit(self):
        from tools.review.ui.gradio import asset_editor_app
        import copy
        current_catalog_record={'revision':'first','assets':[{'texture':'sample','name':'샘플','maps':[],'properties':self.current_property_values}]}
        current_table_values=[['sample','샘플',.5,1,1,1,100,'bottom',0,0,1,1,False,0]]
        for current_next_height,current_revision_value in ((100,'second'),(120,'third')):
            current_table_values[0][6]=current_next_height
            current_request_payload=build_asset_editor_payload(current_catalog_record,current_table_values)
            self.assertEqual(current_request_payload['changes'],[{'texture':'sample','values':{'displayHeight':current_next_height}}])
            current_next_catalog=copy.deepcopy(current_catalog_record)
            current_next_catalog['revision']=current_revision_value
            current_next_catalog['assets'][0]['properties'].update(displayHeight=current_next_height,billboardBlocksMovement=False)
            with patch.object(asset_editor_app,'execute_remote_management_command',side_effect=[{'count':1},current_next_catalog]):
                current_save_outputs=asset_editor_app.save_asset_editor_changes(current_catalog_record,current_table_values,{**current_request_payload,'token':'verified'})
            current_catalog_record,current_table_values=current_save_outputs[3:]
            self.assertEqual(current_catalog_record['revision'],current_revision_value)
            self.assertEqual(build_asset_editor_payload(current_catalog_record,current_table_values)['changes'],[])

    def test_shadow_properties_validate_and_save(self):
        current_shadow_payload={**self.current_request_payload,'changes':[{'texture':'sample','values':{'shadowOffsetColumn':.25,'shadowOffsetRow':-.5,'shadowScaleX':1.4,'shadowScaleY':.7}}]}
        current_preview_result=editor.preview_editor_changes(current_shadow_payload,self.current_asset_root)
        with patch.object(editor,'build_catalog_reference',return_value=self.current_catalog_record):
            editor.save_editor_changes({**current_shadow_payload,'token':current_preview_result['token']},self.current_asset_root)
        current_saved_values=editor.read_editor_snapshot(self.current_asset_root)[4]['data']['sample']
        self.assertEqual(current_saved_values['shadowOffsetColumn'],.25)
        self.assertEqual(current_saved_values['shadowScaleY'],.7)
        from tools.review.common.sprite_display_properties import validate_sprite_display_properties
        for current_invalid_values in ({'shadowScaleX':0},{'shadowOffsetRow':5},{'shadowScaleY':float('nan')}):
            with self.assertRaises(ValueError):validate_sprite_display_properties({'sample':{**self.current_property_values,**current_invalid_values}})

    def test_used_map_collision_warns_on_expansion(self):
        current_map_path=self.current_asset_root/'assets/maps/city_layouts/test.yaml'
        current_map_path.parent.mkdir()
        current_map_path.write_text(yaml.safe_dump({'data':{'columns':6,'rows':6,'objects':[{'id':'first','kind':'decoration','textureKey':'sample','position':{'column':2,'row':2}},{'id':'second','kind':'decoration','textureKey':'sample','position':{'column':3,'row':2}}]}}))
        _,current_preview_result=editor.prepare_editor_changes({**self.current_request_payload,'changes':[{'texture':'sample','values':{'groundFootprintColumns':2}}]},self.current_asset_root)
        self.assertIn('충돌',current_preview_result['map_warnings'][0]['message'])

    def test_editor_command_routes_share_gateway(self):
        from tools.review.common.management_gateway import resolve_management_command
        for current_command_name,current_route_path in [('asset-list','/editor-list'),('asset-preview','/editor-preview'),('asset-save','/editor-save')]:
            current_route_result=resolve_management_command('map-assets',current_command_name,{})
            self.assertEqual(current_route_result,('POST','/map-assets'+current_route_path))

    def test_manual_blocking_is_replaced_by_occupancy(self):
        current_change_payload={**self.current_request_payload,'changes':[{'texture':'sample','values':{'billboardBlocksMovement':True,'displayHeight':30,'billboardPlacementAnchor':'top'}}]}
        current_preview_result=editor.preview_editor_changes(current_change_payload,self.current_asset_root)
        self.assertFalse(current_preview_result['changes'][0]['after']['billboardBlocksMovement'])
        editor.save_editor_changes({**current_change_payload,'token':current_preview_result['token']},self.current_asset_root)
        current_latest_catalog={'revision':editor.read_editor_snapshot(self.current_asset_root)[3]}
        current_resize_payload={'revision':current_latest_catalog['revision'],'changes':[{'texture':'sample','values':{'displayHeight':300}}]}
        self.assertFalse(editor.preview_editor_changes(current_resize_payload,self.current_asset_root)['changes'][0]['after']['billboardBlocksMovement'])
