import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.kimodo_keyframe_operations import read_hermes_keyframe_receipt, save_hermes_keyframe_once, preview_hermes_keyframe_source


class HermesKimodoKeyframeOperationsTests(unittest.TestCase):
    def test_duplicate_and_uncertain_receipts_do_not_repeat_save(self):
        current_request_record={'job_id':'2026-11-06_12-00-00-12345678','attempt_id':'a'*32,'frame':3,'tag':'테스트','review_sha256':'b'*64}
        current_result_record={'id':'c'*32,'source_job':current_request_record['job_id'],'source_attempt':current_request_record['attempt_id'],'source_frame':3,'tag':'테스트'}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_value=HermesDelegationStore(Path(current_directory_name))
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.execute_management_command',return_value=current_result_record) as current_gateway_mock:
                current_first_result=save_hermes_keyframe_once('request_001',current_request_record)
                self.assertEqual(current_first_result['state'],'completed')
                self.assertFalse(current_first_result['duplicate'])
                current_second_result=save_hermes_keyframe_once('request_001',current_request_record)
                self.assertTrue(current_second_result['duplicate'])
                self.assertEqual(current_second_result['keyframe_id'],'c'*32)
                self.assertEqual(current_gateway_mock.call_count,1)
                with self.assertRaises(ValueError):save_hermes_keyframe_once('request_001',{**current_request_record,'frame':4})
                self.assertEqual(read_hermes_keyframe_receipt('request_001')['state'],'completed')
                current_gateway_mock.side_effect=TimeoutError('response lost')
                with self.assertRaises(TimeoutError):save_hermes_keyframe_once('request_002',current_request_record)
                current_unknown_receipt=read_hermes_keyframe_receipt('request_002')
                self.assertEqual(current_unknown_receipt['state'],'unknown')
                self.assertEqual(current_unknown_receipt['source'],{current_key:current_request_record[current_key] for current_key in ('job_id','attempt_id','frame','tag')})
                self.assertEqual(save_hermes_keyframe_once('request_002',current_request_record)['state'],'unknown')
                self.assertEqual(current_gateway_mock.call_count,2)
                self.assertEqual(read_hermes_keyframe_receipt('request_003')['state'],'not_found')

    def test_legacy_receipt_without_source_is_still_readable(self):
        import json
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_value=HermesDelegationStore(Path(current_directory_name))
            (Path(current_directory_name)/'request_legacy.json').write_text(json.dumps({'version':14,'id':'request_legacy','request_sha256':'a'*64,'state':'dispatching'}))
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value):
                current_receipt_value=read_hermes_keyframe_receipt('request_legacy')
                self.assertEqual(current_receipt_value['state'],'unknown')
                self.assertNotIn('source',current_receipt_value)

    def test_unidentified_legacy_chat_receipt_blocks_new_chat_save(self):
        import json
        current_request_record={'job_id':'2026-11-06_12-00-00-12345678','attempt_id':'a'*32,'frame':3,'tag':'테스트','review_sha256':'b'*64}
        current_legacy_identifier='keyframe_'+'c'*64
        current_new_identifier='keyframe_'+'d'*64
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_storage_value=HermesDelegationStore(current_storage_root)
            (current_storage_root/(current_legacy_identifier+'.json')).write_text(json.dumps({'version':14,'id':current_legacy_identifier,'request_sha256':'e'*64,'state':'dispatching'}))
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.execute_management_command') as current_gateway_mock:
                with self.assertRaisesRegex(ValueError,'이전 키프레임 접수'):save_hermes_keyframe_once(current_new_identifier,current_request_record)
                current_gateway_mock.assert_not_called()
                self.assertEqual(read_hermes_keyframe_receipt(current_new_identifier)['state'],'not_found')
                self.assertEqual(read_hermes_keyframe_receipt(current_legacy_identifier)['state'],'unknown')

    def test_review_reports_legacy_block_and_save_rechecks(self):
        import json
        current_job_identifier='2026-11-06_12-00-00-12345678'
        current_attempt_identifier='a'*32
        current_request_record={'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':3,'tag':'테스트','review_sha256':'b'*64}
        current_review_record={**current_request_record,'frame_count':5,'source_motion':'motion.npz','image':'/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-002.png','image_sha256':'c'*64}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_storage_value=HermesDelegationStore(current_storage_root)
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.execute_management_command',return_value=current_review_record) as current_gateway_mock:
                self.assertEqual(preview_hermes_keyframe_source(current_job_identifier,current_attempt_identifier,3,'테스트')['chat_save_readiness'],'ready')
                current_legacy_identifier='keyframe_'+'c'*64
                (current_storage_root/(current_legacy_identifier+'.json')).write_text(json.dumps({'version':14,'id':current_legacy_identifier,'request_sha256':'d'*64,'state':'dispatching'}))
                current_blocked_review=preview_hermes_keyframe_source(current_job_identifier,current_attempt_identifier,3,'테스트')
                self.assertEqual(current_blocked_review['chat_save_readiness'],'check_required')
                self.assertEqual(current_blocked_review['legacy_receipts'],{'records':[{'request_id':current_legacy_identifier,'state':'unknown'}],'truncated':False})
                current_gateway_mock.reset_mock()
                with self.assertRaises(ValueError):save_hermes_keyframe_once('keyframe_'+'e'*64,current_request_record)
                current_gateway_mock.assert_not_called()

    def test_legacy_blocker_list_limits_results_and_detects_unreadable_records(self):
        from workflow.domains.hermes_agent.kimodo_keyframe_operations import inspect_legacy_keyframe_receipts
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            for current_index_value in range(21):
                (current_storage_root/('keyframe_'+format(current_index_value,'064x')+'.json')).write_text('not-json')
            current_blocker_value=inspect_legacy_keyframe_receipts(HermesDelegationStore(current_storage_root))
            self.assertEqual(len(current_blocker_value['records']),20)
            self.assertTrue(current_blocker_value['truncated'])
            self.assertTrue(all(current_record_value['state']=='unavailable' for current_record_value in current_blocker_value['records']))

    def test_legacy_scan_stops_at_directory_entry_limit(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from workflow.domains.hermes_agent.kimodo_keyframe_operations import inspect_legacy_keyframe_receipts
        current_scan_context=MagicMock()
        current_entries_value=(SimpleNamespace(name='unrelated_'+str(current_index_value)) for current_index_value in range(10002))
        current_scan_context.__enter__.return_value=current_entries_value
        with tempfile.TemporaryDirectory() as current_directory_name, patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.os.scandir',return_value=current_scan_context):
            with self.assertRaisesRegex(ValueError,'너무 많아'):
                inspect_legacy_keyframe_receipts(HermesDelegationStore(Path(current_directory_name)))
            self.assertEqual(next(current_entries_value).name,'unrelated_10001')

    def test_mismatched_result_is_unknown_and_invalid_request_does_not_dispatch(self):
        current_request_record={'job_id':'2026-11-06_12-00-00-12345678','attempt_id':'a'*32,'frame':3,'tag':'테스트','review_sha256':'b'*64}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_value=HermesDelegationStore(Path(current_directory_name))
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.execute_management_command',return_value={'id':'c'*32}) as current_gateway_mock:
                with self.assertRaises(ValueError):save_hermes_keyframe_once('request_004',{**current_request_record,'frame':True})
                current_gateway_mock.assert_not_called()
                with self.assertRaises(ValueError):save_hermes_keyframe_once('request_004',current_request_record)
                self.assertEqual(read_hermes_keyframe_receipt('request_004')['state'],'unknown')
                self.assertTrue(save_hermes_keyframe_once('request_004',current_request_record)['duplicate'])
                current_gateway_mock.assert_called_once()

    def test_review_checks_identity_and_filters_untrusted_fields(self):
        current_job_identifier='2026-11-06_12-00-00-12345678'
        current_attempt_identifier='a'*32
        current_review_record={'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':3,'tag':'테스트','frame_count':5,'source_motion':'motion.npz','image':'/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-002.png','image_sha256':'b'*64,'review_sha256':'c'*64,'private_path':'secret'}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_value=HermesDelegationStore(Path(current_directory_name))
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_storage_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.execute_management_command',return_value=current_review_record) as current_gateway_mock:
                current_result_value=preview_hermes_keyframe_source(current_job_identifier,current_attempt_identifier,3,'테스트')
                self.assertNotIn('private_path',current_result_value)
                self.assertEqual(current_result_value['chat_save_readiness'],'ready')
                current_gateway_mock.assert_called_once()
                current_review_record['image']='/other/path'
                with self.assertRaises(ValueError):preview_hermes_keyframe_source(current_job_identifier,current_attempt_identifier,3,'테스트')

    def test_service_dispatches_review_save_and_receipt(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        current_request_record={'job_id':'2026-11-06_12-00-00-12345678','attempt_id':'a'*32,'frame':3,'tag':'테스트','review_sha256':'b'*64}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manager_value=HermesServiceManager(hermes_storage_root=Path(current_directory_name)/'jobs')
            with patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.preview_hermes_keyframe_source',return_value={'review_sha256':'b'*64}) as current_preview_mock, patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.save_hermes_keyframe_once',return_value={'state':'completed'}) as current_save_mock, patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.read_hermes_keyframe_receipt',return_value={'state':'completed'}) as current_receipt_mock:
                current_preview_request={current_key:current_request_record[current_key] for current_key in ('job_id','attempt_id','frame','tag')}
                self.assertEqual(current_manager_value.execute_hermes_command('hermes-kimodo-keyframe-source-review',current_preview_request)['review_sha256'],'b'*64)
                self.assertEqual(current_manager_value.execute_hermes_command('hermes-kimodo-keyframe-save',{'request_id':'request_001',**current_request_record})['state'],'completed')
                self.assertEqual(current_manager_value.execute_hermes_command('hermes-kimodo-keyframe-receipt',{'request_id':'request_001'})['state'],'completed')
                current_preview_mock.assert_called_once()
                current_save_mock.assert_called_once_with('request_001',current_request_record)
                current_receipt_mock.assert_called_once_with('request_001')
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-kimodo-keyframe-save',{'request_id':'request_001',**current_request_record,'extra':True})

    def test_mcp_through_gateway_saves_one_temporary_keyframe(self):
        import hashlib
        import json
        import os
        import subprocess
        import threading
        from http.server import ThreadingHTTPServer
        import numpy as np
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        from workflow.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES
        from workflow.gateway_server import create_gateway_request_handler
        current_repository_root=Path(__file__).resolve().parents[2]
        current_runtime_python=current_repository_root/'.local/hermes-mcp/bin/python'
        if not current_runtime_python.is_file():self.skipTest('Hermes MCP 런타임이 설치되지 않았습니다.')
        current_client_script=r'''
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def test_keyframe_roundtrip():
 current_parameters=StdioServerParameters(command=sys.executable,args=['workflow/domains/hermes_agent/mcp_server.py'],cwd=os.getcwd(),env=dict(os.environ))
 async with stdio_client(current_parameters) as (current_reader,current_writer):
  async with ClientSession(current_reader,current_writer) as current_session:
   await current_session.initialize()
   async def call_checked_tool(current_name,current_arguments):
    current_result=await current_session.call_tool(current_name,current_arguments)
    if current_result.is_error:raise RuntimeError(str(current_result.content))
    return current_result.structured_content or json.loads(current_result.content[0].text)
   current_source={'job_identifier_value':'2026-11-18_00-00-00-12345678','attempt_identifier_value':'a'*32,'frame_number_value':1,'tag_text_value':'임시 검증'}
   current_review=await call_checked_tool('preview_hermes_kimodo_keyframe_source',current_source)
   current_invalid_arguments={'request_identifier_value':'integration_002',**current_source,'review_digest_value':'f'*64}
   current_invalid_result=await current_session.call_tool('save_hermes_kimodo_keyframe',current_invalid_arguments)
   assert current_invalid_result.is_error
   current_uncertain_receipt=await call_checked_tool('read_hermes_kimodo_keyframe_receipt',{'request_identifier_value':'integration_002'})
   assert current_uncertain_receipt['state']=='unknown'
   current_repeat_result=await call_checked_tool('save_hermes_kimodo_keyframe',current_invalid_arguments)
   assert current_repeat_result['state']=='unknown' and current_repeat_result['duplicate'] is True
   current_save_arguments={'request_identifier_value':'integration_001',**current_source,'review_digest_value':current_review['review_sha256']}
   current_first=await call_checked_tool('save_hermes_kimodo_keyframe',current_save_arguments)
   current_second=await call_checked_tool('save_hermes_kimodo_keyframe',current_save_arguments)
   current_receipt=await call_checked_tool('read_hermes_kimodo_keyframe_receipt',{'request_identifier_value':'integration_001'})
   assert current_first['state']=='completed' and current_first['duplicate'] is False
   assert current_second['state']=='completed' and current_second['duplicate'] is True
   assert current_first['keyframe_id']==current_second['keyframe_id']==current_receipt['keyframe_id']
   print(current_first['keyframe_id'])
asyncio.run(test_keyframe_roundtrip())
'''
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_kimodo_manager=KimodoGenerationManager()
            current_kimodo_manager.job_storage_root=current_root_path/'jobs'
            current_kimodo_manager.keyframe_storage_root=current_root_path/'keyframes'
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_attempt_identifier='a'*32
            current_job_path=current_kimodo_manager.job_storage_root/current_job_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_preview_bytes=b'\x89PNG\r\n\x1a\nfixture'
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier}))
            (current_attempt_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[hashlib.sha256(current_preview_bytes).hexdigest()]}))
            (current_attempt_path/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':list(range(77)),'parents':list(range(77))}))
            (current_attempt_path/'output-000.png').write_bytes(current_preview_bytes)
            current_arrays_value={current_name:np.zeros((1,*current_shape),dtype=np.float32) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            current_arrays_value['root_positions'][0,0]=7
            np.savez_compressed(current_attempt_path/'motion.npz',**current_arrays_value)
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'kimodo':current_kimodo_manager.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_arguments:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server_value.server_port)
            current_environment=dict(os.environ,SLIME_MANAGEMENT_GATEWAY_URL=current_gateway_url,PYTHONPATH=str(current_repository_root),CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_process_value=subprocess.run([str(current_runtime_python),'-c',current_client_script],cwd=current_repository_root,env=current_environment,capture_output=True,text=True,timeout=30)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr[-4000:])
                current_saved_identifiers=[current_path.name for current_path in current_kimodo_manager.keyframe_storage_root.iterdir() if current_path.is_dir()]
                self.assertEqual(current_saved_identifiers,[current_process_value.stdout.strip()])
                with np.load(current_kimodo_manager.keyframe_storage_root/current_saved_identifiers[0]/'motion.npz',allow_pickle=False) as current_saved_arrays:self.assertEqual(current_saved_arrays['root_positions'][0,0],7)
            finally:
                current_server_value.shutdown();current_server_value.server_close();current_thread_value.join(timeout=5)

    def test_chat_snapshot_drift_is_rejected_before_gpu_worker(self):
        import hashlib
        import json
        import os
        import threading
        from contextlib import nullcontext
        from http.server import ThreadingHTTPServer
        import numpy as np
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        from workflow.domains.kimodo import keyframe_storage
        from workflow.gateway_server import create_gateway_request_handler
        from gui.ui.gradio import hermes_agent_app
        current_session_identifier='a'*32
        current_source_identifier='2026-11-18_00-00-00-12345678'
        current_attempt_identifier='b'*32
        current_receipt_identifier='keyframe_'+'c'*64
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_kimodo_manager=KimodoGenerationManager()
            current_kimodo_manager.job_storage_root=current_root_path/'jobs'
            current_kimodo_manager.keyframe_storage_root=current_root_path/'keyframes'
            current_job_path=current_kimodo_manager.job_storage_root/current_source_identifier
            current_attempt_path=current_job_path/'attempts'/current_attempt_identifier
            current_attempt_path.mkdir(parents=True)
            current_image_bytes=b'\x89PNG\r\n\x1a\nfixture'
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_attempt_path/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'fps':30,'frames':1,'frame_sha256':[hashlib.sha256(current_image_bytes).hexdigest()]}))
            (current_attempt_path/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':list(range(77)),'parents':list(range(77))}))
            (current_attempt_path/'output-000.png').write_bytes(current_image_bytes)
            current_arrays_value={current_name:np.zeros((1,*current_shape),dtype=np.float32) for current_name,current_shape in keyframe_storage.KIMODO_FRAME_ARRAY_SHAPES.items()}
            np.savez_compressed(current_attempt_path/'motion.npz',**current_arrays_value)
            current_saved_record=keyframe_storage.save_kimodo_keyframe_record(current_source_identifier,current_attempt_identifier,1,'검토',current_job_storage=current_kimodo_manager.job_storage_root,current_keyframe_storage=current_kimodo_manager.keyframe_storage_root)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_store_value.delegation_storage_root.mkdir()
            (current_store_value.delegation_storage_root/(current_receipt_identifier+'.json')).write_text(json.dumps({'version':14,'id':current_receipt_identifier,'request_sha256':'d'*64,'state':'completed','keyframe_id':current_saved_record['id']}))
            current_attachment_value={'session_id':current_session_identifier,'receipt_id':current_receipt_identifier,'keyframe_id':current_saved_record['id'],'output_frame':1}
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'kimodo':current_kimodo_manager.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_arguments:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_url='http://127.0.0.1:'+str(current_server_value.server_port)
            current_original_snapshot=keyframe_storage.snapshot_kimodo_keyframes
            def change_source_before_snapshot(*current_positional_values,**current_keyword_values):
                current_keyframe_root=current_kimodo_manager.keyframe_storage_root/current_saved_record['id']
                current_motion_path=current_keyframe_root/'motion.npz'
                with np.load(current_motion_path,allow_pickle=False) as current_archive_value:
                    current_saved_arrays={current_name:current_archive_value[current_name].copy() for current_name in current_archive_value.files}
                current_saved_arrays['root_positions'][0,0]=9
                np.savez_compressed(current_motion_path,**current_saved_arrays)
                current_record_path=current_keyframe_root/'record.json'
                current_record_value=json.loads(current_record_path.read_text())
                current_record_value['files']['motion.npz']=hashlib.sha256(current_motion_path.read_bytes()).hexdigest()
                current_record_path.write_text(json.dumps(current_record_value))
                return current_original_snapshot(*current_positional_values,**current_keyword_values)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_url}), patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value), patch('workflow.domains.hermes_agent.kimodo_keyframe_operations.HermesDelegationStore',return_value=current_store_value), patch.object(hermes_agent_app,'find_conversation_session_job'), patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value={'prompt':'walk','frames':90,'steps':100,'seed':42}), patch.object(current_kimodo_manager,'validate_generation_runtime'), patch.object(current_kimodo_manager,'hold_generation_submission_guard',side_effect=lambda:nullcontext()), patch.object(current_kimodo_manager,'ensure_generation_request_available'), patch.object(current_kimodo_manager,'launch_generation_worker') as current_worker_mock:
                    current_card_value,_,_=hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_identifier,current_attachment_value)
                    self.assertTrue(current_card_value['ready'])
                    with patch.object(keyframe_storage,'snapshot_kimodo_keyframes',side_effect=change_source_before_snapshot):
                        current_result_value,current_notice_value=hermes_agent_app.submit_conversation_kimodo_review(current_card_value,current_session_identifier,current_source_identifier)
                    self.assertFalse(current_result_value['ready'])
                    self.assertIn('접수 결과 확인 불가',current_notice_value)
                    current_worker_mock.assert_not_called()
                    self.assertEqual(current_store_value.read_delegation_status(current_card_value['review']['request_id'])['state'],'unknown')
                    from types import SimpleNamespace
                    current_worker_mock.return_value=SimpleNamespace(wait=lambda:0)
                    current_next_attachment={**current_attachment_value,'output_frame':2}
                    current_next_card,_,_=hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_identifier,current_next_attachment)
                    self.assertTrue(current_next_card['ready'])
                    current_submit_result=hermes_agent_app.execute_remote_management_command('hermes-agent','hermes-delegate-kimodo',current_next_card['review'])
                    self.assertEqual(current_submit_result['state'],'accepted')
                    current_worker_mock.assert_called_once()
                    current_saved_request=json.loads((current_kimodo_manager.job_storage_root/current_submit_result['job_id']/'request.json').read_text())
                    self.assertEqual(current_saved_request['keyframe_source_hashes'],current_next_card['review']['request']['keyframe_source_hashes'])
                    keyframe_storage.validate_kimodo_job_keyframe_snapshots(current_kimodo_manager.job_storage_root/current_submit_result['job_id'],current_saved_request)
                    import time
                    current_wait_deadline=time.monotonic()+3
                    while time.monotonic()<current_wait_deadline:
                        if json.loads((current_kimodo_manager.job_storage_root/current_submit_result['job_id']/'status.json').read_text()).get('status')=='failed':break
                        time.sleep(.02)
            finally:
                current_server_value.shutdown();current_server_value.server_close();current_thread_value.join(timeout=5)
