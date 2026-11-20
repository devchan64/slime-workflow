import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.map_assets import city_editor


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
        from tools.review.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.review.gateway_server import create_gateway_request_handler
        from tools.review.domains.map_assets.resize import handle_map_resize_request
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
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
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_address_value}), patch('tools.review.domains.hermes_agent.city_map_operations.HermesDelegationStore',return_value=current_store_value):
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
