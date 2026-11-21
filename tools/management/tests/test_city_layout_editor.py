import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.management.domains.map_assets import city_editor


class CityEditorTests(unittest.TestCase):
    def setUp(self):
        self.document = {'managementId':'config.city-layouts.stonewarm','data':{'version':1,'cityId':'stonewarm','columns':5,'rows':5,'safeTown':True,'terrainRows':['sspss']*5,'startPoint':{'column':2,'row':3},'buildings':[{'id':'stonewarm-guild','name':'길드','facilityId':'stonewarm-guild','origin':{'column':0,'row':1},'width':1,'height':1,'facing':'east','entrance':{'column':1,'row':1},'sprite':{'textureKey':'town-test-guild-v1','contentWidth':0.8}}],'objects':[],'connections':[{'column':2,'row':0,'direction':'north','id':'gate','target':'other'}]}}
        self.properties = {'town-test-guild-v1':{'anchorX':0.5,'anchorY':1.0}}
        self.bundle = {'generation':5,'revisions':{'city_layouts/stonewarm.yaml':2},'documents':{'city_layouts/stonewarm.yaml':copy.deepcopy(self.document),'sprite-display-properties.yaml':{'data':self.properties}}}
        self.payload = {'map':'stonewarm','generation':5,'revision':2,'document':copy.deepcopy(self.document)}
        self.temporary = tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        for current_patch in [patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch.object(city_editor,'CITY_EDITOR_STORAGE_ROOT',Path(self.temporary.name)),patch.object(city_editor,'execute_content_api_request',side_effect=self.mock_api),patch.object(city_editor,'read_validated_city_editor_sources',side_effect=lambda current_bundle_value,current_document_name:(copy.deepcopy(current_bundle_value['documents'][current_document_name]),copy.deepcopy(current_bundle_value['documents']['sprite-display-properties.yaml']['data'])))]:
            current_patch.start();self.addCleanup(current_patch.stop)
        self.saved=[]
    def mock_api(self,current_method,current_route,current_payload=None):
        if 'review-bundle' in current_route:return copy.deepcopy(self.bundle)
        if current_route.endswith('map-changes'):
            self.saved.append(current_payload);return {'saved':True}
        raise AssertionError('예상하지 못한 서비스 경로: '+current_route)
    def test_hermes_gateway_city_save_uses_existing_db_contract(self):
        import threading
        from http.server import ThreadingHTTPServer
        from tools.management.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.management.gateway_server import create_gateway_request_handler
        from tools.management.domains.map_assets.resize import handle_map_resize_request
        from tools.management.domains.hermes_agent.service import HermesServiceManager
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_root_path = Path(self.temporary.name)
        current_service_value = HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
        current_gateway_value = ManagementCommandGateway({'hermes-agent':current_service_value.handle_hermes_request,'map-assets':handle_map_resize_request})
        current_server_value = ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
        current_server_value.emit_gateway_trace = lambda *current_values:None
        current_thread_value = threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_thread_value.start()
        current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
        current_store_value = HermesDelegationStore(current_root_path/'receipts')
        try:
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_address_value}), patch('tools.management.domains.hermes_agent.city_map_operations.HermesDelegationStore',return_value=current_store_value):
                current_loaded_value = execute_management_command('hermes-agent','hermes-city-load',{'map':'stonewarm'},current_address_value)
                self.assertEqual(current_loaded_value,self.payload)
                current_noop_preview = execute_management_command('hermes-agent','hermes-city-preview',{'draft':self.payload},current_address_value)
                current_request_value = {'request_id':'city_noop_123','draft':self.payload,'token':current_noop_preview['token']}
                with self.assertRaises(ValueError):
                    execute_management_command('hermes-agent','hermes-city-save',current_request_value,current_address_value)
                self.assertEqual(execute_management_command('hermes-agent','hermes-city-receipt',{'request_id':'city_noop_123'},current_address_value)['state'],'not_found')
                self.assertEqual(self.saved,[])
        finally:
            current_server_value.shutdown()
            current_thread_value.join(timeout=5)
            current_server_value.server_close()

    def test_city_plan_aligns_file_hashes_and_database_without_writing(self):
        import hashlib
        import json
        import yaml
        current_asset_root=Path(self.temporary.name)/'assets-repository'
        current_source_path=current_asset_root/'assets/maps/city_layouts/stonewarm.yaml'
        current_source_path.parent.mkdir(parents=True)
        current_source_path.write_text(yaml.safe_dump(self.document,allow_unicode=True,sort_keys=False))
        current_registry_path=current_asset_root/'asset-registry.yaml'
        current_backend_path=Path(self.temporary.name)/'slime-backend/map-data.lock.yaml'
        current_backend_path.parent.mkdir(parents=True)
        current_source_hash=hashlib.sha256(current_source_path.read_bytes()).hexdigest()
        current_relative_path='assets/maps/city_layouts/stonewarm.yaml'
        current_registry_path.write_text(yaml.safe_dump({'assets':[{'path':current_relative_path,'sha256':current_source_hash}]}))
        current_backend_path.write_text(yaml.safe_dump({'files':[{'path':current_relative_path,'sha256':current_source_hash}]}))
        current_source_bytes={current_path_value:current_path_value.read_bytes() for current_path_value in (current_source_path,current_registry_path,current_backend_path)}
        current_new_document=copy.deepcopy(self.document)
        current_new_document['data']['version']=2
        current_plan_value=city_editor.prepare_city_source_update_plan(current_asset_root,self.payload,current_new_document,'city-db-request',current_source_bytes,[current_registry_path,current_backend_path])
        from tools.management.domains.map_assets.map_recovery_assessment import assess_map_plan_evidence
        current_receipt_record={'state':'matched','request_sha256':current_plan_value['request_sha256']}
        current_mixed_files={**current_source_bytes,current_source_path:current_plan_value['pending_files'][current_source_path]}
        current_assessment_record=assess_map_plan_evidence(current_plan_value,current_source_bytes,current_mixed_files,current_receipt_record)
        self.assertEqual(current_assessment_record['state'],'files_incomplete')
        self.assertEqual(assess_map_plan_evidence(current_plan_value,current_source_bytes,current_plan_value['pending_files'],current_receipt_record)['state'],'files_match_receipt')
        current_database_request=current_plan_value['database_request']
        current_test_hash=hashlib.sha256(json.dumps(current_database_request,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        self.assertEqual(current_plan_value['request_sha256'],current_test_hash)
        self.assertEqual(current_database_request['documents'][0]['document'],current_new_document)
        current_new_hash=hashlib.sha256(current_plan_value['pending_files'][current_source_path]).hexdigest()
        self.assertEqual(yaml.safe_load(current_plan_value['pending_files'][current_registry_path])['assets'][0]['sha256'],current_new_hash)
        self.assertEqual(yaml.safe_load(current_plan_value['pending_files'][current_backend_path])['files'][0]['sha256'],current_new_hash)
        self.assertEqual(yaml.safe_load(current_plan_value['pending_files'][current_source_path]),current_new_document)
        for current_path_value,current_original_bytes in current_source_bytes.items():self.assertEqual(current_path_value.read_bytes(),current_original_bytes)
        with patch('tools.management.common.map_tile_assets.load_registered_tiles',return_value=(current_asset_root,{})), patch.object(city_editor,'read_city_editor_snapshot',return_value={**self.payload,'properties':self.properties}):
            current_summary_value=city_editor.inspect_city_source_plan({**self.payload,'properties':self.properties},current_new_document,'a'*64)
            self.assertEqual(current_summary_value,{'status':'available','before_sha256':current_source_hash,'after_sha256':current_new_hash})
        with patch('tools.management.common.map_tile_assets.load_registered_tiles',return_value=(current_asset_root,{})), patch.object(city_editor,'read_city_editor_snapshot',return_value={**self.payload,'generation':6,'properties':self.properties}):
            self.assertEqual(city_editor.inspect_city_source_plan({**self.payload,'properties':self.properties},current_new_document,'a'*64),{'status':'unavailable'})
        with patch('tools.management.common.map_tile_assets.load_registered_tiles',return_value=(current_asset_root,{})), patch.object(city_editor,'read_city_editor_snapshot',return_value={**self.payload,'properties':self.properties}):
            current_backend_path.write_text('files: [')
            self.assertEqual(city_editor.inspect_city_source_plan({**self.payload,'properties':self.properties},current_new_document,'a'*64),{'status':'unavailable'})
            current_backend_path.write_bytes(current_source_bytes[current_backend_path])
        def mutate_during_final_snapshot(current_request_value):
            current_source_path.write_bytes(current_source_bytes[current_source_path]+b'\n')
            return {**self.payload,'properties':self.properties}
        with patch('tools.management.common.map_tile_assets.load_registered_tiles',return_value=(current_asset_root,{})), patch.object(city_editor,'read_city_editor_snapshot',side_effect=mutate_during_final_snapshot):
            self.assertEqual(city_editor.inspect_city_source_plan({**self.payload,'properties':self.properties},current_new_document,'a'*64),{'status':'unavailable'})
        current_source_path.write_bytes(current_source_bytes[current_source_path])
        current_new_document['data']['version']=3
        self.assertEqual(current_database_request['documents'][0]['document']['data']['version'],2)
        self.assertEqual(yaml.safe_load(current_plan_value['pending_files'][current_source_path])['data']['version'],2)
        current_wrong_snapshot=copy.deepcopy(self.payload)
        current_wrong_snapshot['document']['data']['version']=99
        with self.assertRaisesRegex(ValueError,'일치하지 않습니다'):
            city_editor.prepare_city_source_update_plan(current_asset_root,current_wrong_snapshot,current_new_document,'city-db-request',current_source_bytes,[current_registry_path,current_backend_path])
        with self.assertRaisesRegex(ValueError,'잠금 경로 오류'):
            city_editor.prepare_city_source_update_plan(current_asset_root,self.payload,current_new_document,'city-db-request',current_source_bytes,[current_registry_path,current_source_path])
        current_stale_bytes=dict(current_source_bytes)
        current_stale_bytes[current_backend_path]=yaml.safe_dump({'files':[{'path':current_relative_path,'sha256':'0'*64}]}).encode()
        with self.assertRaisesRegex(ValueError,'해시 불일치'):
            city_editor.prepare_city_source_update_plan(current_asset_root,self.payload,current_new_document,'city-db-request',current_stale_bytes,[current_registry_path,current_backend_path])
        self.assertFalse(self.saved)

    def test_city_preview_plan_reaches_hermes_conversation_without_saving(self):
        import hashlib
        import json
        import yaml
        from tools.management.domains.hermes_agent import city_map_operations
        from tools.management.ui.gradio import hermes_agent_app
        current_asset_root=Path(self.temporary.name)/'slime-assets'
        current_source_path=current_asset_root/'assets/maps/city_layouts/stonewarm.yaml'
        current_source_path.parent.mkdir(parents=True)
        current_source_path.write_text(yaml.safe_dump(self.document,allow_unicode=True,sort_keys=False))
        current_registry_path=current_asset_root/'asset-registry.yaml'
        current_backend_path=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
        current_backend_path.parent.mkdir(parents=True)
        current_source_hash=hashlib.sha256(current_source_path.read_bytes()).hexdigest()
        current_relative_path='assets/maps/city_layouts/stonewarm.yaml'
        current_registry_path.write_text(yaml.safe_dump({'assets':[{'path':current_relative_path,'sha256':current_source_hash}]}))
        current_backend_path.write_text(yaml.safe_dump({'files':[{'path':current_relative_path,'sha256':current_source_hash}]}))
        current_original_files={current_path:current_path.read_bytes() for current_path in (current_source_path,current_registry_path,current_backend_path)}
        current_edited_draft=copy.deepcopy(self.payload)
        current_edited_draft['document']['data']['buildings'][0]['name']='새 길드 이름'
        def route_test_city_editor(current_command_name,current_request_record):
            if current_command_name=='city-edit-preview':return city_editor.preview_city_editor_changes(current_request_record)
            if current_command_name=='city-edit-load':return city_editor.load_city_editor_document(current_request_record)
            raise AssertionError('저장 명령은 호출하지 않습니다.')
        def route_test_hermes_gateway(current_service_name,current_command_name,current_request_record):
            self.assertEqual(current_command_name,'hermes-city-preview')
            return city_map_operations.preview_hermes_city_map(current_request_record['draft'])
        with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch('tools.management.common.map_tile_assets.load_registered_tiles',return_value=(current_asset_root,{})),patch.object(city_map_operations,'call_field_map_editor',side_effect=route_test_city_editor),patch('tools.management.domains.map_assets.source_consistency.inspect_city_source_alignment',return_value={'status':'matched','note':'fixture'}),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=route_test_hermes_gateway):
            current_review_record,current_notice_text,_=hermes_agent_app.review_hermes_city_map_draft(json.dumps(current_edited_draft,ensure_ascii=False),'city_request_123')
        self.assertIn('원본 변경 계획: 해시 계산됨',current_notice_text)
        self.assertIn('변경 전 SHA-256: '+current_source_hash,current_notice_text)
        self.assertIn('신규 저장은 사용할 수 없습니다',current_notice_text)
        self.assertEqual(current_review_record['draft'],current_edited_draft)
        self.assertFalse(self.saved)
        for current_path,current_original_bytes in current_original_files.items():self.assertEqual(current_path.read_bytes(),current_original_bytes)

    def test_preview_succeeds_but_direct_city_save_is_blocked(self):
        self.payload['document']['data']['version']=2
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        self.assertTrue(current_preview['changed'])
        with self.assertRaisesRegex(ValueError,'동기 저장이 구현될 때까지 중단'):
            city_editor.save_city_editor_changes({**self.payload,'token':current_preview['token']})
        self.assertEqual(self.saved,[])
    def test_invalid_stale_and_changed_drafts_rejected(self):
        with self.assertRaisesRegex(ValueError,'변경되었습니다'):city_editor.preview_city_editor_changes({**self.payload,'revision':1})
        current_invalid=copy.deepcopy(self.payload);current_invalid['document']['data']['buildings'][0]['entrance']['column']=4
        with self.assertRaisesRegex(ValueError,'출입구'):city_editor.preview_city_editor_changes(current_invalid)
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        with self.assertRaisesRegex(ValueError,'먼저 검증'):city_editor.save_city_editor_changes({**current_invalid,'token':current_preview['token']})
        self.assertFalse(self.saved)
    def test_change_after_preview_is_rejected(self):
        current_preview=city_editor.preview_city_editor_changes(self.payload)
        self.bundle['generation']+=1
        with self.assertRaisesRegex(ValueError,'동기 저장이 구현될 때까지 중단'):city_editor.save_city_editor_changes({**self.payload,'token':current_preview['token']})
        self.assertFalse(self.saved)

if __name__ == '__main__':unittest.main()
