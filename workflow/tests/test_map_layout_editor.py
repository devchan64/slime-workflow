"""격리된 맵 편집 저장과 실패 시 원본 보존 검사."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from workflow.domains.map_assets import map_editor
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES

class MapLayoutEditorTests(unittest.TestCase):
    def test_loaded_map_and_preview_match_ui_contract(self):
        import json
        import os
        import subprocess
        with patch.object(map_editor,'read_map_editor_billboard_identifiers',return_value=set()), patch.object(map_editor,'map_wall_tile_records',return_value={}), patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'file'}):
            source=map_editor.load_map_editor_document({'map':'sample'})
            preview=map_editor.preview_map_editor_changes(self.current_input_payload)
        root=Path(__file__).resolve().parents[2]
        script="""import assert from 'node:assert/strict';
          import {readMapCell,validMapDraftPreview} from './gui/mapDraftPreview.mjs';
          let input='';for await(const part of process.stdin)input+=part;
          const {source,preview}=JSON.parse(input);
          assert.deepEqual(readMapCell(source,'sample',{column:2,row:2}),{column:2,row:2,tile:'K',height:0,blocked:false});
          assert.throws(()=>readMapCell(source,'sample',{column:3,row:2}),/범위/);
          assert.equal(validMapDraftPreview(preview),true);"""
        subprocess.run(['node','--input-type=module','-e',script],input=json.dumps({'source':source,'preview':preview}),cwd=root,check=True,capture_output=True,text=True)

    def setUp(self):
        self.current_temp_root=tempfile.TemporaryDirectory();self.addCleanup(self.current_temp_root.cleanup)
        self.current_asset_root=Path(self.current_temp_root.name)/'slime-assets'
        self.current_source_paths=[self.current_asset_root/'assets/maps/field_tiles/sample.yaml',self.current_asset_root/'assets/maps/terrain/maps/sample.yaml']
        self.current_map_documents=[{'managementId':'tiles','data':{'rows':['KKK','KKK','KKK'],'objects':[{'id':'tower','kind':'ward-tower','position':{'column':1,'row':1}}]}},{'managementId':'terrain','data':{'terrainMovementVersion':2,'columns':3,'rows':3,'elevations':[[0]*3 for current_row_index in range(3)],'blocked':[]}}]
        for current_source_path,current_document_value in zip(self.current_source_paths,self.current_map_documents):current_source_path.parent.mkdir(parents=True,exist_ok=True);current_source_path.write_text(yaml.safe_dump(current_document_value))
        (self.current_asset_root/'assets/maps/field_tiles/codes.yaml').write_text('data: {K: angular-quarry-scree, H: dirt-road}\n')
        self.current_property_path=self.current_asset_root/'assets/maps/sprite-display-properties.yaml';self.current_property_path.write_text('data: {}\n')
        self.current_metadata_paths=[self.current_asset_root/'asset-registry.yaml',self.current_asset_root.parent/'slime-backend/map-data.lock.yaml',self.current_asset_root/'assets/billboards/catalog.yaml']
        for current_metadata_path in self.current_metadata_paths:
            current_metadata_path.parent.mkdir(parents=True,exist_ok=True)
            current_entries=[{'path':current_source_path.relative_to(self.current_asset_root).as_posix(),'sha256':hashlib.sha256(current_source_path.read_bytes()).hexdigest()} for current_source_path in self.current_source_paths]
            current_metadata_path.write_text(yaml.safe_dump({'assets' if current_metadata_path.name=='asset-registry.yaml' else 'files':current_entries},sort_keys=False))
        self.current_metadata_paths[2].write_text('schema_version: 1\nfamilies: {}\nbillboards: []\n')
        self.current_render_record={'id':'sample','startPoint':{'column':1,'row':1},'terrainCodes':{'K':'angular-quarry-scree','H':'dirt-road'},'connections':[{'direction':'east','column':2,'row':1}]}
        self.current_input_payload={'map':'sample','revision':'revision','cells':[{'column':0,'row':0,'tile':'H','height':1,'blocked':False}],'objects':[]}
        for current_patch_value in [patch.object(map_editor,'read_map_editor_snapshot',side_effect=self.read_test_snapshot),patch.object(map_editor,'load_registered_map_review',side_effect=lambda current_map_identifier:copy.deepcopy(self.current_render_record)),patch.object(map_editor,'MAP_EDITOR_STORAGE_ROOT',Path(self.current_temp_root.name)/'history'),patch.object(map_editor,'build_catalog_reference',return_value={'billboards':[]})]:current_patch_value.start();self.addCleanup(current_patch_value.stop)
    def read_test_snapshot(self,current_map_identifier):
        current_source_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in self.current_source_paths+[self.current_property_path]}
        return self.current_asset_root,self.current_source_paths,[yaml.safe_load(current_source_path.read_text()) for current_source_path in self.current_source_paths],current_source_bytes,'revision'
    def test_hermes_gateway_saves_isolated_map_and_recovers_receipt(self):
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from workflow.common.management_gateway import ManagementCommandGateway, execute_management_command
        from workflow.gateway_server import create_gateway_request_handler
        from workflow.domains.map_assets.resize import handle_map_resize_request
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_root_path = Path(self.current_temp_root.name)
        current_service_value = HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
        current_gateway_value = ManagementCommandGateway({'hermes-agent':current_service_value.handle_hermes_request,'map-assets':handle_map_resize_request})
        current_server_value = ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
        current_server_value.emit_gateway_trace = lambda *current_values:None
        current_thread_value = threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_thread_value.start()
        current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
        current_store_value = HermesDelegationStore(current_root_path/'receipts')
        try:
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_address_value,'SLIME_CONTENT_STORAGE':'file'}), patch('workflow.domains.hermes_agent.field_map_operations.HermesDelegationStore',return_value=current_store_value):
                current_preview_value = execute_management_command('hermes-agent','hermes-field-preview',{'draft':self.current_input_payload},current_address_value)
                self.assertTrue(current_preview_value['changed'])
                current_request_value = {'request_id':'field_http_123','draft':self.current_input_payload,'token':current_preview_value['token']}
                current_result_value = execute_management_command('hermes-agent','hermes-field-save',current_request_value,current_address_value)
                self.assertTrue(current_result_value['saved'])
                self.assertFalse(current_result_value['duplicate'])
                self.assertTrue(execute_management_command('hermes-agent','hermes-field-save',current_request_value,current_address_value)['duplicate'])
                current_receipt_value = execute_management_command('hermes-agent','hermes-field-receipt',{'request_id':'field_http_123'},current_address_value)
                self.assertEqual(current_receipt_value['state'],'completed')
                self.assertTrue(current_receipt_value['saved'])
                self.assertEqual(execute_management_command('hermes-agent','hermes-field-history',{},current_address_value)['records'][0]['request_id'],'field_http_123')
            self.assertEqual(yaml.safe_load(self.current_source_paths[0].read_text())['data']['rows'][0],'HKK')
            for current_source_path in self.current_source_paths:
                for current_metadata_path in self.current_metadata_paths[:2]:
                    self.assertIn(hashlib.sha256(current_source_path.read_bytes()).hexdigest(),current_metadata_path.read_text())
        finally:
            current_server_value.shutdown()
            current_thread_value.join(timeout=5)
            current_server_value.server_close()

    def test_save_updates_both_hashes_and_preserves_tower(self):
        current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        current_saved_record=map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_record['token']})
        self.assertTrue(current_saved_record['saved'])
        self.assertEqual(yaml.safe_load(self.current_source_paths[0].read_text())['data']['rows'][0],'HKK')
        self.assertEqual(yaml.safe_load(self.current_source_paths[0].read_text())['data']['objects'][0]['id'],'tower')
        for current_source_path in self.current_source_paths:
            for current_metadata_path in self.current_metadata_paths[:2]:self.assertIn(hashlib.sha256(current_source_path.read_bytes()).hexdigest(),current_metadata_path.read_text())
    def test_save_preserves_source_and_metadata_permissions(current_test_case):
        for current_file_path in current_test_case.current_source_paths+current_test_case.current_metadata_paths[:2]:
            current_file_path.chmod(0o640)
        current_preview=map_editor.preview_map_editor_changes(current_test_case.current_input_payload)
        map_editor.save_map_editor_changes({**current_test_case.current_input_payload,'token':current_preview['token']})
        for current_file_path in current_test_case.current_source_paths+current_test_case.current_metadata_paths[:2]:
            current_test_case.assertEqual(current_file_path.stat().st_mode & 0o777,0o640)

    def test_parallel_map_saves_are_serialized(current_test_case):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        import time
        current_active_count=0
        current_maximum_count=0
        current_count_lock=threading.Lock()
        def simulate_map_save(current_request_payload):
            nonlocal current_active_count,current_maximum_count
            with current_count_lock:
                current_active_count+=1
                current_maximum_count=max(current_maximum_count,current_active_count)
            time.sleep(0.02)
            with current_count_lock:current_active_count-=1
            return {'saved':True}
        with patch.object(map_editor,'save_locked_map_editor_changes',side_effect=simulate_map_save):
            with ThreadPoolExecutor(max_workers=4) as current_executor:
                list(current_executor.map(map_editor.save_map_editor_changes,[{}]*4))
        current_test_case.assertEqual(current_maximum_count,1)

    def test_interrupted_map_save_blocks_next_save_and_retains_backup(current_test_case):
        import json
        import os
        current_preview=map_editor.preview_map_editor_changes(current_test_case.current_input_payload)
        current_request={**current_test_case.current_input_payload,'token':current_preview['token']}
        current_original_replace=os.replace
        current_process_id=os.fork()
        if current_process_id==0:
            def interrupt_after_map_replace(current_source,current_destination):
                current_original_replace(current_source,current_destination)
                if Path(current_destination)==current_test_case.current_source_paths[0]:os._exit(73)
            with patch.object(map_editor.os,'replace',side_effect=interrupt_after_map_replace):
                map_editor.save_map_editor_changes(current_request)
            os._exit(1)
        _,current_status=os.waitpid(current_process_id,0)
        current_test_case.assertEqual(os.waitstatus_to_exitcode(current_status),73)
        current_marker=map_editor.MAP_EDITOR_STORAGE_ROOT/'map-save-pending.json'
        current_test_case.assertTrue(current_marker.is_file())
        current_blocked_preview=map_editor.preview_map_editor_changes(current_test_case.current_input_payload)
        current_test_case.assertFalse(current_blocked_preview['save_available'])
        current_test_case.assertEqual(current_blocked_preview['save_block_reason'],'interrupted')
        current_pending=json.loads(current_marker.read_text())
        current_backup=map_editor.MAP_EDITOR_STORAGE_ROOT/current_pending['backup']
        current_test_case.assertTrue((current_backup/'paths.json').is_file())
        current_test_case.assertEqual(hashlib.sha256((current_backup/'0').read_bytes()).hexdigest(),current_pending['before_sha256'][0])
        from workflow.domains.hermes_agent.map_pending_observer import inspect_hermes_map_pending_status
        with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_test_case.current_asset_root)}):
            current_observed=inspect_hermes_map_pending_status()
            current_test_case.assertEqual(current_observed['state'],'pending')
            current_test_case.assertEqual(current_observed['backup_valid'],len(current_pending['before_sha256']))
            current_test_case.assertGreaterEqual(current_observed['changed_since_backup'],1)
            current_first_file=next(current_item for current_item in current_observed['file_details'] if current_item['path']=='assets/maps/field_tiles/sample.yaml')
            current_test_case.assertEqual((current_first_file['current'],current_first_file['backup']),('after','valid'))
            current_test_case.assertNotIn(str(current_test_case.current_asset_root),str(current_observed))
            current_test_case.current_source_paths[0].write_text('다른 변경')
            current_observed=inspect_hermes_map_pending_status()
            current_first_file=next(current_item for current_item in current_observed['file_details'] if current_item['path']=='assets/maps/field_tiles/sample.yaml')
            current_test_case.assertEqual(current_first_file['current'],'changed')
            (current_backup/'0').write_text('corrupt')
            current_test_case.assertEqual(inspect_hermes_map_pending_status()['backup_invalid'],1)
        with current_test_case.assertRaisesRegex(ValueError,'완료되지 않은 야외 맵 저장'):
            map_editor.save_map_editor_changes(current_request)
        current_test_case.assertTrue(current_marker.is_file())

    def test_pending_observer_rejects_marker_that_grows_after_hash(self):
        from workflow.domains.hermes_agent import map_pending_observer
        from workflow.domains.hermes_agent import sprite_pending_observer
        current_marker_path=map_editor.MAP_EDITOR_STORAGE_ROOT/'map-save-pending.json'
        current_marker_path.parent.mkdir(parents=True,exist_ok=True)
        (current_marker_path.parent/'save.lock').touch()
        current_marker_path.write_bytes(b'{}')
        current_real_hash=sprite_pending_observer.read_sprite_pending_file_hash
        def grow_after_hash(current_file_path):
            current_hash_value=current_real_hash(current_file_path)
            if current_file_path==current_marker_path:current_file_path.write_bytes(b'x'*131073)
            return current_hash_value
        with patch.object(sprite_pending_observer,'read_sprite_pending_file_hash',side_effect=grow_after_hash):
            self.assertEqual(map_pending_observer.inspect_hermes_map_pending_status()['state'],'unavailable')
        with self.assertRaisesRegex(ValueError,'크기 초과'):
            map_pending_observer.read_bounded_map_pending_bytes(current_marker_path)

    def test_unreadable_pending_marker_blocks_preview_and_save(self):
        current_marker_path=map_editor.MAP_EDITOR_STORAGE_ROOT/'map-save-pending.json'
        current_original_bytes={current_path:current_path.read_bytes() for current_path in self.current_source_paths+self.current_metadata_paths}
        current_lstat_method=Path.lstat
        def reject_marker_stat(current_path_value,*current_arguments,**current_keywords):
            if current_path_value==current_marker_path:raise PermissionError('unreadable')
            return current_lstat_method(current_path_value,*current_arguments,**current_keywords)
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'lstat',autospec=True,side_effect=reject_marker_stat):
            current_preview_value=map_editor.preview_map_editor_changes(self.current_input_payload)
            self.assertFalse(current_preview_value['save_available'])
            self.assertIsNone(current_preview_value['save_block_reason'])
            from workflow.domains.hermes_agent.map_pending_observer import inspect_hermes_map_pending_status
            self.assertEqual(inspect_hermes_map_pending_status()['state'],'unavailable')
            with self.assertRaisesRegex(ValueError,'표식의 상태를 확인할 수 없습니다'):
                map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_value['token']})
        for current_path,current_content in current_original_bytes.items():self.assertEqual(current_path.read_bytes(),current_content)

    @unittest.skip('폐기된 Gradio UI 전용 검사')
    def test_direct_map_editor_blocks_unavailable_save_before_dispatch(self):
        from workflow.common import gradio_map_editor
        current_editor_state={'draft':self.current_input_payload}
        current_base_preview={'token':'a'*64,'changed':True,'render':{},'cells':1,'objects':0,'reachable':5}
        for current_reason_value,current_expected_text in (('database','DB 모드'),('interrupted','이전 저장이 중단'),(None,'확인할 수 없습니다')):
            current_preview_record={**current_base_preview,'save_available':False,'save_block_reason':current_reason_value}
            with self.subTest(reason=current_reason_value),patch.object(gradio_map_editor,'execute_remote_management_command',return_value=current_preview_record) as current_gateway_mock:
                current_review_value,_,current_notice,current_button=gradio_map_editor.preview_map_edit_draft(current_editor_state)
                self.assertIn(current_expected_text,current_notice)
                self.assertFalse(current_button['interactive'])
                current_gateway_mock.reset_mock()
                current_result=gradio_map_editor.save_map_edit_draft(current_editor_state,current_review_value)
                self.assertIn('저장 요청을 보내지 않았습니다',current_result[1])
                current_gateway_mock.assert_not_called()
        with patch.object(gradio_map_editor,'execute_remote_management_command',return_value={**current_base_preview,'save_available':True}):
            self.assertTrue(gradio_map_editor.preview_map_edit_draft(current_editor_state)[3]['interactive'])

    @unittest.skip('폐기된 Gradio UI 전용 검사')
    def test_direct_editor_preserves_draft_for_unverified_save_result(self):
        from workflow.common import gradio_map_editor
        current_editor_state={'draft':self.current_input_payload,'snapshot':{},'history':[{'old':True}],'future':[]}
        current_preview_record={'token':'a'*64,'save_available':True}
        for current_response_value in ({'saved':True,'map':'other'},{'saved':False,'map':'sample','unchanged':True},{'saved':'yes','map':'sample'}):
            with self.subTest(response=current_response_value),patch.object(gradio_map_editor,'execute_remote_management_command',return_value=current_response_value) as current_gateway_mock:
                current_result=gradio_map_editor.save_map_edit_draft(current_editor_state,current_preview_record)
                self.assertIs(current_result[0],current_editor_state)
                self.assertNotIn('저장 완료',current_result[1])
                current_gateway_mock.assert_called_once()
        with patch.object(gradio_map_editor,'execute_remote_management_command',side_effect=TimeoutError('lost')) as current_gateway_mock:
            current_result=gradio_map_editor.save_map_edit_draft(current_editor_state,current_preview_record)
            self.assertIn('결과 확인 불가',current_result[1])
            self.assertIs(current_result[0],current_editor_state)
            current_gateway_mock.assert_called_once()
        with patch.object(gradio_map_editor,'execute_remote_management_command',side_effect=[{'saved':True,'map':'sample'},TimeoutError('lost')]) as current_gateway_mock:
            current_result=gradio_map_editor.save_map_edit_draft(current_editor_state,current_preview_record)
            self.assertIn('원본을 확인할 수 없습니다',current_result[1])
            self.assertIs(current_result[0],current_editor_state)
            self.assertEqual(current_gateway_mock.call_count,2)
        with patch.object(gradio_map_editor,'execute_remote_management_command',side_effect=[{'saved':True,'map':'sample'},{'map':'sample','revision':'new-revision'}]):
            current_result=gradio_map_editor.save_map_edit_draft(current_editor_state,current_preview_record)
            self.assertIn('저장 완료',current_result[1])
            self.assertEqual(current_result[0]['draft']['revision'],'new-revision')
            self.assertEqual(current_result[0]['history'],[])

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
    def test_database_mode_save_rejects_before_database_write(self):
        import os
        current_original_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in self.current_source_paths+self.current_metadata_paths}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'files'}):
            current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch('workflow.domains.map_assets.database_client.execute_content_api_request') as current_database_mock:
            with self.assertRaisesRegex(ValueError,'DB 모드의 야외 맵 저장'):
                map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_record['token']})
            current_database_mock.assert_not_called()
        for current_source_path,current_original_value in current_original_bytes.items():
            self.assertEqual(current_source_path.read_bytes(),current_original_value)

    def test_hash_updates_target_paths_even_when_hashes_are_identical(self):
        current_old_hash='a'*64
        current_new_hash='b'*64
        current_source_text=yaml.safe_dump({'assets':[{'path':'assets/maps/one.yaml','sha256':current_old_hash},{'path':'assets/maps/two.yaml','sha256':current_old_hash}]},sort_keys=False)
        current_updated_text=map_editor.update_registered_map_hashes(current_source_text,{'assets/maps/one.yaml':(current_old_hash,current_new_hash)})
        current_asset_records=yaml.safe_load(current_updated_text)['assets']
        self.assertEqual([current_record['sha256'] for current_record in current_asset_records],[current_new_hash,current_old_hash])
        with self.assertRaisesRegex(ValueError,'누락 또는 중복'):
            map_editor.update_registered_map_hashes(current_source_text,{'assets/maps/missing.yaml':(current_old_hash,current_new_hash)})

    def test_invalid_metadata_stops_before_any_map_write(self):
        current_preview_record=map_editor.preview_map_editor_changes(self.current_input_payload)
        current_registry_path=self.current_metadata_paths[0]
        current_registry_record=yaml.safe_load(current_registry_path.read_text())
        current_registry_record['assets'][0]['sha256']='f'*64
        current_registry_path.write_text(yaml.safe_dump(current_registry_record,sort_keys=False))
        current_before_values={current_source_path:current_source_path.read_bytes() for current_source_path in self.current_source_paths+self.current_metadata_paths}
        with self.assertRaisesRegex(ValueError,'해시 불일치'):
            map_editor.save_map_editor_changes({**self.current_input_payload,'token':current_preview_record['token']})
        self.assertEqual({current_source_path:current_source_path.read_bytes() for current_source_path in current_before_values},current_before_values)

    def test_duplicate_map_paths_are_rejected(self):
        current_hash_value='a'*64
        current_metadata_text=yaml.safe_dump({'files':[{'path':'assets/maps/one.yaml','sha256':current_hash_value},{'path':'assets/maps/one.yaml','sha256':current_hash_value}]},sort_keys=False)
        with self.assertRaisesRegex(ValueError,'누락 또는 중복'):
            map_editor.update_registered_map_hashes(current_metadata_text,{'assets/maps/one.yaml':(current_hash_value,'b'*64)})

    def test_shared_yaml_hash_alias_is_rejected_before_update(self):
        current_hash_value='a'*64
        current_metadata_text='files:\n- path: assets/maps/one.yaml\n  sha256: &shared '+current_hash_value+'\n- path: assets/maps/two.yaml\n  sha256: *shared\n'
        with self.assertRaisesRegex(ValueError,'YAML 별칭'):
            map_editor.update_registered_map_hashes(current_metadata_text,{'assets/maps/two.yaml':(current_hash_value,'b'*64)})

    def test_gateway_commands_have_routes(self):
        for current_command_name in map_editor.MAP_EDITOR_ALLOWED_COMMANDS:
            self.assertIn(current_command_name,MANAGEMENT_SERVICE_COMMANDS['map-assets'])
            self.assertEqual(MANAGEMENT_COMMAND_ROUTES[current_command_name],('POST','/editor-'+current_command_name))
    def test_wall_paint_preview_and_save_preserves_floor(self):
        current_wall_payload={**self.current_input_payload,'cells':[{'column':0,'row':0,'tile':'K','height':0,'blocked':False,'wall':'cliff-wall'}]}
        with patch('workflow.common.map_asset_sources.validate_map_cliff_texture',return_value='cliff-wall'):
            current_preview_record=map_editor.preview_map_editor_changes(current_wall_payload)
            self.assertEqual(current_preview_record['render']['cliffOverrides'],[{'position':{'column':0,'row':0},'textureKey':'cliff-wall'}])
            map_editor.save_map_editor_changes({**current_wall_payload,'token':current_preview_record['token']})
        current_saved_tiles=yaml.safe_load(self.current_source_paths[0].read_text())['data']
        self.assertEqual(current_saved_tiles['rows'],['KKK']*3)
        self.assertEqual(current_saved_tiles['cliffOverrides'],current_preview_record['render']['cliffOverrides'])
    def test_ambient_tint_save_omission_and_reset(self):
        current_tint_payload={**self.current_input_payload,'ambientTint':'#607c90'}
        current_preview_record=map_editor.preview_map_editor_changes(current_tint_payload)
        self.assertEqual(current_preview_record['render']['ambientTint'],'#607c90')
        map_editor.save_map_editor_changes({**current_tint_payload,'token':current_preview_record['token']})
        self.assertEqual(yaml.safe_load(self.current_source_paths[1].read_text())['data']['ambientTint'],'#607c90')
        self.assertEqual(map_editor.preview_map_editor_changes(self.current_input_payload)['render']['ambientTint'],'#607c90')
        self.assertEqual(map_editor.preview_map_editor_changes({**self.current_input_payload,'ambientTint':'#ffffff'})['render']['ambientTint'],'#ffffff')
        with self.assertRaisesRegex(ValueError,'ambientTint'):
            map_editor.preview_map_editor_changes({**self.current_input_payload,'ambientTint':None})

    def test_terrain_effect_preview_save_and_omission_preserve(self):
        current_effect_record=dict(version=1,id='test-glow',kind='glow',position=dict(column=1,row=1),color='#ffe8a3',radius=1,intensity=.6,periodMs=4000,height=20,seed=1)
        current_effect_payload={**self.current_input_payload,'terrainEffects':[current_effect_record]}
        current_preview_record=map_editor.preview_map_editor_changes(current_effect_payload)
        self.assertEqual(current_preview_record['render']['terrainEffects'],[current_effect_record])
        map_editor.save_map_editor_changes({**current_effect_payload,'token':current_preview_record['token']})
        self.assertEqual(yaml.safe_load(self.current_source_paths[1].read_text())['data']['terrainEffects'],[current_effect_record])
        current_preserved_preview=map_editor.preview_map_editor_changes(self.current_input_payload)
        self.assertEqual(current_preserved_preview['render']['terrainEffects'],[current_effect_record])
        current_deleted_preview=map_editor.preview_map_editor_changes({**self.current_input_payload,'terrainEffects':[]})
        self.assertEqual(current_deleted_preview['render']['terrainEffects'],[])
    def test_terrain_effect_missing_attachment_rejects_before_write(self):
        current_effect_record=dict(version=1,id='test-glow',kind='glow',objectId='deleted-object',color='#ffe8a3',radius=1,intensity=.6,periodMs=4000,height=20,seed=1)
        with self.assertRaisesRegex(ValueError,'연결 대상'):
            map_editor.preview_map_editor_changes({**self.current_input_payload,'terrainEffects':[current_effect_record]})


class TerrainAmbientContractTest(unittest.TestCase):
    def test_reject_invalid_ambient_values(self):
        from workflow.domains.map_assets.terrain_ambient import validate_terrain_ambient_tint
        validate_terrain_ambient_tint({})
        validate_terrain_ambient_tint({'ambientTint':'#607c90'})
        for current_invalid_color in [None,True,123,'red','#fff']:
            with self.assertRaises(ValueError):validate_terrain_ambient_tint({'ambientTint':current_invalid_color})
