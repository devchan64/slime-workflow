"""DWPose·Wan 서비스별 접수, 결과 경로, 중지 경계 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.management.domains.hermes_agent import video_operations
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesVideoOperationsTests(unittest.TestCase):
    def test_services_delegate_independently_and_reject_prepare(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(video_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(video_operations,'validate_hermes_video_request') as current_validate_mock, patch.object(video_operations,'call_hermes_video_service',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_service_name in enumerate(video_operations.HERMES_VIDEO_SERVICES):
                current_request_id='video_request_'+str(current_index_value)
                current_request_value={'action':'generate'}
                self.assertFalse(video_operations.submit_hermes_video_request(current_request_id,current_service_name,current_request_value)['duplicate'])
                self.assertTrue(video_operations.submit_hermes_video_request(current_request_id,current_service_name,current_request_value)['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,4)
            self.assertEqual(current_validate_mock.call_count,4)
            with self.assertRaises(ValueError):
                video_operations.read_hermes_video_status('video_request_0','wan22-vace')
            with self.assertRaises(ValueError):
                video_operations.list_hermes_video_receipts('arbitrary-service')
        with self.assertRaises(ValueError):
            video_operations.validate_hermes_video_request('wan22-fun-control',{'action':'prepare'})

    def test_video_source_observation_rejects_status_change_and_special_file(self):
        import os
        from types import SimpleNamespace
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_job_root=current_storage_root/current_job_identifier
            current_job_root.mkdir()
            current_status_path=current_job_root/'status.json'
            current_manager_value=SimpleNamespace(job_storage_root=current_storage_root)
            with patch.object(video_operations,'make_hermes_video_manager',return_value=current_manager_value):
                os.mkfifo(current_status_path)
                with self.assertRaises(ValueError):video_operations.read_hermes_video_source_job('dwpose',current_job_identifier)
                current_status_path.unlink()
                current_status_path.write_text('{"status":"running"}')
                with patch('tools.management.domains.hermes_agent.delegation_store.read_bounded_delegation_record',side_effect=[{'status':'running'},{'status':'completed'}]):
                    with self.assertRaisesRegex(ValueError,'조회 중 변경'):video_operations.read_hermes_video_source_job('dwpose',current_job_identifier)

    def test_video_source_observation_uses_each_actual_manager_storage(self):
        import json
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_service_settings=(('dwpose','tools.management.domains.dwpose.generation.DWPOSE_JOB_STORAGE'),('wan22-animate2','tools.management.domains.wan_animate2.generation.ANIMATE_JOB_STORAGE'),('wan22-vace','tools.management.domains.wan_vace.generation.VACE_JOB_STORAGE'),('wan22-fun-control','tools.management.domains.wan_fun.generation.FUN_JOB_STORAGE'),('kimodo','tools.management.domains.kimodo.generation.KIMODO_JOB_STORAGE'))
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            for current_service_name,current_storage_setting in current_service_settings:
                with self.subTest(service=current_service_name):
                    current_storage_root=current_root_path/current_service_name
                    current_job_root=current_storage_root/current_job_identifier
                    current_attempt_root=current_job_root/'attempts'/('a'*32)
                    current_attempt_root.mkdir(parents=True)
                    (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
                    (current_job_root/'result.json').write_text(json.dumps({'attempt':'a'*32}))
                    for current_file_name in ('preview.mp4','output-000.png','frames.zip'):(current_attempt_root/current_file_name).write_bytes(b'mock')
                    with patch(current_storage_setting,current_storage_root),patch('tools.management.common.video_job_recovery.recover_interrupted_video_job') as current_recovery_mock:
                        current_result_value=video_operations.read_hermes_video_source_job(current_service_name,current_job_identifier)
                        self.assertEqual(current_result_value['result_status'],'available')
                        self.assertEqual(current_result_value['video'],'/'+current_service_name+'/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/preview.mp4')
                        current_recovery_mock.assert_not_called()
                        (current_attempt_root/'preview.mp4').unlink()
                        (current_attempt_root/'preview.mp4').symlink_to(current_attempt_root/'output-000.png')
                        self.assertEqual(video_operations.read_hermes_video_source_job(current_service_name,current_job_identifier)['result_status'],'unavailable')
                        self.assertEqual(json.loads((current_job_root/'status.json').read_text()),{'status':'completed'})

    def test_source_observation_rejects_changed_result_attempt(self):
        import json
        from types import SimpleNamespace
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_root=current_root_path/current_job_identifier
            current_attempt_root=current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_root/'result.json').write_text(json.dumps({'attempt':'a'*32}))
            for current_file_name in ('preview.mp4','output-000.png','frames.zip'):(current_attempt_root/current_file_name).write_bytes(b'fixture')
            current_status_record={'status':'completed'}
            with patch.object(video_operations,'make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=current_root_path)),patch('tools.management.domains.hermes_agent.delegation_store.read_bounded_delegation_record',side_effect=[current_status_record,{'attempt':'a'*32},current_status_record,{'attempt':'b'*32}]):
                with self.assertRaisesRegex(ValueError,'결과가 조회 중 변경'):video_operations.read_hermes_video_source_job('kimodo',current_job_identifier)

    def test_kimodo_source_links_reach_runtime_and_actual_file_handler(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import Request,urlopen
        from tools.management.common.management_gateway import MANAGEMENT_SERVICE_ROUTES,execute_management_command
        from tools.management.common.management_runtime import ManagementServiceRuntime,bind_stored_management_service
        from tools.management.common.management_transport import proxy_management_request
        from tools.management.domains.hermes_agent.service import HermesServiceManager
        from tools.management.domains.kimodo.generation import KimodoGenerationManager
        from tools.management.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_kimodo_manager=KimodoGenerationManager()
            current_kimodo_manager.job_storage_root=current_root_path/'kimodo'
            current_job_root=current_kimodo_manager.job_storage_root/current_job_identifier
            current_attempt_root=current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_root/'result.json').write_text(json.dumps({'attempt':'a'*32}))
            for current_file_name in ('preview.mp4','output-000.png','frames.zip'):(current_attempt_root/current_file_name).write_bytes(b'fixture-'+current_file_name.encode())
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_bindings_map={current_name:bind_stored_management_service(lambda current_request:False,current_root_path) for current_name in MANAGEMENT_SERVICE_ROUTES}
            current_bindings_map['hermes-agent']=bind_stored_management_service(current_hermes_manager.handle_hermes_request,current_root_path/'hermes')
            current_bindings_map['kimodo']=bind_stored_management_service(current_kimodo_manager.handle_image_request,current_kimodo_manager.job_storage_root)
            current_runtime_value=ManagementServiceRuntime(current_bindings_map,lambda current_request:False,lambda:None)
            current_gateway_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_runtime_value.dispatch_runtime_request))
            current_gateway_server.emit_gateway_trace=lambda *current_values:None
            current_gateway_thread=threading.Thread(target=current_gateway_server.serve_forever,daemon=True)
            current_gateway_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_gateway_server.server_port)
            class TestProxyHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if not proxy_management_request(self,current_gateway_url):self.send_error(404)
                def log_message(self,*current_values):pass
            current_proxy_server=ThreadingHTTPServer(('127.0.0.1',0),TestProxyHandler)
            current_proxy_thread=threading.Thread(target=current_proxy_server.serve_forever,daemon=True)
            current_proxy_thread.start()
            current_proxy_url='http://127.0.0.1:'+str(current_proxy_server.server_port)
            try:
                with patch.object(video_operations,'make_hermes_video_source_manager',return_value=current_kimodo_manager),patch('tools.management.common.video_job_recovery.recover_interrupted_video_job') as current_recovery_mock:
                    current_response_value=execute_management_command('hermes-agent','hermes-video-source-status',{'service':'kimodo','job_id':current_job_identifier},current_gateway_url)
                    current_job_record=video_operations.validate_hermes_video_source_response('kimodo',current_job_identifier,current_response_value)
                    for current_field_name,current_file_name in (('video','preview.mp4'),('image','output-000.png'),('download','frames.zip')):
                        with urlopen(current_proxy_url+current_job_record[current_field_name],timeout=5) as current_http_response:self.assertEqual(current_http_response.read(),b'fixture-'+current_file_name.encode())
                    with urlopen(Request(current_proxy_url+current_job_record['video'],headers={'Range':'bytes=0-3'}),timeout=5) as current_range_response:self.assertEqual((current_range_response.status,current_range_response.read()),(206,b'fixt'))
                    current_recovery_mock.assert_not_called()
                    self.assertEqual(json.loads((current_job_root/'status.json').read_text()),{'status':'completed'})
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_kimodo_source_does_not_expand_video_delegation_contract(self):
        self.assertIn('kimodo',video_operations.HERMES_VIDEO_SOURCE_SERVICES)
        self.assertNotIn('kimodo',video_operations.HERMES_VIDEO_SERVICES)
        with self.assertRaises(ValueError):video_operations.validate_hermes_video_service('kimodo')

    def test_video_source_observation_never_recovers_and_checks_result_files(self):
        import json
        from types import SimpleNamespace
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier
            current_job_path.mkdir()
            current_status_path=current_job_path/'status.json'
            current_status_path.write_text(json.dumps({'status':'running'}))
            current_manager_value=SimpleNamespace(job_storage_root=current_root_path)
            with patch.object(video_operations,'make_hermes_video_manager',return_value=current_manager_value),patch('tools.management.common.video_job_recovery.recover_interrupted_video_job') as current_recovery_mock,patch.object(video_operations,'call_hermes_video_service') as current_gateway_mock:
                self.assertEqual(video_operations.read_hermes_video_source_job('wan22-vace',current_job_identifier)['status'],'running')
                current_status_path.write_text(json.dumps({'status':'completed'}))
                (current_job_path/'result.json').write_text(json.dumps({'attempt':'a'*32}))
                current_attempt_path=current_job_path/'attempts'/('a'*32)
                current_attempt_path.mkdir(parents=True)
                for current_file_name in ('preview.mp4','output-000.png','frames.zip'):(current_attempt_path/current_file_name).write_bytes(b'mock')
                current_result_value=video_operations.read_hermes_video_source_job('wan22-vace',current_job_identifier)
                self.assertEqual(current_result_value['result_status'],'available')
                self.assertTrue(current_result_value['video'].endswith('/preview.mp4'))
                (current_attempt_path/'frames.zip').unlink()
                self.assertEqual(video_operations.read_hermes_video_source_job('wan22-vace',current_job_identifier)['result_status'],'unavailable')
                self.assertEqual(json.loads(current_status_path.read_text()),{'status':'completed'})
                current_recovery_mock.assert_not_called()
                current_gateway_mock.assert_not_called()
                with self.assertRaises(ValueError):video_operations.read_hermes_video_source_job('wan22-vace','../invalid')

    def test_video_paths_are_same_service_job_and_attempt(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_good_path='/wan22-vace/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/preview.mp4'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('video_request_123','wan22-vace',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(video_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(video_operations,'call_hermes_video_service',return_value={'status':'completed','video':current_good_path,'log':'private'}) as current_gateway_mock:
                current_result_value=video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-ffffffff','status':'completed','video':current_good_path}
                with self.assertRaises(ValueError):
                    video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','video':current_good_path}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['video'],current_good_path)
                self.assertEqual(current_result_value['job']['video'],current_good_path)
                self.assertEqual(current_result_value['job']['result_status'],'partial')
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'status':'completed','video':current_good_path,'image':current_good_path.replace('preview.mp4','output-000.png'),'download':current_good_path.replace('preview.mp4','frames.zip')}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['result_status'],'available')
                current_gateway_mock.return_value={'status':'completed','result_error':'private filesystem detail','video':current_good_path}
                current_result_value=video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                self.assertEqual(current_result_value['job']['result_status'],'unavailable')
                self.assertIsNone(current_result_value['job']['video'])
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'status':'completed','video':current_good_path,'image':current_good_path.replace('a'*32,'b'*32).replace('preview.mp4','output-000.png')}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['result_status'],'unavailable')
                current_gateway_mock.return_value={'status':'completed','video':'https://evil.invalid/video.mp4'}
                self.assertIsNone(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['video'])
                with self.assertRaises(ValueError):
                    video_operations.cancel_hermes_video_request('video_request_123','wan22-vace','2026-11-18_00-00-00-ffffffff')

    def test_attached_video_ui_confirms_real_service_receipt(self):
        from tools.management.ui.gradio import hermes_agent_app
        current_job='2026-11-18_00-00-00-12345678'
        current_source={'proposal':{'service':'dwpose'},'request_id':'video_request_123'}
        current_review={'source':current_source,'review':{'request_id':'video_request_123','service':'dwpose','request':{'action':'generate'}}}
        def current_gateway(current_service,current_command,current_payload):
            self.assertEqual(current_service,'hermes-agent')
            if current_command=='hermes-delegate-video':return video_operations.submit_hermes_video_request(current_payload['request_id'],current_payload['service'],current_payload['request'])
            if current_command=='hermes-video-status':return video_operations.read_hermes_video_status(current_payload['request_id'],current_payload['service'])
            raise AssertionError(current_command)
        def current_video_service(current_service,current_command,current_payload):
            return {'id':current_job} if current_command=='generate' else {'id':current_job,'status':'queued'}
        with TemporaryDirectory() as current_root, patch.object(video_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root))), patch.object(video_operations,'validate_hermes_video_request'), patch.object(video_operations,'call_hermes_video_service',side_effect=current_video_service) as current_video_mock, patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway), patch.object(hermes_agent_app,'review_conversation_video_inputs',return_value=(current_review,'','')):
            for current_iteration in range(2):
                _,current_message=hermes_agent_app.submit_conversation_video_inputs(current_review,current_source,'session','job','{}',None,None,None,None,None)
                self.assertIn('queued',current_message)
            self.assertEqual(sum(current_call.args[1]=='generate' for current_call in current_video_mock.call_args_list),1)

    def test_unknown_video_response_is_not_resent(self):
        with TemporaryDirectory() as current_root_name, patch.object(video_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(video_operations,'validate_hermes_video_request'), patch.object(video_operations,'call_hermes_video_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                video_operations.submit_hermes_video_request('video_unknown_123','dwpose',{'action':'generate'})
            self.assertEqual(video_operations.read_hermes_video_status('video_unknown_123','dwpose')['receipt']['state'],'unknown')
            self.assertTrue(video_operations.submit_hermes_video_request('video_unknown_123','dwpose',{'action':'generate'})['duplicate'])
            current_gateway_mock.assert_called_once()
