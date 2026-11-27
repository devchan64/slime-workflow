"""격리 HTTP 게이트웨이 재시작 뒤 Hermes 기록과 중복 방지 확인."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

from workflow.common.management_gateway import ManagementCommandGateway
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.gateway_server import create_gateway_request_handler


class HermesGatewayRestartTests(unittest.TestCase):
    def test_legacy_anchor_summary_reaches_mcp_via_http(self):
        import os
        from workflow.domains.character_animation import anchor_history
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            current_history_root=current_root_path/'history'
            current_identifier_value='2026-11-20_10-00-00-12345678'
            current_job_path=current_history_root/current_identifier_value[:19]/current_identifier_value
            current_job_path.mkdir(parents=True)
            (current_job_path/'result.json').write_text(json.dumps({'id':current_identifier_value,'created_at':'2026-11-20T10:00:00+09:00','status':'completed','source':{'animationId':'walk','animationVersion':'v1','sheets':[{'image':'/private/image.png'}]},'frames':4}))
            current_manager_value=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_log_values:None
            current_server_thread=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_server_thread.start()
            try:
                current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',current_history_root):
                    current_result_value=hermes_module_value.list_hermes_legacy_anchor_history('walk','v1')
                self.assertEqual(current_result_value['records'][0]['id'],current_identifier_value)
                self.assertNotIn('/private/',str(current_result_value))
                self.assertTrue((current_job_path/'result.json').is_file())
            finally:
                current_server_value.shutdown()
                current_server_thread.join(timeout=5)
                current_server_value.server_close()

    def test_custom_writer_queue_reaches_hermes_mcp_via_http(self):
        import os
        import yaml
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent import management_observer
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            current_workflow_root=current_root_path/'workflow'
            current_queue_path=current_workflow_root/'.tmp'/'gpu-queue'
            current_queue_path.mkdir(parents=True)
            current_state_path=current_root_path/'writer-state'
            current_job_path=current_state_path/'jobs'/'20261121-120000-12345678'
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'writer-agent'}))
            current_ticket_path=current_queue_path/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_path)}))
            current_config_path=current_root_path/'writer-custom.yaml'
            current_config_path.write_text(yaml.safe_dump({'schema_version':1,'document_root':str(current_root_path/'docs'),'state_root':str(current_state_path),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None}))
            current_manager_value=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_log_values:None
            current_server_thread=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_server_thread.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':str(current_config_path),'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_path),patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_gpu_reservation_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
                    current_snapshot_value=hermes_module_value.read_hermes_management_status()
                    current_other_path=current_root_path/'other'/'jobs'/current_job_path.name
                    current_other_path.mkdir(parents=True)
                    (current_other_path/'status.json').write_text(json.dumps({'status':'queued'}))
                    (current_other_path/'gpu-command.json').write_text(json.dumps({'service':'writer-agent'}))
                    current_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(current_other_path)}))
                    current_invalid_snapshot=hermes_module_value.read_hermes_management_status()
                self.assertEqual(current_invalid_snapshot['queue']['status'],'unavailable')
                self.assertEqual(current_invalid_snapshot['queue']['jobs'],[])
                self.assertNotIn(str(current_other_path),str(current_invalid_snapshot))
                self.assertEqual(current_snapshot_value['queue']['status'],'available')
                self.assertEqual(current_snapshot_value['queue']['jobs'][0]['id'],current_job_path.name)
                self.assertTrue(current_ticket_path.is_file())
                self.assertFalse((current_root_path/'docs').exists())
            finally:
                current_server_value.shutdown()
                current_server_thread.join(timeout=5)
                current_server_value.server_close()

    def test_music_resume_preview_and_stale_rejection_over_isolated_gateway(self):
        from workflow.domains.music.generation import MusicGenerationManager
        from workflow.common.management_gateway import execute_management_command
        from workflow.common.generation_records import write_record_atomically
        from generators.music.contracts import build_music_request
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=MusicGenerationManager('music-heartmula')
            current_manager_value.job_storage_root=current_root_path/'jobs'
            current_manager_value.history_storage_root=current_root_path/'history'
            current_manager_value.history_storage_root.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=current_manager_value.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            write_record_atomically(current_job_path/'request.json',build_music_request('music-heartmula',{'prompt':'piano','lyrics':'','seed':1}))
            write_record_atomically(current_job_path/'status.json',{'status':'failed'})
            write_record_atomically(current_job_path/'gpu-command.json',{'service':'music-heartmula','command':current_manager_value.build_music_worker_command(current_job_path)})
            current_gateway_value=ManagementCommandGateway({'music-heartmula':current_manager_value.handle_music_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_preview_value=execute_management_command('music-heartmula','resume-preview',{'id':current_job_identifier},current_gateway_origin)
                    self.assertEqual((current_preview_value['id'],current_preview_value['status']),(current_job_identifier,'failed'))
                    write_record_atomically(current_job_path/'status.json',{'status':'cancelled'})
                    with self.assertRaises((ValueError,HTTPError)):
                        execute_management_command('music-heartmula','resume',{'id':current_job_identifier,'expected_resume_fingerprint':current_preview_value['expected_resume_fingerprint']},current_gateway_origin)
                    current_launch_mock.assert_not_called()
                    current_new_preview=execute_management_command('music-heartmula','resume-preview',{'id':current_job_identifier},current_gateway_origin)
                    current_result_value=execute_management_command('music-heartmula','resume',{'id':current_job_identifier,'expected_resume_fingerprint':current_new_preview['expected_resume_fingerprint']},current_gateway_origin)
                    self.assertEqual(current_result_value,{'id':current_job_identifier,'status':'queued'})
                    current_launch_mock.assert_called_once()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_audio_resume_mcp_through_isolated_gateway(self):
        import os
        from workflow.domains.music.generation import MusicGenerationManager
        from workflow.common.generation_records import write_record_atomically
        from generators.music.contracts import build_music_request
        from workflow.domains.hermes_agent import audio_resume_operations
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_music_manager=MusicGenerationManager('music-heartmula')
            current_music_manager.job_storage_root=current_root_path/'music-jobs'
            current_music_manager.history_storage_root=current_root_path/'history'
            current_music_manager.history_storage_root.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=current_music_manager.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            write_record_atomically(current_job_path/'request.json',build_music_request('music-heartmula',{'prompt':'piano','lyrics':'','seed':1}))
            write_record_atomically(current_job_path/'status.json',{'status':'failed'})
            write_record_atomically(current_job_path/'gpu-command.json',{'service':'music-heartmula','command':current_music_manager.build_music_worker_command(current_job_path)})
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'music-heartmula':current_music_manager.handle_music_request,'hermes-agent':current_hermes_manager.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',current_root_path/'receipts'),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_preview_value=hermes_module_value.preview_hermes_audio_resume('music-heartmula',current_job_identifier)
                    current_fingerprint_value=current_preview_value['expected_resume_fingerprint']
                    current_first_value=hermes_module_value.submit_hermes_audio_resume('audio_resume_123','music-heartmula',current_job_identifier,current_fingerprint_value)
                    self.assertEqual(current_first_value['state'],'accepted')
                    current_repeat_value=hermes_module_value.submit_hermes_audio_resume('audio_resume_123','music-heartmula',current_job_identifier,current_fingerprint_value)
                    self.assertTrue(current_repeat_value['duplicate'])
                    self.assertEqual(hermes_module_value.read_hermes_audio_resume_receipt('audio_resume_123')['job_id'],current_job_identifier)
                    current_launch_mock.assert_called_once()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_translation_resume_mcp_through_isolated_gateway(self):
        import os
        from workflow.domains.translation import service as translation_service
        from workflow.common.generation_records import write_record_atomically
        from workflow.domains.hermes_agent import translation_resume_operations
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_translation_manager=translation_service.TranslationServiceManager()
            current_translation_manager.job_storage_root=current_root_path/'translation-jobs'
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_path=current_translation_manager.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_request_value=translation_service.validate_translation_submission({'text':'나무','target_language':'en'})
            write_record_atomically(current_job_path/'request.json',{**current_request_value,'model_id':'google/translategemma-4b-it'})
            write_record_atomically(current_job_path/'status.json',{'status':'failed'})
            write_record_atomically(current_job_path/'gpu-command.json',{'service':'prompt-translation','command':translation_service.build_translation_worker_command(current_job_path)})
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'prompt-translation':current_translation_manager.handle_translation_request,'hermes-agent':current_hermes_manager.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(translation_resume_operations,'TRANSLATION_RESUME_RECEIPT_ROOT',current_root_path/'receipts'),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                    current_preview_value=hermes_module_value.preview_hermes_translation_resume(current_job_identifier)
                    current_fingerprint_value=current_preview_value['expected_resume_fingerprint']
                    current_first_value=hermes_module_value.submit_hermes_translation_resume('translation_resume_123',current_job_identifier,current_fingerprint_value)
                    self.assertEqual(current_first_value['state'],'accepted')
                    current_repeat_value=hermes_module_value.submit_hermes_translation_resume('translation_resume_123',current_job_identifier,current_fingerprint_value)
                    self.assertTrue(current_repeat_value['duplicate'])
                    self.assertEqual(hermes_module_value.read_hermes_translation_resume_receipt('translation_resume_123')['job_id'],current_job_identifier)
                    current_launch_mock.assert_called_once()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_capture_status_mcp_uses_isolated_http_gateway(self):
        import os
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value),patch('workflow.domains.hermes_agent.service.WORKFLOW_ROOT_DIRECTORY',current_root_path):
                    current_result_value=hermes_module_value.read_hermes_capture_status('request_123','map-review')
                    self.assertEqual(current_result_value['receipt'],{'state':'not_found','request_id':'request_123','service':'map-review'})
                    self.assertIsNone(current_result_value['job'])
                    from workflow.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once, normalize_capture_delegation_request
                    current_job_identifier='2026-11-19_12-00-00-12345678'
                    current_job_path=current_root_path/'.tmp'/'test'/'review-capture'/current_job_identifier
                    current_job_path.mkdir(parents=True)
                    current_settings_value=normalize_capture_delegation_request('map-review',{'map':'ash-edge'})
                    prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},lambda current_request_value:{'id':current_job_identifier})
                    (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':current_settings_value}))
                    (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'review-capture','command':['python','-m','workflow.domains.hermes_agent.capture_worker','--job-dir',str(current_job_path)]}))
                    (current_job_path/'status.json').write_text('{"status":"queued"}')
                    current_queued_value=hermes_module_value.read_hermes_capture_status('request_123','map-review')
                    self.assertEqual(current_queued_value['receipt']['job_id'],current_job_identifier)
                    self.assertEqual(current_queued_value['job'],{'status':'queued','result_available':False})
                    with self.assertRaises(ValueError):hermes_module_value.read_hermes_capture_status('request_123','character-review')
                    with self.assertRaises(ValueError):hermes_module_value.read_hermes_capture_status('request_123','unsupported')
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_model_receipt_mcp_through_isolated_gateway(self):
        import os
        from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        from workflow.tests.test_hermes_mcp import hermes_module_value
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesModelPreparationStore(current_root_path/'receipts')
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            from workflow.common.management_gateway import execute_management_command as current_gateway_dispatch
            from unittest.mock import Mock
            current_prepare_mock=Mock(return_value={'preparation_status':'running'})
            def dispatch_isolated_model_command(*current_arguments,**current_keywords):
                if current_keywords.get('gateway_request_handler') is not None:
                    return current_gateway_dispatch(*current_arguments,**current_keywords)
                return current_prepare_mock(*current_arguments,**current_keywords)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch('workflow.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore',return_value=current_store_value),patch('workflow.common.management_gateway.execute_management_command',side_effect=dispatch_isolated_model_command):
                    current_missing_value=hermes_module_value.read_hermes_model_preparation_receipt('model_request_123','flux-image')
                    self.assertEqual((current_missing_value['state'],current_missing_value['request_id'],current_missing_value['service']),('not_found','model_request_123','flux-image'))
                    current_first_value=hermes_module_value.prepare_hermes_managed_model('model_request_123','flux-image')
                    current_repeat_value=hermes_module_value.prepare_hermes_managed_model('model_request_123','flux-image')
                    current_receipt_value=hermes_module_value.read_hermes_model_preparation_receipt('model_request_123','flux-image')
                    self.assertEqual((current_first_value['state'],current_receipt_value['request_id'],current_receipt_value['service']),('accepted','model_request_123','flux-image'))
                    self.assertTrue(current_repeat_value['duplicate'])
                    current_prepare_mock.assert_called_once()
                    current_prepare_mock.side_effect=OSError('simulated loss')
                    with self.assertRaises(ValueError):hermes_module_value.prepare_hermes_managed_model('model_request_lost','flux-image')
                    current_unknown_value=hermes_module_value.read_hermes_model_preparation_receipt('model_request_lost','flux-image')
                    self.assertEqual((current_unknown_value['state'],current_unknown_value['request_id'],current_unknown_value['service']),('unknown','model_request_lost','flux-image'))
                    self.assertTrue(hermes_module_value.prepare_hermes_managed_model('model_request_lost','flux-image')['duplicate'])
                    self.assertEqual(current_prepare_mock.call_count,2)
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_city_and_building_proposals_through_isolated_http_gateway(self):
        from workflow.common.management_gateway import execute_management_command
        current_proposals={
            'city':{'map':'stonewarm','generation':5,'revision':2,'changes':[{'path':['data','name'],'before':'기존','after':'변경'}]},
            'building':{'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}},
        }
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root=Path(current_temp_name)
            current_job='2026-11-18_00-00-00-12345678'
            current_job_path=current_root/'jobs'/current_job
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            current_manager=HermesServiceManager(current_root/'jobs',current_root/'sessions')
            current_gateway=ManagementCommandGateway({'hermes-agent':current_manager.handle_hermes_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            current_origin='http://127.0.0.1:'+str(current_server.server_port)
            try:
                for current_kind,current_proposal in current_proposals.items():
                    with self.subTest(kind=current_kind):
                        current_answer='HERMES_'+current_kind.upper()+'_PROPOSAL\n'+json.dumps(current_proposal,ensure_ascii=False)+'\nEND_HERMES_'+current_kind.upper()+'_PROPOSAL'
                        (current_job_path/'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':current_answer}))
                        current_result=execute_management_command('hermes-agent','hermes-'+current_kind+'-proposal',{'id':current_job},current_origin)
                        self.assertEqual(current_result,{'job_id':current_job,'proposal':current_proposal})
                        (current_job_path/'status.json').write_text('{"status":"running"}')
                        with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-'+current_kind+'-proposal',{'id':current_job},current_origin)
                        (current_job_path/'status.json').write_text('{"status":"completed"}')
            finally:
                current_server.shutdown()
                current_thread.join(timeout=5)
                current_server.server_close()

    def test_coding_cancel_identity_through_isolated_gateway(self):
        from workflow.common.management_gateway import execute_management_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_job_path=current_manager_value.hermes_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                with patch('workflow.domains.hermes_agent.service.cancel_gpu_generation',return_value={'status':'queued','cancel_requested':True}) as current_cancel_mock:
                    current_response_record=execute_management_command('hermes-agent','hermes-cancel',{'id':current_job_identifier},'http://127.0.0.1:'+str(current_server_value.server_port))
                    self.assertEqual(current_response_record,{'id':current_job_identifier,'status':'queued','cancel_requested':True})
                    current_cancel_mock.assert_called_once_with(current_job_path)
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_writer_search_paths_through_isolated_gateway(self):
        import os
        from generators.writer_agent.management import WriterAgentManager
        from workflow.common.management_gateway import execute_management_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_document_root=current_root_path/'documents'
            (current_document_root/'world').mkdir(parents=True)
            (current_document_root/'world'/'town.md').write_text('fixture private body')
            (current_document_root/'escape').symlink_to('/tmp')
            current_job_identifier='20261118-120000-12345678'
            current_writer_manager=WriterAgentManager(current_root_path/'unused.yaml')
            current_hermes_manager=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_detail_record={'id':current_job_identifier,'status':{'stage':'review'},'search':{'prompt':'fixture private prompt','results':[{'path':'world/town.md','text':'fixture private body'},{'path':'/private/secret'},{'path':'escape/nope'}]}}
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_manager.handle_hermes_request,'writer-agent':current_writer_manager.handle_writer_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_writer_manager,'read_writer_detail',return_value=current_detail_record),patch('generators.writer_agent.management.load_workspace_config',return_value={'document_root':str(current_document_root),'state_root':str(current_root_path/'state'),'excluded_roots':[]}),patch('workflow.domains.hermes_agent.writer_operations.HermesDelegationStore') as current_store_mock:
                    current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
                    current_result_value=execute_management_command('hermes-agent','hermes-writer-search-paths',{'request_id':'fixture_request'},current_gateway_origin)
                    self.assertEqual(current_result_value,{'paths':['world/town.md'],'truncated':True})
                    self.assertNotIn('fixture private',str(current_result_value))
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_writer_source_history_through_isolated_http_gateway(self):
        import os
        from generators.writer_agent.documents import save_yaml_document
        from generators.writer_agent.management import WriterAgentManager
        from workflow.common.management_gateway import execute_management_command
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_documents_root=current_root_path/'docs'
            (current_documents_root/'ideas').mkdir(parents=True)
            current_workspace_path=current_root_path/'workspace.yaml'
            save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_root_path/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            current_job_identifier='20261118-120000-12345678'
            current_job_directory=current_root_path/'state'/'jobs'/current_job_identifier
            current_job_directory.mkdir(parents=True)
            save_yaml_document(current_job_directory/'status.yaml',{'id':current_job_identifier,'stage':'review','summary':'secret'})
            save_yaml_document(current_job_directory/'request.yaml',{'prompt':'private'})
            current_writer_value=WriterAgentManager(current_workspace_path)
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'writer-agent':current_writer_value.handle_writer_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_writer_value,'search_writer_history') as current_history_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'writer-agent'},current_gateway_origin)
                    current_search_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'writer-agent','query':'12345678'},current_gateway_origin)
                    self.assertEqual(current_search_value['records'][0]['id'],current_job_identifier)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'writer-agent','query':'not-found'},current_gateway_origin)['total'],0)
                    with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'writer-agent','query':'not-found','snapshot':current_search_value['snapshot']},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'review','status_source':'job'}])
                    self.assertNotIn('secret',str(current_result_value))
                    self.assertNotIn('private',str(current_result_value))
                    current_history_mock.assert_not_called()
                    (current_job_directory/'status.yaml').write_text('invalid: [')
                    with patch.object(current_writer_value,'read_workspace_state',side_effect=AssertionError('전체 상태 조회 금지')):
                        current_damaged_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'writer-agent'},current_gateway_origin)
                    self.assertEqual(current_damaged_value['records'],[{'id':current_job_identifier,'recorded_status':'unknown','status_source':'unavailable'}])
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_writer_cancellation_through_isolated_http_gateway(self):
        import os
        from generators.writer_agent.documents import save_yaml_document
        from generators.writer_agent.jobs import read_process_identity
        from generators.writer_agent.management import WriterAgentManager
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.hermes_agent import writer_operations
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_documents_root=current_root_path/'docs'
            (current_documents_root/'ideas').mkdir(parents=True)
            current_workspace_path=current_root_path/'workspace.yaml'
            save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_root_path/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            current_job_identifier='20261118-120000-12345678'
            current_job_directory=current_root_path/'state/jobs'/current_job_identifier
            current_job_directory.mkdir(parents=True)
            save_yaml_document(current_job_directory/'status.yaml',{'id':current_job_identifier,'stage':'reasoning'})
            save_yaml_document(current_job_directory/'request.yaml',{'mode':'write','prompt':'private'})
            (current_job_directory/'status.json').write_text(json.dumps({'status':'running'}))
            (current_job_directory/'queue-process.json').write_text(json.dumps({'pid':os.getpid(),'identity':read_process_identity(os.getpid())}))
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{},lambda current_payload_value:{'id':current_job_identifier},lambda current_payload_value:None)
            current_writer_value=WriterAgentManager(current_workspace_path)
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'writer-agent':current_writer_value.handle_writer_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value):
                    current_cancel_value=execute_management_command('hermes-agent','hermes-writer-cancel',{'request_id':'writer_request_123','job_id':current_job_identifier},current_gateway_origin)
                    self.assertTrue(current_cancel_value['cancel_requested'])
                    self.assertTrue((current_job_directory/'cancel.request').exists())
                    (current_job_directory/'status.json').write_text(json.dumps({'status':'cancelled'}))
                    current_status_value=execute_management_command('hermes-agent','hermes-writer-status',{'request_id':'writer_request_123'},current_gateway_origin)
                    self.assertEqual(current_status_value['job']['stage'],'interrupted')
                    self.assertNotIn('private',str(current_status_value))
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_translation_source_history_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.translation.service import TranslationServiceManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_translation_value=TranslationServiceManager()
            current_translation_value.job_storage_root=current_root_path/'translation'
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_translation_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text(json.dumps({'text':'secret'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_directory/'result.json').write_text(json.dumps({'text':'secret result'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'prompt-translation':current_translation_value.handle_translation_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_translation_value,'read_translation_job') as current_detail_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'prompt-translation'},current_gateway_origin)
                    current_search_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'prompt-translation','query':'12345678'},current_gateway_origin)
                    self.assertEqual(current_search_value['records'][0]['id'],current_job_identifier)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'prompt-translation','query':'not-found'},current_gateway_origin)['total'],0)
                    with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'prompt-translation','query':'not-found','snapshot':current_search_value['snapshot']},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'completed','status_source':'job'}])
                    self.assertNotIn('secret',str(current_result_value))
                    current_detail_mock.assert_not_called()
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_building_alias_reports_billboard_history_source(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.common.management_runtime import build_building_compatibility_handler
        from workflow.domains.image.billboard_generation import BillboardGuideGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_billboard_value=BillboardGuideGenerationManager()
            current_billboard_value.job_storage_root=current_root_path/'billboard'
            current_history_path=current_root_path/'history'
            current_history_path.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_billboard_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text('{}')
            (current_job_directory/'status.json').write_text(json.dumps({'status':'completed'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'building-generator':build_building_compatibility_handler(current_billboard_value),'billboard-generator':current_billboard_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_billboard_value,'history_storage_path',return_value=current_history_path):
                    current_building_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'building-generator'},current_gateway_origin)
                    current_billboard_result=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'billboard-generator'},current_gateway_origin)
                    self.assertEqual(current_building_value['records'],current_billboard_result['records'])
                    self.assertEqual(current_building_value['source_service'],'billboard-generator')
                    self.assertEqual(current_billboard_result['source_service'],'billboard-generator')
                    self.assertIn('호환 경로',current_building_value['note'])
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_archived_qwen_history_does_not_enable_generation(self):
        import os
        from workflow.common.management_gateway import execute_management_command,resolve_management_command
        from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_qwen_value=QwenPlainGenerationManager()
            current_qwen_value.job_storage_root=current_root_path/'qwen'
            current_history_path=current_root_path/'history'
            current_history_path.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_qwen_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text(json.dumps({'prompt':'private'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'completed'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'qwen-21':current_qwen_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_qwen_value,'history_storage_path',return_value=current_history_path):
                    current_result_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'qwen-21'},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'completed','status_source':'job'}])
                    for current_command_name in ('generate','resume','prepare'):
                        with self.assertRaises(ValueError):
                            resolve_management_command('qwen-21',current_command_name,{})
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_flux_source_history_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_flux_value=FluxImageGenerationManager('flux-image')
            current_flux_value.job_storage_root=current_root_path/'flux'
            current_history_path=current_root_path/'history'
            current_history_path.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_flux_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text(json.dumps({'prompt':'secret'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'completed'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'flux-image':current_flux_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_flux_value,'history_storage_path',return_value=current_history_path),patch.object(current_flux_value,'read_generation_status_record') as current_status_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'flux-image','limit':1},current_gateway_origin)
                    current_search_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'flux-image','query':'12345678'},current_gateway_origin)
                    self.assertEqual(current_search_value['records'][0]['id'],current_job_identifier)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'flux-image','query':'not-found'},current_gateway_origin)['total'],0)
                    with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'flux-image','query':'not-found','snapshot':current_search_value['snapshot']},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'completed','status_source':'job'}])
                    self.assertNotIn('secret',str(current_result_value))
                    current_status_mock.assert_not_called()
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_video_source_history_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_video_value=VaceVideoGenerationManager()
            current_video_value.job_storage_root=current_root_path/'video'
            current_history_path=current_root_path/'history'
            current_history_path.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_video_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text(json.dumps({'prompt':'secret'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'running'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'wan22-vace':current_video_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_video_value,'history_storage_path',return_value=current_history_path),patch('workflow.common.reference_video_generation.recover_interrupted_video_job') as current_recovery_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'wan22-vace','limit':1},current_gateway_origin)
                    current_search_value=execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'wan22-vace','query':'12345678'},current_gateway_origin)
                    self.assertEqual(current_search_value['records'][0]['id'],current_job_identifier)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'wan22-vace','query':'not-found'},current_gateway_origin)['total'],0)
                    with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'wan22-vace','query':'not-found','snapshot':current_search_value['snapshot']},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'running','status_source':'job'}])
                    self.assertNotIn('secret',str(current_result_value))
                    current_recovery_mock.assert_not_called()
                    (current_job_directory/'.history-deleted').touch()
                    with self.assertRaises(ValueError):
                        execute_management_command('hermes-agent','hermes-generator-source-history',{'service':'wan22-vace','offset':1,'snapshot':current_result_value['snapshot']},current_gateway_origin)
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_audio_source_history_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.music.generation import MusicGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_music_value=MusicGenerationManager('music-heartmula')
            current_music_value.history_storage_root=current_root_path/'history'
            current_music_value.job_storage_root=current_root_path/'audio'
            current_music_value.history_storage_root.mkdir()
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_music_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'request.json').write_text(json.dumps({'prompt':'secret'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'completed','log':'secret'}))
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'music-heartmula':current_music_value.handle_music_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(current_music_value,'read_music_status') as current_status_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-audio-source-history',{'service':'music-heartmula','limit':1},current_gateway_origin)
                    current_search_value=execute_management_command('hermes-agent','hermes-audio-source-history',{'service':'music-heartmula','query':'12345678'},current_gateway_origin)
                    self.assertEqual(current_search_value['records'][0]['id'],current_job_identifier)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-audio-source-history',{'service':'music-heartmula','query':'not-found'},current_gateway_origin)['total'],0)
                    with self.assertRaises(ValueError):execute_management_command('hermes-agent','hermes-audio-source-history',{'service':'music-heartmula','query':'not-found','snapshot':current_search_value['snapshot']},current_gateway_origin)
                    self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'completed','status_source':'job'}])
                    self.assertNotIn('secret',str(current_result_value))
                    current_status_mock.assert_not_called()
                    (current_job_directory/'.history-deleted').touch()
                    with self.assertRaises(ValueError):
                        execute_management_command('hermes-agent','hermes-audio-source-history',{'service':'music-heartmula','offset':1,'snapshot':current_result_value['snapshot']},current_gateway_origin)
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_kimodo_build_record_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        from workflow.domains.kimodo import migraphx_build
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_job_identifier='2026-11-18_00-00-00-12345678'
            current_job_directory=current_root_path/'builds'/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory.parent/'latest.json').write_text(json.dumps({'job':current_job_identifier}))
            (current_job_directory/'status.json').write_text(json.dumps({'status':'running','private':'secret'}))
            current_kimodo_value=KimodoGenerationManager()
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'kimodo':current_kimodo_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}),patch.object(migraphx_build,'POSE_BUILD_JOB_ROOT',current_job_directory.parent),patch.object(migraphx_build,'check_pose_cache_environment') as current_gpu_mock:
                    current_status_value=execute_management_command('hermes-agent','hermes-kimodo-build-status',{},current_gateway_origin)
                    self.assertEqual(current_status_value['status'],'running')
                    self.assertEqual(current_status_value['job_id'],current_job_identifier)
                    self.assertEqual(current_status_value['cache_status'],'unverified')
                    self.assertNotIn('secret',str(current_status_value))
                    (current_job_directory/'status.json').write_text(json.dumps({'status':'failed','error':'시스템 RAM 보호: /private/secret'}))
                    current_guard_value=execute_management_command('hermes-agent','hermes-kimodo-build-status',{},current_gateway_origin)
                    self.assertEqual(current_guard_value['failure_code'],'host_memory_guard')
                    self.assertIn('메모리 보호',current_guard_value['failure_reason'])
                    self.assertNotIn('private',str(current_guard_value))
                    (current_job_directory/'status.json').unlink()
                    self.assertEqual(execute_management_command('hermes-agent','hermes-kimodo-build-status',{},current_gateway_origin)['status'],'unavailable')
                    (current_job_directory/'status.json').write_text('not json')
                    self.assertEqual(execute_management_command('hermes-agent','hermes-kimodo-build-status',{},current_gateway_origin)['status'],'unavailable')
                    current_gpu_mock.assert_not_called()
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_keyframe_preview_through_isolated_kimodo_gateway(self):
        import os
        import shutil
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        current_keyframe_identifier='a0000000000000000000000000000001'
        current_example_identifier='b0000000000000000000000000000001'
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_keyframe_root=current_root_path/'keyframes'
            current_keyframe_root.mkdir()
            current_source_path=Path(__file__).resolve().parents[2]/'generators/kimodo/keyframe-examples'/current_example_identifier
            shutil.copytree(current_source_path,current_keyframe_root/current_keyframe_identifier)
            current_record_path=current_keyframe_root/current_keyframe_identifier/'record.json'
            current_record_value=json.loads(current_record_path.read_text())
            current_record_value['id']=current_keyframe_identifier
            current_record_path.write_text(json.dumps(current_record_value))
            current_kimodo_value=KimodoGenerationManager()
            current_kimodo_value.keyframe_storage_root=current_keyframe_root
            current_hermes_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_hermes_value.handle_hermes_request,'kimodo':current_kimodo_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin}):
                    current_catalog_value=execute_management_command('hermes-agent','hermes-kimodo-keyframes',{'query':'복싱'},current_gateway_origin)
                    self.assertEqual(current_catalog_value['items'][0]['id'],current_keyframe_identifier)
                    current_preview_value=execute_management_command('hermes-agent','hermes-kimodo-keyframe-preview',{'keyframe_id':current_keyframe_identifier},current_gateway_origin)
                    self.assertEqual(current_preview_value['id'],current_keyframe_identifier)
                    self.assertEqual(len(current_preview_value['sha256']),64)
                    current_batch_request={'frames':30,'keyframes':[{'id':current_keyframe_identifier,'frame':1},{'id':current_keyframe_identifier,'frame':20}]}
                    current_batch_value=execute_management_command('hermes-agent','hermes-kimodo-keyframe-validate',current_batch_request,current_gateway_origin)
                    self.assertEqual(len(current_batch_value['sources']),1)
                    self.assertEqual(current_batch_value['skeleton_signature_sha256'],current_preview_value['skeleton_signature_sha256'])
                    (current_keyframe_root/current_keyframe_identifier/'preview.png').write_bytes(b'changed')
                    with self.assertRaises(ValueError):
                        execute_management_command('hermes-agent','hermes-kimodo-keyframe-preview',{'keyframe_id':current_keyframe_identifier},current_gateway_origin)
                    with self.assertRaises(ValueError):
                        execute_management_command('hermes-agent','hermes-kimodo-keyframe-validate',current_batch_request,current_gateway_origin)
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_effect_registration_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.hermes_agent import effect_operations
        from workflow.domains.map_assets.resize import handle_map_resize_request
        current_effect_value={'id':'waypoint-test-v1','name':'신규','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
        current_register_calls=[]
        def execute_test_content_api(current_method_value,current_route_value,current_payload_value=None):
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/status':
                return {'capabilities':{'waypointEffectWrites':True}}
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/effects':
                return {'effects':current_register_calls[:]}
            if current_method_value=='POST' and current_route_value=='/internal/v1/content/effects':
                current_register_calls.append(current_payload_value)
                return {'created':True,'id':current_payload_value['id'],'generation':2,'snapshot':'pending'}
            raise AssertionError((current_method_value,current_route_value))
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request,'map-assets':handle_map_resize_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_CONTENT_STORAGE':'database'}),patch('workflow.domains.map_assets.effect_editor.execute_content_api_request',side_effect=execute_test_content_api),patch.object(effect_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_preview_value=execute_management_command('hermes-agent','hermes-effect-register-preview',{'draft':current_effect_value},current_gateway_origin)
                    current_request_value={'request_id':'effect_http_123','draft':current_effect_value,'review_sha256':current_preview_value['review_sha256']}
                    self.assertEqual(execute_management_command('hermes-agent','hermes-effect-register',current_request_value,current_gateway_origin)['state'],'completed')
                    self.assertTrue(execute_management_command('hermes-agent','hermes-effect-register',current_request_value,current_gateway_origin)['duplicate'])
                    current_receipt_value=execute_management_command('hermes-agent','hermes-effect-register-receipt',{'request_id':'effect_http_123'},current_gateway_origin)
                    self.assertEqual((current_receipt_value['id'],current_receipt_value['generation']),('waypoint-test-v1',2))
                    self.assertEqual(current_register_calls,[current_effect_value])
                    with self.assertRaisesRegex(ValueError,'이미 있습니다'):
                        execute_management_command('hermes-agent','hermes-effect-register-preview',{'draft':current_effect_value},current_gateway_origin)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-effect-register-receipt',{'request_id':'effect_http_456'},current_gateway_origin)['state'],'not_found')
                    self.assertEqual(len(current_register_calls),1)
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_billboard_effect_reviewed_registration_over_http(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.hermes_agent import effect_operations
        from workflow.domains.map_assets import resize
        current_effect_value={'id':'glow-test-v1','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'test-glow','texture':'mushroom-variant-2-v1','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        current_revision_value=[1]
        current_register_calls=[]
        def read_test_catalog(current_payload_value):
            return {'storage':'database','assets':[{'texture':'mushroom-variant-2-v1','databaseRevision':current_revision_value[0]}]}
        def execute_test_content_api(current_method_value,current_route_value,current_payload_value=None):
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/status':
                return {'capabilities':{'reviewedBillboardEffectRegistration':True}}
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/effects':
                return {'effects':[]}
            if current_method_value=='POST' and current_route_value=='/internal/v1/content/effects/reviewed':
                self.assertEqual(current_payload_value['expectedBillboardRevision'],1)
                current_register_calls.append(current_payload_value['effect'])
                return {'created':True,'id':current_payload_value['effect']['id'],'generation':2,'snapshot':'pending'}
            raise AssertionError((current_method_value,current_route_value))
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request,'map-assets':resize.handle_map_resize_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_CONTENT_STORAGE':'database'}),patch.object(resize,'RESIZE_STORAGE_DIRECTORY',current_root_path/'locks'),patch('workflow.domains.map_assets.database_editor.load_database_editor_catalog',side_effect=read_test_catalog),patch('workflow.domains.map_assets.effect_editor.execute_content_api_request',side_effect=execute_test_content_api),patch.object(effect_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_preview_value=execute_management_command('hermes-agent','hermes-effect-register-preview',{'draft':current_effect_value},current_gateway_origin)
                    current_request_value={'request_id':'glow_http_123','draft':current_effect_value,'review_sha256':current_preview_value['review_sha256']}
                    current_response_value=execute_management_command('hermes-agent','hermes-effect-register',current_request_value,current_gateway_origin)
                    self.assertEqual(current_response_value['state'],'completed')
                    self.assertTrue(execute_management_command('hermes-agent','hermes-effect-register',current_request_value,current_gateway_origin)['duplicate'])
                    self.assertEqual(current_register_calls,[current_effect_value])
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_old_asset_server_rejected_before_effect_receipt(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.hermes_agent import effect_operations
        from workflow.domains.map_assets import resize
        current_effect_value={'id':'old-server-glow','name':'발광','image':'assets/sprites/effects/terrain/glow-mushroom-single-sheet-v1.png','renderer':'billboard-glow','columns':4,'rows':2,'frames':8,'alignment':{'key':'old-server-glow','texture':'mushroom-variant-2-v1','target':[0,0,1,1],'alpha':0.5,'frames':[[0,0,1,1]]*8}}
        def read_test_catalog(current_payload_value):
            return {'storage':'database','assets':[{'texture':'mushroom-variant-2-v1','databaseRevision':1}]}
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request,'map-assets':resize.handle_map_resize_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_CONTENT_STORAGE':'database'}),patch.object(resize,'RESIZE_STORAGE_DIRECTORY',current_root_path/'locks'),patch('workflow.domains.map_assets.database_editor.load_database_editor_catalog',side_effect=read_test_catalog),patch('workflow.domains.map_assets.effect_editor.execute_content_api_request',return_value={'generation':1}) as current_api_mock,patch.object(effect_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    with self.assertRaisesRegex(ValueError,'지원하지 않습니다'):
                        execute_management_command('hermes-agent','hermes-effect-register',{'request_id':'old_server_123','draft':current_effect_value,'review_sha256':'a'*64},current_gateway_origin)
                    self.assertEqual(execute_management_command('hermes-agent','hermes-effect-register-receipt',{'request_id':'old_server_123'},current_gateway_origin)['state'],'not_found')
                    current_api_mock.assert_called_once_with('GET','/internal/v1/content/status')

            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_waypoint_replacement_through_isolated_http_gateway(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.hermes_agent import effect_operations
        from workflow.domains.map_assets.resize import handle_map_resize_request
        current_old_value={'id':'waypoint-guide-v3','name':'기존','image':'assets/sprites/effects/waypoint/waypoint-guide-v4.png','animation':'assets/sprites/effects/waypoint/waypoint-guide-v4.animation.json','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}
        current_new_value={**current_old_value,'id':'waypoint-guide-v4','name':'신규'}
        current_effect_values=[current_old_value]
        current_replace_calls=[]
        def execute_test_content_api(current_method_value,current_route_value,current_payload_value=None):
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/status':
                return {'capabilities':{'waypointEffectWrites':True}}
            if current_method_value=='GET' and current_route_value=='/internal/v1/content/effects':
                return {'effects':current_effect_values[:]}
            if current_method_value=='POST' and current_route_value=='/internal/v1/content/effects/waypoint-guide-v3/replace':
                current_replace_calls.append(current_payload_value)
                current_effect_values[:]=[current_payload_value['effect']]
                return {'saved':True,'id':'waypoint-guide-v4','replaced':'waypoint-guide-v3','generation':2,'snapshot':'pending'}
            raise AssertionError((current_method_value,current_route_value))
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request,'map-assets':handle_map_resize_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_origin,'SLIME_CONTENT_STORAGE':'database'}),patch('workflow.domains.map_assets.effect_editor.execute_content_api_request',side_effect=execute_test_content_api),patch.object(effect_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_detail_value=execute_management_command('hermes-agent','hermes-effect-detail',{'id':'waypoint-guide-v3'},current_gateway_origin)
                    current_draft_value={'id':'waypoint-guide-v3','revision':current_detail_value['revision'],'effect':current_new_value}
                    current_review_value=execute_management_command('hermes-agent','hermes-waypoint-preview',{'draft':current_draft_value},current_gateway_origin)
                    current_request_value={'request_id':'waypoint_http_123','draft':current_draft_value,'review_sha256':current_review_value['review_sha256']}
                    self.assertEqual(execute_management_command('hermes-agent','hermes-waypoint-replace',current_request_value,current_gateway_origin)['state'],'completed')
                    self.assertTrue(execute_management_command('hermes-agent','hermes-waypoint-replace',current_request_value,current_gateway_origin)['duplicate'])
                    self.assertEqual(execute_management_command('hermes-agent','hermes-waypoint-receipt',{'request_id':'waypoint_http_123'},current_gateway_origin)['id'],'waypoint-guide-v4')
                    self.assertEqual(len(current_replace_calls),1)
            finally:
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()

    def test_kimodo_recorded_status_through_isolated_http_gateway(self):
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        from workflow.domains.hermes_agent.management_observer import read_hermes_generator_snapshot
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_manager_value=KimodoGenerationManager()
            current_manager_value.job_storage_root=Path(current_temp_root)/'jobs'
            current_job_path=current_manager_value.job_storage_root/'2026-11-17_10-00-00-12345678'
            current_job_path.mkdir(parents=True)
            current_status_path=current_job_path/'status.json'
            current_status_bytes=b'{"status":"running"}\n'
            current_status_path.write_bytes(current_status_bytes)
            current_gateway_value=ManagementCommandGateway({'kimodo':current_manager_value.handle_image_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                current_server_address=f'http://127.0.0.1:{current_server_value.server_port}'
                current_result_value=execute_management_command('kimodo','active-observe',{},current_server_address)
                self.assertEqual(current_result_value['id'],current_job_path.name)
                self.assertEqual(current_result_value['count'],1)
                self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
                self.assertFalse((current_job_path/'resume.lock').exists())
                with self.assertRaises(ValueError):execute_management_command('kimodo','active-observe',{'extra':True},current_server_address)
                with patch('workflow.domains.hermes_agent.management_observer.inspect_hermes_model_status',return_value={}):
                    with patch.dict('os.environ',{'SLIME_MANAGEMENT_GATEWAY_URL':current_server_address}):
                        current_observation_value=read_hermes_generator_snapshot()['kimodo']['active']
                self.assertEqual(current_observation_value['id'],current_job_path.name)
                self.assertTrue(current_observation_value['running'])
                self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
                self.assertFalse((current_job_path/'resume.lock').exists())
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=3)

    def test_audio_download_observed_when_model_service_unavailable(self):
        import os
        from workflow.common.management_gateway import execute_management_command
        from workflow.common.management_transport import send_management_json_response
        def reject_audio_status(current_request_handler, current_method_value, current_route_value, current_payload_record):
            return send_management_json_response(current_request_handler,503,{'error':'service unavailable'})
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_manager_value=HermesServiceManager(Path(current_temp_root)/'jobs',Path(current_temp_root)/'sessions')
            current_gateway_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request,'music-heartmula':reject_audio_status})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_values:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                current_gateway_address=f'http://127.0.0.1:{current_server_value.server_port}'
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_gateway_address}), patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='running'), patch('workflow.common.audio_model_download.inspect_audio_download_files',return_value=False), patch('workflow.common.model_prepare_process.start_registered_preparation') as current_start_mock:
                    current_result_value=execute_management_command('hermes-agent','hermes-model-readiness',{'service':'music-heartmula'},current_gateway_address)
                self.assertEqual(current_result_value['status'],'unavailable')
                self.assertEqual(current_result_value['download'],{'ready':False,'preparation_status':'running'})
                current_start_mock.assert_not_called()
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_restart_preserves_sessions_receipts_and_prevents_relaunch(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_root_path = Path(current_temp_root)
            current_store_path = current_root_path / 'delegations'
            current_store_value = HermesDelegationStore(current_store_path)
            current_request_value = {'action':'generate', 'prompt':'테스트'}
            current_store_value.execute_delegation_once('receipt_123456', {'service':'kimodo', 'request':current_request_value}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('unknown_123456', {}, Mock(side_effect=TimeoutError()))
            current_session_identifier = 'a' * 32
            current_session_payload = {'session_id':current_session_identifier, 'request_id':'session_123456', 'prompt':'재시작 시험'}

            def start_test_gateway():
                current_service_value = HermesServiceManager(current_root_path / 'jobs', current_root_path / 'sessions')
                current_gateway_value = ManagementCommandGateway({'hermes-agent':current_service_value.handle_hermes_request})
                current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), create_gateway_request_handler(current_gateway_value.handle))
                current_server_value.emit_gateway_trace = lambda *current_values: None
                current_thread_value = threading.Thread(target=current_server_value.serve_forever, daemon=True)
                current_thread_value.start()
                return current_server_value, current_thread_value

            def request_test_command(current_server_value, current_command_name, current_payload_value):
                current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
                current_body_value = json.dumps({'service':'hermes-agent', 'command':current_command_name, 'payload':current_payload_value}, ensure_ascii=False).encode()
                current_request_object = Request(current_address_value + '/management/command', data=current_body_value, headers={'Content-Type':'application/json','Origin':current_address_value}, method='POST')
                with urlopen(current_request_object, timeout=5) as current_response_value:
                    return json.load(current_response_value)

            def stop_test_gateway(current_server_value, current_thread_value):
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()
                self.assertFalse(current_thread_value.is_alive())

            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value='resident_123'), patch('workflow.domains.hermes_agent.resident_chat_executor.launch_resident_chat') as current_launch_mock, patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore', side_effect=lambda: HermesDelegationStore(current_store_path)):
                current_server_value, current_thread_value = start_test_gateway()
                try:
                    current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
                    current_denied_body = json.dumps({'service':'hermes-agent','command':'hermes-session-create','payload':{'session_id':'b' * 32}}).encode()
                    current_denied_request = Request(current_address_value + '/management/command', data=current_denied_body, headers={'Content-Type':'application/json','Origin':'http://other.invalid'}, method='POST')
                    with self.assertRaises(HTTPError) as current_denied_error:
                        urlopen(current_denied_request, timeout=5)
                    self.assertEqual(current_denied_error.exception.code, 400)
                    self.assertFalse((current_root_path / 'sessions' / ('b' * 32 + '.json')).exists())
                    request_test_command(current_server_value, 'hermes-session-create', {'session_id':current_session_identifier})
                    current_first_result = request_test_command(current_server_value, 'hermes-session-submit', current_session_payload)
                    self.assertFalse(current_first_result['duplicate'])
                finally:
                    stop_test_gateway(current_server_value, current_thread_value)
                current_server_value, current_thread_value = start_test_gateway()
                try:
                    current_retry_result = request_test_command(current_server_value, 'hermes-session-submit', current_session_payload)
                    self.assertTrue(current_retry_result['duplicate'])
                    self.assertEqual(current_retry_result['job_id'], current_first_result['job_id'])
                    self.assertEqual(request_test_command(current_server_value, 'hermes-session-read', {'session_id':current_session_identifier})['messages'][0]['job_id'], current_first_result['job_id'])
                    current_receipt_value = request_test_command(current_server_value, 'hermes-delegate-kimodo', {'request_id':'receipt_123456', 'request':current_request_value})
                    self.assertTrue(current_receipt_value['duplicate'])
                    self.assertEqual(current_receipt_value['job_id'], '2026-11-18_00-00-00-12345678')
                    self.assertEqual(request_test_command(current_server_value, 'hermes-delegation-status', {'request_id':'unknown_123456'})['state'], 'unknown')
                    with self.assertRaises(HTTPError) as current_error_value:
                        request_test_command(current_server_value, 'hermes-session-submit', {**current_session_payload, 'prompt':'다른 지시'})
                    self.assertEqual(current_error_value.exception.code, 400)
                finally:
                    stop_test_gateway(current_server_value, current_thread_value)
            current_launch_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
