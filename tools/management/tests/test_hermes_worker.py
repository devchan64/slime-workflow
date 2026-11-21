import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import Mock, patch

from tools.management.domains.hermes_agent import worker as hermes_worker_module
from tools.management.domains.hermes_agent import runtime_integrity as hermes_runtime_module


class HermesWorkerTests(unittest.TestCase):
    def setUp(self):
        current_trial_directory = tempfile.TemporaryDirectory()
        self.addCleanup(current_trial_directory.cleanup)
        current_trial_root = Path(current_trial_directory.name)
        current_python_path = current_trial_root / '.venv/bin/python'
        current_python_path.parent.mkdir(parents=True)
        current_python_path.touch()
        current_root_patch = patch.object(hermes_worker_module, 'WORKFLOW_ROOT_DIRECTORY', current_trial_root)
        current_root_patch.start()
        self.addCleanup(current_root_patch.stop)

    def test_model_use_guard_distinguishes_running_worker_from_preparation(self):
        from tools.management.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation, hold_hermes_model_usage_guard
        current_working_root = hermes_worker_module.WORKFLOW_ROOT_DIRECTORY
        current_job_path = current_working_root / 'job'
        current_job_path.mkdir()
        def check_running_model_guard(current_job_value):
            self.assertEqual(current_job_value, current_job_path)
            self.assertEqual(inspect_registered_preparation(current_working_root, 'hermes-model'), 'idle')
            with patch('tools.management.common.model_prepare_process.subprocess.Popen') as current_spawn_mock:
                with self.assertRaisesRegex(ValueError, '모델이 준비 또는 실행 중'):
                    start_registered_preparation(current_working_root, 'hermes-model')
                current_spawn_mock.assert_not_called()
            raise RuntimeError('모의 작업 종료')
        with patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'execute_hermes_gpu_job', side_effect=check_running_model_guard) as current_worker_mock:
            with self.assertRaisesRegex(RuntimeError, '모의 작업 종료'):
                hermes_worker_module.execute_guarded_hermes_gpu_job(current_job_path)
            with hold_hermes_model_usage_guard(current_working_root):
                with self.assertRaisesRegex(ValueError, '모델이 준비 또는 실행 중'):
                    hermes_worker_module.execute_guarded_hermes_gpu_job(current_job_path)
            current_worker_mock.assert_called_once()
        with hold_hermes_model_usage_guard(current_working_root):
            pass

    def test_model_use_conflict_records_actionable_job_failure(self):
        from tools.management.common.model_prepare_process import hold_hermes_model_usage_guard
        current_working_root = hermes_worker_module.WORKFLOW_ROOT_DIRECTORY
        current_job_path = current_working_root / 'job-conflict'
        current_job_path.mkdir()
        (current_job_path / 'status.json').write_text(json.dumps({'status':'running'}))
        with hold_hermes_model_usage_guard(current_working_root), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation') as current_reservation_mock, patch.object(hermes_worker_module, 'execute_hermes_gpu_job') as current_execution_mock:
            with self.assertRaisesRegex(ValueError, '모델이 준비 또는 실행 중'):
                hermes_worker_module.execute_guarded_hermes_gpu_job(current_job_path)
            current_execution_mock.assert_not_called()
            current_reservation_mock.assert_called_once_with(current_job_path.resolve())
        current_status_record = json.loads((current_job_path / 'status.json').read_text())
        self.assertEqual(current_status_record['status'], 'failed')
        self.assertIn('준비 또는 사용 중', current_status_record['error'])
        self.assertIn('새 요청', current_status_record['error'])

    def test_model_use_guard_stays_with_detached_preparation_process(self):
        import sys
        from tools.management.common.model_prepare_process import hold_hermes_model_usage_guard, start_detached_preparation, start_registered_preparation, inspect_registered_preparation
        current_working_root = hermes_worker_module.WORKFLOW_ROOT_DIRECTORY
        current_state_root = current_working_root / '.local/model-preparation/hermes-model'
        current_script_path = current_working_root / 'fake_prepare.py'
        current_script_path.write_text('import time\ntime.sleep(0.8)\n')
        current_process_handle = start_detached_preparation(current_state_root, [sys.executable, str(current_script_path)], current_working_root, return_process_value=True, current_usage_guard=hold_hermes_model_usage_guard(current_working_root))
        try:
            self.assertEqual(inspect_registered_preparation(current_working_root, 'hermes-model'), 'running')
            with patch('tools.management.common.model_prepare_process.subprocess.Popen') as current_duplicate_spawn:
                self.assertEqual(start_registered_preparation(current_working_root, 'hermes-model'), {'preparation_status': 'running'})
                current_duplicate_spawn.assert_not_called()
            with self.assertRaisesRegex(ValueError, '모델이 준비 또는 실행 중'):
                with hold_hermes_model_usage_guard(current_working_root):
                    pass
            self.assertEqual(current_process_handle.wait(timeout=5), 0)
            with hold_hermes_model_usage_guard(current_working_root):
                pass
        finally:
            if current_process_handle.poll() is None:
                current_process_handle.terminate()
                current_process_handle.wait(timeout=5)

    def test_real_isolated_network_cannot_reach_host_loopback(self):
        import shutil
        import socket
        import sys
        current_bwrap_path = shutil.which('bwrap')
        if current_bwrap_path is None:
            self.skipTest('bubblewrap이 없습니다.')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as current_listener_socket:
            current_listener_socket.bind(('127.0.0.1', 0))
            current_listener_socket.listen(2)
            current_listener_port = current_listener_socket.getsockname()[1]
            with socket.create_connection(('127.0.0.1', current_listener_port), timeout=2):
                pass
            current_sandbox_code = "import json,os,socket,sys; s=socket.socket(); s.settimeout(2); result=s.connect_ex(('127.0.0.1',int(sys.argv[1]))); print(json.dumps({'connect_result':result,'test_env':os.environ.get('HERMES_BOUNDARY_TEST_VALUE'),'host_home_visible':os.path.exists('/home')}))"
            current_sandbox_arguments = [current_bwrap_path, '--die-with-parent', '--unshare-all', '--clearenv', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev', '--', '/usr/bin/python3', '-c', current_sandbox_code, str(current_listener_port)]
            current_sandbox_environment = dict(os.environ, HERMES_BOUNDARY_TEST_VALUE='not-for-sandbox')
            current_sandbox_result = subprocess.run(current_sandbox_arguments, env=current_sandbox_environment, capture_output=True, text=True, timeout=10)
            if current_sandbox_result.returncode and ('Operation not permitted' in current_sandbox_result.stderr or 'Creating new namespace failed' in current_sandbox_result.stderr):
                self.skipTest('이 환경은 격리 네임스페이스 실행을 허용하지 않습니다.')
            self.assertEqual(current_sandbox_result.returncode, 0, current_sandbox_result.stderr)
            current_sandbox_record = json.loads(current_sandbox_result.stdout)
            self.assertNotEqual(current_sandbox_record['connect_result'], 0)
            self.assertIsNone(current_sandbox_record['test_env'])
            self.assertFalse(current_sandbox_record['host_home_visible'])

    def test_audio_source_status_fixed_bridge_validates_input(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,audio_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        for current_payload_value,current_expected_key in (({'service':'music-heartmula','job_id':current_job_identifier},'job'),({'service':'music-heartmula','job_id':current_job_identifier,'extra':1},'error')):
            with self.subTest(payload=current_payload_value):
                current_client_socket,current_server_socket=socket.socketpair()
                with current_client_socket,patch.object(audio_operations,'read_hermes_audio_source_job',return_value={'status':'queued'}) as current_reader_mock:
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_value.start()
                    current_client_socket.sendall(b'audio-source-status '+json.dumps(current_payload_value).encode()+b'\n')
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_value.join(timeout=3)
                    self.assertIn(current_expected_key,current_response_value)
                    self.assertEqual(current_reader_mock.call_count,1 if current_expected_key=='job' else 0)

    def test_observer_bridge_accepts_only_fixed_read_request(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes, current_expected_key in ((b'gpu-queue\n', 'gpu'), (b'gpu-queue\nother\n', 'error'), (b'run shell\n', 'error')):
            with self.subTest(request=current_request_bytes):
                current_client_socket, current_server_socket = socket.socketpair()
                self.addCleanup(current_client_socket.close)
                self.addCleanup(current_server_socket.close)
                with patch.object(management_bridge, 'read_hermes_management_snapshot', return_value={'gpu': {'status':'idle'}}) as current_snapshot_mock:
                    current_thread_handle = threading.Thread(target=management_bridge.handle_hermes_observer_connection, args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record = json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertFalse(current_thread_handle.is_alive())
                    self.assertIn(current_expected_key, current_response_record)
                    self.assertEqual(current_snapshot_mock.call_count, 1 if current_expected_key == 'gpu' else 0)

    def test_content_database_bridge_only_accepts_fixed_request(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes, current_allowed_value in ((b'content-database-status\n',True),(b'content-database-status extra\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket, current_server_socket = socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge, 'read_hermes_content_database_status', return_value={'status':'unavailable'}) as current_status_mock:
                    current_thread_handle = threading.Thread(target=management_bridge.handle_hermes_observer_connection, args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value = json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    if current_allowed_value:
                        self.assertEqual(current_response_value['status'],'unavailable')
                        current_status_mock.assert_called_once()
                    else:
                        self.assertIn('error',current_response_value)
                        current_status_mock.assert_not_called()

    def test_kimodo_resume_bridge_only_allows_valid_preview_identifier(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_valid_identifier='2026-11-20_00-00-00-12345678'
        current_cases=((('kimodo-resume-preview '+current_valid_identifier+'\n').encode(),True),(b'kimodo-resume-preview ../invalid\n',False),(('kimodo-resume-preview '+current_valid_identifier+'\nresume\n').encode(),False))
        for current_request_bytes,current_allowed_value in current_cases:
            with self.subTest(current_request_bytes=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.hermes_agent.kimodo_resume_operations.preview_hermes_kimodo_resume',return_value={'service':'kimodo','job_id':current_valid_identifier}) as current_preview_mock,patch('tools.management.domains.hermes_agent.kimodo_resume_operations.submit_hermes_kimodo_resume_once') as current_submit_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertFalse(current_thread_handle.is_alive())
                    if current_allowed_value:
                        self.assertEqual(current_response_record['job_id'],current_valid_identifier)
                        current_preview_mock.assert_called_once_with(current_valid_identifier)
                    else:
                        self.assertIn('error',current_response_record)
                        current_preview_mock.assert_not_called()
                    current_submit_mock.assert_not_called()

    def test_sandbox_flux_resume_preview_forwards_fixed_json(self):
        import json
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        current_request_text=json.dumps({'service':'flux-character','job_id':'2026-11-20_00-00-00-12345678'})
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"service":"flux-character"}\n'
            self.assertEqual(read_sandbox_management_status('flux-resume-preview',current_request_text),{'service':'flux-character'})
            current_socket_value.sendall.assert_called_once_with(('flux-resume-preview '+current_request_text+'\n').encode())
        with self.assertRaises(ValueError):read_sandbox_management_status('flux-resume-preview','{}\nexecute')

    def test_sandbox_kimodo_resume_preview_validates_job_id(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        current_job_identifier='2026-11-20_00-00-00-12345678'
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"service":"kimodo"}\n'
            self.assertEqual(read_sandbox_management_status('kimodo-resume-preview',current_job_identifier),{'service':'kimodo'})
            current_socket_value.sendall.assert_called_once_with(('kimodo-resume-preview '+current_job_identifier+'\n').encode())
        with self.assertRaises(ValueError):read_sandbox_management_status('kimodo-resume-preview','../invalid')

    def test_city_map_bridge_reads_only_valid_city_identifier(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed in ((b'city-map stonewarm\n',True),(b'city-map ../secret\n',False),(b'city-map stonewarm\nother\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.hermes_agent.city_map_operations.load_hermes_city_map',return_value={'map':'stonewarm','generation':1,'revision':2,'document':{}}) as current_reader_mock:
                    current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread.join(timeout=3)
                    self.assertFalse(current_thread.is_alive())
                    if current_allowed:
                        self.assertEqual(current_response['map'],'stonewarm')
                        current_reader_mock.assert_called_once_with('stonewarm')
                    else:
                        self.assertIn('error',current_response)
                        current_reader_mock.assert_not_called()

    def test_city_map_bridge_rejects_oversize_response_without_partial_document(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_client_socket,current_server_socket=socket.socketpair()
        self.addCleanup(current_client_socket.close)
        with patch('tools.management.domains.hermes_agent.city_map_operations.load_hermes_city_map',return_value={'map':'stonewarm','document':'x'*262144}):
            current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread.start()
            current_client_socket.sendall(b'city-map stonewarm\n')
            current_response=json.loads(current_client_socket.makefile('rb').readline())
            current_thread.join(timeout=3)
            self.assertIn('크기 제한 초과',current_response['error'])
            self.assertNotIn('document',current_response)

    def test_expression_catalog_bridge_validates_fixed_request(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed in ((b'expression-catalog {"query":"joy"}\n',True),(b'expression-catalog {"query":"joy","query":"bad"}\n',False),(b'expression-catalog {"path":"/tmp"}\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread.start()
                current_client_socket.sendall(current_request_bytes)
                current_response=json.loads(current_client_socket.makefile('rb').readline())
                current_thread.join(timeout=3)
                self.assertIn('records' if current_allowed else 'error',current_response)
                if current_allowed:self.assertIn({'id':'joy','label':'기쁨'},current_response['records'])

    def test_source_history_bridge_rejects_invalid_or_extra_input(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,audio_operations
        for current_request_bytes,current_allowed_value in ((b'source-history {"service":"flux-image","limit":1}\n',True),(b'source-history {"service":"flux-image","query":"12345678"}\n',True),(b'source-history {"service":"flux-image","service":"kimodo"}\n',False),(b'source-history {"service":"flux-image","path":"/tmp"}\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(audio_operations,'read_hermes_generator_source_history',return_value={'records':[]}) as current_history_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertEqual(current_history_mock.call_count,int(current_allowed_value))
                    self.assertIn('records' if current_allowed_value else 'error',current_response_value)

    def test_sandbox_client_preserves_fixed_resume_and_cleanup_errors(self):
        import re
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        current_error_cases=(('video-resume-preview','{}','영상 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.'),('cleanup-preview','kimodo','정리 미리보기를 확인할 수 없습니다. 원 서비스 상태를 확인하세요.'),('cleanup-preview','kimodo','/private/path'))
        for current_request_kind,current_request_input,current_error_text in current_error_cases:
            with self.subTest(request=current_request_kind,error=current_error_text),patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
                current_socket_value=current_socket_factory.return_value.__enter__.return_value
                current_socket_value.recv.return_value=(json.dumps({'error':current_error_text},ensure_ascii=False)+'\n').encode()
                current_expected_text='관리 상태 조회가 거절됐습니다.' if current_error_text=='/private/path' else current_error_text
                with self.assertRaisesRegex(ValueError,re.escape(current_expected_text)):
                    read_sandbox_management_status(current_request_kind,current_request_input)

    def test_map_database_receipt_sandbox_client_sends_fixed_request(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        current_request_text=json.dumps({'database_request_id':'test','request_sha256':'a'*64})
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"state":"not_found"}\n'
            self.assertEqual(read_sandbox_management_status('map-database-receipt',current_request_text),{'state':'not_found'})
            current_socket_value.sendall.assert_called_once_with(('map-database-receipt '+current_request_text+'\n').encode())
        current_long_request=json.dumps({'database_request_id':'😀'*180,'request_sha256':'a'*64})
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"state":"not_found"}\n'
            self.assertEqual(read_sandbox_management_status('map-database-receipt',current_long_request),{'state':'not_found'})
        with self.assertRaises(ValueError):read_sandbox_management_status('map-database-receipt','x'*4001)
        with self.assertRaises(ValueError):read_sandbox_management_status('map-database-receipt','{}\nrun shell')

    def test_map_database_receipt_bridge_rejects_extra_and_invalid_inputs(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_valid_hash='a'*64
        current_request_values=[({'database_request_id':'😀'*180,'request_sha256':current_valid_hash},True),({'database_request_id':'😀'*181,'request_sha256':current_valid_hash},False),({'database_request_id':'db-1','request_sha256':current_valid_hash},True),({'database_request_id':'db-1','request_sha256':'bad'},False),({'database_request_id':'db-1','request_sha256':current_valid_hash,'action':'save'},False)]
        for current_payload_value,current_allowed_value in current_request_values:
            with self.subTest(payload=current_payload_value):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'matched'}) as current_http_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(('map-database-receipt '+json.dumps(current_payload_value)+'\n').encode())
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertFalse(current_thread_handle.is_alive())
                    self.assertEqual(current_http_mock.call_count,int(current_allowed_value))
                    self.assertIn('state' if current_allowed_value else 'error',current_response_value)
                    if current_allowed_value:self.assertEqual(current_http_mock.call_args.args[0],'GET')
        current_client_socket,current_server_socket=socket.socketpair()
        self.addCleanup(current_client_socket.close)
        current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
        current_thread_handle.start()
        current_client_socket.sendall(('map-database-receipt {"database_request_id":"x","database_request_id":"y","request_sha256":"'+current_valid_hash+'"}\n').encode())
        self.assertIn('error',json.loads(current_client_socket.makefile('rb').readline()))
        current_thread_handle.join(timeout=3)

    def test_map_database_receipt_bridge_bounds_do_not_extend_other_requests(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_json_bytes=json.dumps({'database_request_id':'db-1','request_sha256':'a'*64}).encode()
        current_map_prefix=b'map-database-receipt '
        current_valid_bytes=current_map_prefix+current_json_bytes+b' '*(4095-len(current_map_prefix)-len(current_json_bytes))+b'\n'
        current_oversized_bytes=current_valid_bytes[:-1]+b' '+b'\n'
        current_other_bytes=b'capture-map-check '+b' '*1050+b'{}\n'
        for current_request_bytes,current_expected_calls in ((current_valid_bytes,1),(current_oversized_bytes,0),(current_other_bytes,0)):
            with self.subTest(size=len(current_request_bytes),prefix=current_request_bytes[:20]):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'matched'}) as current_http_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertFalse(current_thread_handle.is_alive())
                    self.assertEqual(current_http_mock.call_count,current_expected_calls)
                    self.assertIn('state' if current_expected_calls else 'error',current_response_value)

    def test_reservation_inspection_bridge_is_fixed_and_read_only(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,reservation_observer
        current_requests=((b'reservation-inspect {"service":"kimodo","job_id":"job-1"}\n',True),(b'reservation-inspect {"service":"kimodo","job_id":"job-1","action":"recover"}\n',False),(b'reservation-inspect {"service":"kimodo","service":"bad","job_id":"job-1"}\n',False),(b'reservation-recover {}\n',False))
        for current_request_bytes,current_allowed_value in current_requests:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(reservation_observer,'inspect_generator_reservation_identity',return_value={'executor':'unverified'}) as current_inspect_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertEqual(current_inspect_mock.call_count,int(current_allowed_value))
                    self.assertIn('executor' if current_allowed_value else 'error',current_response_record)

    def test_passive_kimodo_build_bridge_rejects_extra_commands(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed_value in ((b'kimodo-build-status\n',True),(b'kimodo-build-status extra\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge,'read_hermes_kimodo_build_status',return_value={'status':'completed','cache_status':'unverified'}) as current_status_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertEqual(current_status_mock.call_count,int(current_allowed_value))
                    self.assertIn('status' if current_allowed_value else 'error',current_response_value)

    def test_model_inventory_bridge_only_accepts_fixed_request(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_client_socket, current_server_socket = socket.socketpair()
        self.addCleanup(current_client_socket.close)
        with patch.object(management_bridge, 'read_hermes_model_inventory', return_value={'models': []}) as current_inventory_mock:
            current_thread_handle = threading.Thread(target=management_bridge.handle_hermes_observer_connection, args=(current_server_socket,))
            current_thread_handle.start()
            current_client_socket.sendall(b'model-inventory\n')
            current_response_record = json.loads(current_client_socket.makefile('rb').readline())
            current_thread_handle.join(timeout=3)
            self.assertEqual(current_response_record, {'models': []})
            current_inventory_mock.assert_called_once_with()

    def test_service_registration_bridge_rejects_extra_commands(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes, current_allowed_value in ((b'service-registration\n', True), (b'service-registration\nrun shell\n', False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket, current_server_socket = socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge, 'list_management_service_registration', return_value={'services': []}) as current_catalog_mock:
                    current_thread_handle = threading.Thread(target=management_bridge.handle_hermes_observer_connection, args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record = json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('services' if current_allowed_value else 'error', current_response_record)
                    self.assertEqual(current_catalog_mock.call_count, int(current_allowed_value))

    def test_capability_bridge_returns_same_catalog_and_rejects_extra_commands(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        from tools.management.domains.hermes_agent.capabilities import list_hermes_capability_catalog
        current_catalog_value=list_hermes_capability_catalog()
        for current_request_bytes,current_allowed_value in ((b'capabilities\n',True),(b'capabilities\nrun shell\n',False),(b'capabilities extra\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_handle.start()
                current_client_socket.sendall(current_request_bytes)
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_handle.join(timeout=3)
                self.assertFalse(current_thread_handle.is_alive())
                if current_allowed_value:self.assertEqual(current_response_value,current_catalog_value)
                else:self.assertIn('error',current_response_value)

    def test_translation_evidence_bridge_passes_bounded_data_and_rejects_wrong_fields(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, translation_operations
        current_source_text='나무'*1800
        current_response_record={'candidates':[{'path':'world/tree.md','heading':'나무','text':'문서 근거','matched_terms':['나무']}],'note':'문서 근거'}
        with patch.object(translation_operations,'search_hermes_translation_evidence',return_value=current_response_record) as current_search_mock:
            for current_request_value,current_expected_success in (({'text':current_source_text},True),({'text':'나무','action':'run'},False)):
                current_client_socket,current_server_socket=socket.socketpair()
                current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_value.start()
                with current_client_socket:
                    current_client_socket.sendall(('translation-evidence '+json.dumps(current_request_value,ensure_ascii=False)+'\n').encode('utf-8'))
                    current_actual_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_value.join(timeout=5)
                self.assertFalse(current_thread_value.is_alive())
                if current_expected_success:self.assertEqual(current_actual_value,current_response_record)
                else:self.assertIn('error',current_actual_value)
            current_search_mock.assert_called_once_with(current_source_text)

    def test_model_download_status_crosses_observer_socket(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, management_observer
        current_status_record={'records':[{'model':'org/model','status':'running','bytes':4,'total_bytes':10}],'truncated':False}
        with patch.object(management_observer,'read_hermes_model_download_status',return_value=current_status_record) as current_status_mock:
            current_client_socket,current_server_socket=socket.socketpair()
            current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread_value.start()
            with current_client_socket:
                current_client_socket.sendall(b'model-download-status\n')
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
            current_thread_value.join(timeout=5)
            self.assertEqual(current_response_value,current_status_record)
            current_status_mock.assert_called_once_with()

    def test_writer_index_status_crosses_observer_socket(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, writer_operations
        current_status_record={'status':'stale','note':'조회 시점'}
        with patch.object(writer_operations,'read_hermes_writer_index_status',return_value=current_status_record) as current_status_mock:
            current_client_socket,current_server_socket=socket.socketpair()
            current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread_value.start()
            with current_client_socket:
                current_client_socket.sendall(b'writer-index-status\n')
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
            current_thread_value.join(timeout=5)
            self.assertEqual(current_response_value,current_status_record)
            current_status_mock.assert_called_once_with()

    def test_translation_evidence_bridge_enforces_request_limit(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, translation_operations
        current_request_bytes=b'translation-evidence '+b'x'*(management_bridge.HERMES_OBSERVER_MAX_REQUEST-19)+b'\n'
        self.assertGreater(len(current_request_bytes),management_bridge.HERMES_OBSERVER_MAX_REQUEST)
        with patch.object(translation_operations,'search_hermes_translation_evidence') as current_search_mock:
            current_client_socket,current_server_socket=socket.socketpair()
            current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread_value.start()
            with current_client_socket:
                current_client_socket.sendall(current_request_bytes)
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
            current_thread_value.join(timeout=5)
            self.assertIn('error',current_response_value)
            current_search_mock.assert_not_called()

    def test_translation_evidence_bridge_reports_stale_index_without_leaking_errors(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, translation_operations
        current_error_cases=(('관리 API 오류: 문서 추가·수정·삭제 이후 색인이 오래되었습니다. 학습 갱신이 필요합니다.','작가 색인이 오래되어'),('unexpected private /path','검색 원문과 작가 색인'))
        for current_error_text,current_expected_text in current_error_cases:
            with self.subTest(current_error_text=current_error_text), patch.object(translation_operations,'search_hermes_translation_evidence',side_effect=ValueError(current_error_text)):
                current_client_socket,current_server_socket=socket.socketpair()
                current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_value.start()
                with current_client_socket:
                    current_client_socket.sendall(b'translation-evidence {"text":"tree"}\n')
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_value.join(timeout=5)
                self.assertIn(current_expected_text,current_response_value['error'])
                self.assertNotIn('/path',current_response_value['error'])

    def test_audio_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,audio_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_audio_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_audio_connection,daemon=True)
            with patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'queued'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','audio-source-status',json.dumps({'service':'music-heartmula','job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with('music-heartmula','status',{'id':current_job_identifier})

    def test_video_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,video_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_video_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_video_connection,daemon=True)
            with patch.object(video_operations,'read_hermes_video_source_job',return_value={'status':'queued','result_status':'not_ready'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','video-source-status',json.dumps({'service':'wan22-vace','job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with('wan22-vace',current_job_identifier)

    def test_kimodo_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,video_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_video_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_video_connection,daemon=True)
            with patch.object(video_operations,'read_hermes_video_source_job',return_value={'status':'queued','result_status':'not_ready'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','video-source-status',json.dumps({'service':'kimodo','job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with('kimodo',current_job_identifier)

    def test_flux_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,flux_profile_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_flux_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_flux_connection,daemon=True)
            with patch.object(flux_profile_operations,'read_hermes_flux_source_job',return_value={'status':'queued','result_status':'not_ready'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','flux-source-status',json.dumps({'service':'flux-building','job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with('flux-building',current_job_identifier)

    def test_image_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,image_source_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_flux_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_flux_connection,daemon=True)
            with patch.object(image_source_operations,'read_hermes_image_source_job',return_value={'status':'queued','result_status':'not_ready'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','image-source-status',json.dumps({'service':'building-generator','job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with('building-generator',current_job_identifier)

    def test_character_source_status_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge,management_status_client,character_source_operations
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_socket_directory,socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_flux_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_thread_value=threading.Thread(target=serve_one_flux_connection,daemon=True)
            with patch.object(character_source_operations,'read_character_source_job',return_value={'status':'queued','result_status':'not_ready'}) as current_service_mock:
                current_thread_value.start()
                current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','character-source-status',json.dumps({'job_id':current_job_identifier})]
                current_process_value=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
                current_thread_value.join(timeout=5)
                self.assertEqual(current_process_value.returncode,0,current_process_value.stderr)
                self.assertEqual(json.loads(current_process_value.stdout)['job']['status'],'queued')
                current_service_mock.assert_called_once_with(current_job_identifier)

    def test_capability_search_from_real_isolated_client(self):
        import shutil
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, management_status_client
        current_bwrap_path=shutil.which('bwrap')
        if current_bwrap_path is None:self.skipTest('bubblewrap이 없습니다.')
        with tempfile.TemporaryDirectory() as current_socket_directory, socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as current_listener_socket:
            current_socket_path=Path(current_socket_directory)/'observer.sock'
            current_listener_socket.bind(str(current_socket_path))
            current_listener_socket.listen(1)
            current_listener_socket.settimeout(10)
            def serve_one_connection():
                try:
                    current_client_socket,_=current_listener_socket.accept()
                    management_bridge.handle_hermes_observer_connection(current_client_socket)
                except TimeoutError:
                    pass
            current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
            current_server_thread.start()
            current_sandbox_arguments=[current_bwrap_path,'--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--dir','/control','--ro-bind',str(current_socket_path),'/control/management-status.sock','--ro-bind',str(Path(management_status_client.__file__)),'/control/management-status.py','--proc','/proc','--dev','/dev','--','/usr/bin/python3','/control/management-status.py','capabilities','{"query":"FLUX","limit":2}']
            current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
            if current_sandbox_result.returncode and ('Operation not permitted' in current_sandbox_result.stderr or 'Creating new namespace failed' in current_sandbox_result.stderr):self.skipTest('이 환경은 격리 네임스페이스 실행을 허용하지 않습니다.')
            self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
            current_sandbox_record=json.loads(current_sandbox_result.stdout)
            self.assertEqual(len(current_sandbox_record['records']),2)
            self.assertEqual(current_sandbox_record['next_offset'],2)
            self.assertTrue(all('flux' in str(current_record).lower() for current_record in current_sandbox_record['records']))
            current_server_thread.join(timeout=2)
            self.assertFalse(current_server_thread.is_alive())
            current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
            current_server_thread.start()
            current_sandbox_arguments[-2:]=['capabilities',json.dumps({'query':'animation_version','limit':20})]
            current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
            self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
            current_sandbox_record=json.loads(current_sandbox_result.stdout)
            self.assertIn('hermes-anchor-history-observe',[current_record['command'] for current_record in current_sandbox_record['records']])
            current_server_thread.join(timeout=2)
            self.assertFalse(current_server_thread.is_alive())
            with patch('tools.management.domains.map_assets.database_client.execute_content_api_request',return_value={'state':'matched'}) as current_content_mock:
                current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
                current_server_thread.start()
                current_sandbox_arguments[-2:]=['map-database-receipt',json.dumps({'database_request_id':'fixture-id','request_sha256':'a'*64})]
                current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
                self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
                self.assertEqual(json.loads(current_sandbox_result.stdout)['state'],'matched')
                self.assertEqual(current_content_mock.call_args.args[0],'GET')
                current_server_thread.join(timeout=2)
                self.assertFalse(current_server_thread.is_alive())
            with patch('tools.management.common.map_asset_sources.load_review_map_menu',return_value=[{'id':'test-map'}]):
                current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
                current_server_thread.start()
                current_sandbox_arguments[-2:]=['capture-map-check','{"map":"test-map"}']
                current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
                self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
                self.assertEqual(json.loads(current_sandbox_result.stdout),{'status':'registered','map':'test-map'})
                current_server_thread.join(timeout=2)
                self.assertFalse(current_server_thread.is_alive())
            current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
            current_server_thread.start()
            current_sandbox_arguments[-2:]=['capture-map-check','{"map":"stonewarm"}']
            current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=15)
            self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
            self.assertEqual(json.loads(current_sandbox_result.stdout),{'status':'registered','map':'stonewarm'})
            current_server_thread.join(timeout=3)
            self.assertFalse(current_server_thread.is_alive())
            current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
            current_server_thread.start()
            current_sandbox_arguments[-2:]=['service-registration','{"query":"music","limit":1}']
            current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
            self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
            current_sandbox_record=json.loads(current_sandbox_result.stdout)
            self.assertEqual(len(current_sandbox_record['services']),1)
            self.assertEqual(current_sandbox_record['next_offset'],1)
            self.assertIn('music',current_sandbox_record['services'][0]['service'])
            current_server_thread.join(timeout=2)
            self.assertFalse(current_server_thread.is_alive())
            from tools.management.domains.hermes_agent import reservation_observer
            with patch.object(reservation_observer,'inspect_generator_reservation_identity',return_value={'service':'kimodo','job_id':'job-1','executor':'unverified'}) as current_inspect_mock:
                current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
                current_server_thread.start()
                current_sandbox_arguments[-2:]=['reservation-inspect','{"service":"kimodo","job_id":"job-1"}']
                current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
                self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
                self.assertEqual(json.loads(current_sandbox_result.stdout)['executor'],'unverified')
                current_server_thread.join(timeout=2)
                self.assertFalse(current_server_thread.is_alive())
                current_inspect_mock.assert_called_once_with('kimodo','job-1')
            with patch('tools.management.domains.hermes_agent.capture_status.read_capture_delegation_status',return_value={'receipt':{'state':'not_found','request_id':'request_123','service':'map-review'},'job':None}) as current_capture_mock:
                current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
                current_server_thread.start()
                current_sandbox_arguments[-2:]=['capture-status','{"service":"map-review","request_id":"request_123"}']
                current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
                self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
                self.assertEqual(json.loads(current_sandbox_result.stdout)['receipt']['state'],'not_found')
                current_server_thread.join(timeout=2)
                self.assertFalse(current_server_thread.is_alive())
                self.assertEqual(current_capture_mock.call_count,1)
            with patch('tools.management.domains.hermes_agent.writer_operations.read_hermes_writer_search_paths',return_value={'paths':['world/town.md'],'truncated':False}) as current_writer_paths_mock:
                current_server_thread=threading.Thread(target=serve_one_connection,daemon=True)
                current_server_thread.start()
                current_sandbox_arguments[-2:]=['writer-search-paths','{\"request_id\":\"request_123\"}']
                current_sandbox_result=subprocess.run(current_sandbox_arguments,capture_output=True,text=True,timeout=12)
                self.assertEqual(current_sandbox_result.returncode,0,current_sandbox_result.stderr)
                self.assertEqual(json.loads(current_sandbox_result.stdout),{'paths':['world/town.md'],'truncated':False})
                current_server_thread.join(timeout=2)
                self.assertFalse(current_server_thread.is_alive())
                current_writer_paths_mock.assert_called_once_with('request_123')

    def test_custom_writer_queue_crosses_isolated_observer_socket(self):
        import socket
        import threading
        import yaml
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import management_bridge,management_observer
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
            current_client_socket,current_server_socket=socket.socketpair()
            current_client_socket.settimeout(3)
            try:
                with patch.dict(os.environ,{'SLIME_WRITER_WORKSPACE_CONFIG':str(current_config_path)}),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_path),patch('tools.management.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_gpu_reservation_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_value.start()
                    current_client_socket.sendall(b'gpu-queue\n')
                    with current_client_socket.makefile('rb') as current_response_stream:current_result_value=json.loads(current_response_stream.readline())
                    current_thread_value.join(timeout=3)
                self.assertFalse(current_thread_value.is_alive())
                self.assertEqual(current_result_value['queue']['status'],'available')
                self.assertEqual(current_result_value['queue']['jobs'][0]['id'],current_job_path.name)
                self.assertNotIn(str(current_job_path),str(current_result_value))
                self.assertTrue(current_ticket_path.is_file())
            finally:
                current_client_socket.close()

    def test_service_registration_search_pages_and_rejects_bad_input(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        from tools.management.domains.hermes_agent.capabilities import search_management_service_registration
        current_first_page=search_management_service_registration({'query':'music','limit':1})
        self.assertEqual(len(current_first_page['services']),1)
        self.assertEqual(current_first_page['next_offset'],1)
        current_next_page=search_management_service_registration({'query':'MUSIC','limit':1,'offset':1})
        self.assertNotEqual(current_first_page['services'][0]['service'],current_next_page['services'][0]['service'])
        for current_request_bytes,current_expected_key in ((b'service-registration {"query":"music","limit":1}\n','services'),(b'service-registration {"limit":11}\n','error'),(b'service-registration {"query":"a","query":"b"}\n','error')):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_handle.start()
                current_client_socket.sendall(current_request_bytes)
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_handle.join(timeout=3)
                self.assertIn(current_expected_key,current_response_value)
                if current_expected_key=='services':self.assertEqual(current_response_value,current_first_page)

    def test_service_registration_all_pages_fit_observer_protocol(self):
        import socket
        import threading
        from tools.management.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        from tools.management.domains.hermes_agent import management_bridge
        current_service_names=[]
        current_page_offset=0
        while current_page_offset is not None:
            current_client_socket,current_server_socket=socket.socketpair()
            current_client_socket.settimeout(3)
            current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread_handle.start()
            current_request_bytes=('service-registration '+json.dumps({'limit':10,'offset':current_page_offset})+'\n').encode()
            current_client_socket.sendall(current_request_bytes)
            with current_client_socket.makefile('rb') as current_response_stream:
                current_response_bytes=current_response_stream.readline()
            current_client_socket.close()
            current_thread_handle.join(timeout=3)
            self.assertFalse(current_thread_handle.is_alive())
            self.assertLessEqual(len(current_response_bytes),management_bridge.HERMES_OBSERVER_MAX_RESPONSE+1)
            current_response_record=json.loads(current_response_bytes)
            self.assertNotIn('error',current_response_record)
            self.assertEqual(current_response_record['offset'],current_page_offset)
            current_service_names.extend(record['service'] for record in current_response_record['services'])
            current_next_offset=current_response_record['next_offset']
            if current_next_offset is not None:
                self.assertGreater(current_next_offset,current_page_offset)
            current_page_offset=current_next_offset
        self.assertEqual(len(current_service_names),len(set(current_service_names)))
        self.assertEqual(set(current_service_names),set(MANAGEMENT_SERVICE_COMMANDS))

    def test_service_search_finds_korean_capability_labels(self):
        from tools.management.domains.hermes_agent.capabilities import search_management_service_registration
        current_audio_page=search_management_service_registration({'query':'음악','limit':10})
        self.assertTrue({'music-heartmula','sfx-dasheng-audiogen'} <= {current_record['service'] for current_record in current_audio_page['services']})
        current_effect_page=search_management_service_registration({'query':'이펙트 신규 등록','limit':10})
        self.assertIn('map-assets',{current_record['service'] for current_record in current_effect_page['services']})
        current_limit_page=search_management_service_registration({'query':'건물 신규 등록','limit':10})
        current_asset_record=next(current_record for current_record in current_limit_page['services'] if current_record['service']=='map-assets')
        self.assertTrue(any(current_item['command']=='building-register' for current_item in current_asset_record['conditional_limitations']))
        current_build_page=search_management_service_registration({'query':'캐시 유효성 확인','limit':10})
        self.assertTrue(any(current_record['service']=='kimodo' for current_record in current_build_page['services']))
        current_unknown_page=search_management_service_registration({'query':'존재하지않는기능','limit':10})
        self.assertEqual(current_unknown_page['services'],[])

    def test_service_search_finds_hermes_links_through_bridge(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_client_socket,current_server_socket=socket.socketpair()
        self.addCleanup(current_client_socket.close)
        current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
        current_thread_handle.start()
        current_client_socket.sendall(b'service-registration {\"query\":\"hermes-city-save\",\"limit\":10}\n')
        current_response_record=json.loads(current_client_socket.makefile('rb').readline())
        current_thread_handle.join(timeout=3)
        self.assertFalse(current_thread_handle.is_alive())
        current_records_by_service={record['service']:record for record in current_response_record['services']}
        self.assertIn('hermes-city-save',current_records_by_service['map-assets']['hermes_links'])
        self.assertIn('hermes-city-save',current_records_by_service['hermes-agent']['commands'])
        self.assertIsNone(current_response_record['next_offset'])

    def test_capability_search_pages_and_rejects_invalid_requests(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        from tools.management.domains.hermes_agent.capabilities import search_hermes_capability_catalog
        current_first_page=search_hermes_capability_catalog({'query':'FLUX','limit':2})
        self.assertEqual(len(current_first_page['records']),2)
        self.assertEqual(current_first_page['next_offset'],2)
        current_second_page=search_hermes_capability_catalog({'query':'flux','offset':2,'limit':2})
        self.assertFalse({current_record['command'] for current_record in current_first_page['records']} & {current_record['command'] for current_record in current_second_page['records']})
        for current_request_bytes,current_expected_key in ((b'capabilities {"query":"FLUX","limit":2}\n','records'),(b'capabilities {"limit":21}\n','error'),(b'capabilities {"query":"x","query":"y"}\n','error')):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_handle.start()
                current_client_socket.sendall(current_request_bytes)
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_handle.join(timeout=3)
                self.assertIn(current_expected_key,current_response_value)
                if current_expected_key=='records':self.assertEqual(current_response_value,current_first_page)

    def test_model_readiness_bridge_rejects_extra_lines(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes, current_allowed_value in ((b'model-readiness flux-image\n',True),(b'model-readiness flux-image\nrun shell\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket = socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge,'read_hermes_model_readiness',return_value={'ready':True}) as current_readiness_mock:
                    current_thread_handle = threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record = json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('ready' if current_allowed_value else 'error',current_response_record)
                    self.assertEqual(current_readiness_mock.call_count,int(current_allowed_value))

    def test_model_readiness_bridge_preserves_partial_download_status(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_client_socket,current_server_socket=socket.socketpair()
        self.addCleanup(current_client_socket.close)
        with patch('tools.management.common.management_gateway.execute_management_command',side_effect=[{'ready':False,'preparation_status':'running'},OSError('private path')]):
            current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
            current_thread_handle.start()
            current_client_socket.sendall(b'model-readiness music-heartmula\n')
            current_response_record=json.loads(current_client_socket.makefile('rb').readline())
            current_thread_handle.join(timeout=3)
        self.assertFalse(current_thread_handle.is_alive())
        self.assertEqual(current_response_record['status'],'unavailable')
        self.assertEqual(current_response_record['download'],{'ready':False,'preparation_status':'running'})
        self.assertNotIn('private',str(current_response_record))

    def test_sandbox_capability_client_uses_fixed_request(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"records":[],"unlisted_commands":[]}\n'
            self.assertEqual(read_sandbox_management_status('capabilities')['unlisted_commands'],[])
            current_socket_value.sendall.assert_called_once_with(b'capabilities\n')
        with self.assertRaises(ValueError):read_sandbox_management_status('capabilities','{}\nrun shell')

    def test_sandbox_catalog_client_encodes_korean_search_as_utf8(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"items":[]}\n'
            self.assertEqual(read_sandbox_management_status('billboard-catalog','{"query":"나무"}'),{'items':[]})
            current_socket_value.sendall.assert_called_once_with('billboard-catalog {"query":"나무"}\n'.encode('utf-8'))

    def test_billboard_bridge_rejects_extra_messages_and_duplicate_keys(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_test_cases = ((b'billboard-catalog {"query":"tree"}\n',True),(b'billboard-catalog {"query":"a","query":"b"}\n',False),(b'billboard-catalog {}\nrun shell\n',False))
        for current_request_bytes,current_allowed_value in current_test_cases:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge,'read_hermes_billboard_catalog',return_value={'items':[]}) as current_catalog_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('items' if current_allowed_value else 'error',current_response_record)
                    self.assertEqual(current_catalog_mock.call_count,int(current_allowed_value))

    def test_effect_bridge_accepts_fixed_queries_only(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge, effect_observer
        current_test_cases=((b'effect-catalog {"query":"fog"}\n','catalog'),(b'effect-detail fog-v1\n','detail'),(b'effect-detail fog-v1\nrun shell\n','error'),(b'effect-catalog {"query":"a","query":"b"}\n','error'))
        for current_request_bytes,current_expected_kind in current_test_cases:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(effect_observer,'list_hermes_effect_catalog',return_value={'catalog':True}) as current_catalog_mock, patch.object(effect_observer,'read_hermes_effect_detail',return_value={'detail':True}) as current_detail_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn(current_expected_kind,current_response_record)
                    self.assertEqual(current_catalog_mock.call_count,int(current_expected_kind=='catalog'))
                    self.assertEqual(current_detail_mock.call_count,int(current_expected_kind=='detail'))

    def test_world_map_bridge_only_accepts_fixed_request(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed_value in ((b'world-map\n',True),(b'world-map\nrun shell\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge,'read_hermes_world_map_catalog',return_value={'maps':[]}) as current_catalog_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('maps' if current_allowed_value else 'error',current_response_record)
                    self.assertEqual(current_catalog_mock.call_count,int(current_allowed_value))

    def test_sandbox_world_map_client_sends_selected_map(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"maps":[]}\n'
            self.assertEqual(read_sandbox_management_status('world-map','iseulon'),{'maps':[]})
            current_socket_value.sendall.assert_called_once_with(b'world-map iseulon\n')
        with self.assertRaises(ValueError):
            read_sandbox_management_status('world-map','../outside')

    def test_sandbox_city_map_client_checks_identifier_and_exposes_size_limit(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"map":"stonewarm"}\n'
            self.assertEqual(read_sandbox_management_status('city-map','stonewarm'),{'map':'stonewarm'})
            current_socket_value.sendall.assert_called_once_with(b'city-map stonewarm\n')
            current_socket_value.recv.return_value=(json.dumps({'error':'조회 응답 크기 제한 초과: 원 도구에서 확인하세요.'},ensure_ascii=False)+'\n').encode()
            with self.assertRaisesRegex(ValueError,'크기 제한 초과'):read_sandbox_management_status('city-map','stonewarm')
        with self.assertRaises(ValueError):read_sandbox_management_status('city-map','../outside')

    def test_building_bridge_rejects_duplicate_keys_and_extra_lines(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed_value in ((b'building-catalog {"query":"town"}\n',True),(b'building-catalog {"query":"a","query":"b"}\n',False),(b'building-catalog {}\nrun shell\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch.object(management_bridge,'read_hermes_building_catalog',return_value={'items':[]}) as current_catalog_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('items' if current_allowed_value else 'error',current_response_record)
                    self.assertEqual(current_catalog_mock.call_count,int(current_allowed_value))

    def test_field_region_bridge_accepts_only_fixed_json(self):
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        for current_request_bytes,current_allowed_value in ((b'field-region {"map":"sample"}\n',True),(b'field-region {"map":"a","map":"b"}\n',False),(b'field-region {}\nrun shell\n',False)):
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.hermes_agent.field_map_operations.read_hermes_field_region',return_value={'cells':[]}) as current_region_mock:
                    current_thread_handle=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_handle.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_handle.join(timeout=3)
                    self.assertIn('cells' if current_allowed_value else 'error',current_response_value)
                    self.assertEqual(current_region_mock.call_count,int(current_allowed_value))

    def test_sandbox_field_region_client_uses_fixed_command(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"cells":[]}\n'
            self.assertEqual(read_sandbox_management_status('field-region','{"map":"sample"}'),{'cells':[]})
            current_socket_value.sendall.assert_called_once_with(b'field-region {"map":"sample"}\n')
        with self.assertRaises(ValueError):
            read_sandbox_management_status('field-region','{}\nrun shell')

    def test_sandbox_client_preserves_only_known_error_message(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        for current_error_text,current_expected_text in (('건물 목록 조회 실패: 콘텐츠 서비스 연결을 확인하세요.','콘텐츠 서비스 연결'),('/private/path','거절')):
            current_reply_bytes=(json.dumps({'error':current_error_text},ensure_ascii=False)+'\n').encode('utf-8')
            with self.subTest(reply=current_error_text),patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_factory:
                current_factory.return_value.__enter__.return_value.recv.return_value=current_reply_bytes
                with self.assertRaisesRegex(ValueError,current_expected_text):
                    read_sandbox_management_status('world-map')

    def test_changed_audit_runner_blocks_independent_verification(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            (hermes_job_path / 'request.json').write_text(json.dumps({'prompt':'test', 'verification_modules':['tools.management.tests.test_hermes_service']}))
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_server_mock = Mock()
            hermes_agent_mock = Mock()
            hermes_agent_mock.wait.return_value = 0
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return {'baseline_commit':'a' * 40}
            hermes_previous_directory = os.getcwd()
            try:
                with patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'hash_hermes_verification_controls', side_effect=[{'runner':'before'}, {'runner':'after'}]), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'diff'), patch.object(hermes_worker_module.subprocess, 'Popen', side_effect=[hermes_server_mock, hermes_agent_mock]), patch.object(hermes_worker_module, 'wait_worker_model_ready', return_value='offloaded 1/1 layers to GPU'), patch.object(hermes_worker_module.threading.Thread, 'start'), patch.object(hermes_worker_module, 'execute_hermes_independent_verification') as hermes_verify_mock:
                    with self.assertRaisesRegex(RuntimeError, '실행기가 변경'):
                        hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
                    hermes_verify_mock.assert_not_called()
            finally:
                os.chdir(hermes_previous_directory)
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertEqual(hermes_result_record['verification']['status'], 'failed')
            self.assertTrue(hermes_result_record['partial'])
            current_query_text=(hermes_job_path / 'query.txt').read_text(encoding='utf-8')
            self.assertIn('작업 ID 일부는 query',current_query_text)
            self.assertIn('같은 query와 snapshot',current_query_text)
            self.assertIn('HERMES_WRITER_PROPOSAL',current_query_text)
            self.assertIn('END_HERMES_WRITER_PROPOSAL',current_query_text)
            self.assertIn('사용자가 입력과 GPU 접수를 확인하기 전에는',current_query_text)
            self.assertIn('DB 모드에서는 신규 저장이 중단',current_query_text)
            self.assertIn('도시 맵 신규 저장은 에셋 원본',current_query_text)
            self.assertIn('writer-job-search-paths',current_query_text)

    def test_verification_control_hashes_detect_changes_and_symlinks(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_workspace_path = Path(hermes_temporary_root)
            hermes_control_path = hermes_workspace_path / 'tools/management/tests'
            hermes_control_path.mkdir(parents=True)
            (hermes_control_path / 'run_management_audit.py').write_text('original')
            (hermes_control_path / 'run_music_regression.py').write_text('original')
            hermes_original_hashes = hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path)
            (hermes_control_path / 'run_music_regression.py').write_text('changed')
            self.assertNotEqual(hermes_original_hashes, hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path))
            (hermes_control_path / 'run_music_regression.py').unlink()
            (hermes_control_path / 'run_music_regression.py').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, '심볼릭 링크'):
                hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path)

    def test_verification_failure_marks_agent_output_partial(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            hermes_module_values = ['tools.management.tests.test_hermes_service']
            (hermes_job_path / 'request.json').write_text(json.dumps({'prompt':'test', 'verification_modules':hermes_module_values}))
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_server_mock = Mock()
            hermes_agent_mock = Mock()
            hermes_agent_mock.wait.return_value = 0
            hermes_baseline_record = {'baseline_commit':'a' * 40}
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return hermes_baseline_record
            def fail_mock_verification(*verification_argument_values):
                hermes_server_mock.terminate.assert_called_once()
                return {'status':'failed', 'modules':hermes_module_values, 'exit_code':1}
            hermes_previous_directory = os.getcwd()
            try:
                with patch.dict(os.environ, {'HERMES_PRIVATE_TEST_VALUE':'must-not-inherit', 'SLIME_HERMES_PROCESS_TOKEN':'a' * 32}), patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'hash_hermes_verification_controls', return_value={'runner':'hash'}), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'diff'), patch.object(hermes_worker_module.subprocess, 'Popen', side_effect=[hermes_server_mock, hermes_agent_mock]) as hermes_launch_mock, patch.object(hermes_worker_module, 'wait_worker_model_ready', return_value='offloaded 1/1 layers to GPU'), patch.object(hermes_worker_module.threading.Thread, 'start'), patch.object(hermes_worker_module, 'execute_hermes_independent_verification', side_effect=fail_mock_verification):
                    with self.assertRaisesRegex(RuntimeError, '독립 회귀 검증'):
                        hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
                    self.assertNotIn('HERMES_PRIVATE_TEST_VALUE', hermes_launch_mock.call_args_list[1].kwargs['env'])
                    self.assertNotIn('SLIME_HERMES_PROCESS_TOKEN', hermes_launch_mock.call_args_list[1].kwargs['env'])
            finally:
                os.chdir(hermes_previous_directory)
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertTrue(hermes_result_record['partial'])
            self.assertEqual(hermes_result_record['verification']['status'], 'failed')
            self.assertEqual((hermes_job_path / 'change.diff').read_bytes(), b'diff')

    def test_independent_verifier_reports_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root)
            hermes_module_values = ['tools.management.tests.test_hermes_service']
            with patch.dict(os.environ, {'HERMES_PRIVATE_TEST_VALUE':'must-not-inherit'}), patch.object(hermes_worker_module.subprocess, 'run', return_value=Mock(returncode=1)) as hermes_run_mock:
                hermes_result_record = hermes_worker_module.execute_hermes_independent_verification(hermes_job_path, hermes_job_path, hermes_job_path, hermes_module_values)
                self.assertEqual(hermes_result_record['status'], 'failed')
                self.assertEqual(hermes_run_mock.call_args.args[0][-2:], ['--module', hermes_module_values[0]])
                self.assertNotIn('HERMES_PRIVATE_TEST_VALUE', hermes_run_mock.call_args.kwargs['env'])
            with patch.object(hermes_worker_module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('audit', 300)):
                hermes_timeout_record = hermes_worker_module.execute_hermes_independent_verification(hermes_job_path, hermes_job_path, hermes_job_path, hermes_module_values)
                self.assertEqual(hermes_timeout_record['status'], 'timed_out')
                self.assertIn('시간 초과', (hermes_job_path / 'verification.log').read_text())

    def test_worker_requires_matching_gpu_reservation(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            hermes_reservation_path = Path(hermes_temporary_root) / 'reservation.json'
            hermes_start_token = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
            hermes_process_token = 'a' * 32
            hermes_reservation_path.write_text(json.dumps({'path':str(hermes_job_path), 'service':'hermes-agent', 'worker_pgid':os.getpgrp(), 'worker_start_token':hermes_start_token, 'worker_process_token':hermes_process_token}))
            with patch.dict('os.environ', {'SLIME_GPU_RESERVATION_PATH':str(hermes_reservation_path), 'SLIME_HERMES_PROCESS_TOKEN':hermes_process_token}):
                hermes_worker_module.wait_hermes_gpu_reservation(hermes_job_path)
            with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(RuntimeError, '예약 없이'):
                hermes_worker_module.wait_hermes_gpu_reservation(hermes_job_path)

    def test_runtime_rejects_modified_or_untracked_source(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_runtime_path = Path(hermes_temporary_root)
            subprocess.run(['git', 'init', '-q', str(hermes_runtime_path)], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'config', 'user.email', 'test@localhost'], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'config', 'user.name', 'Test'], check=True)
            (hermes_runtime_path / 'agent.py').write_text('original')
            (hermes_runtime_path / '.gitignore').write_text('.venv/\n')
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'add', 'agent.py', '.gitignore'], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'commit', '-qm', 'initial'], check=True)
            hermes_revision_value = subprocess.check_output(['git', '-C', str(hermes_runtime_path), 'rev-parse', 'HEAD'], text=True).strip()
            (hermes_runtime_path / '.venv/bin').mkdir(parents=True)
            (hermes_runtime_path / '.venv/bin/python').write_text('')
            (hermes_runtime_path / 'prepared-local.json').write_text(json.dumps({'revision':hermes_revision_value, 'release':hermes_runtime_module.HERMES_RUNTIME_RELEASE, 'source':hermes_runtime_module.HERMES_RUNTIME_SOURCE}))
            with patch.object(hermes_runtime_module, 'HERMES_RUNTIME_REVISION', hermes_revision_value):
                hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)
                (hermes_runtime_path / 'agent.py').write_text('changed')
                with self.assertRaisesRegex(ValueError, '소스에 수정'):
                    hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)
                (hermes_runtime_path / 'agent.py').write_text('original')
                (hermes_runtime_path / 'extra.py').write_text('new')
                with self.assertRaisesRegex(ValueError, '소스에 수정'):
                    hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)

    def test_interrupted_model_start_preserves_partial_diff(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            (hermes_job_path / 'request.json').write_text('{"prompt":"test"}')
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_agent_path = Path(hermes_temporary_root) / 'agent'
            (hermes_agent_path / '.venv/bin').mkdir(parents=True)
            (hermes_agent_path / '.venv/bin/python').write_text('')
            hermes_baseline_record = {'baseline_commit':'a' * 40}
            hermes_server_mock = Mock()
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return hermes_baseline_record
            with patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'HERMES_RUNTIME_DIRECTORY', hermes_agent_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'partial diff'), patch.object(hermes_worker_module.subprocess, 'Popen', return_value=hermes_server_mock), patch.object(hermes_worker_module, 'wait_worker_model_ready', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
            self.assertEqual((hermes_job_path / 'change.diff').read_bytes(), b'partial diff')
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertTrue(hermes_result_record['partial'])
            self.assertIsNone(hermes_result_record['agent_exit_code'])
            hermes_server_mock.terminate.assert_called_once()
            hermes_server_mock.wait.assert_called_once()


if __name__ == '__main__':
    unittest.main()
