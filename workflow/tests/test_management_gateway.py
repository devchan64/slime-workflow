"""브라우저 호환 요청과 CLI 명령 봉투가 같은 서비스로 연결되는지 검증."""
import contextlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str((Path(__file__).resolve().parents[2] / 'tools')))
from workflow.common.management_gateway import ManagementCommandGateway, resolve_management_command, execute_gateway_cli, MANAGEMENT_SERVICE_COMMANDS


class GatewayContractTest(unittest.TestCase):
    def test_http_error_response_is_closed_and_bounded(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        from workflow.common.management_gateway import call_management_api
        for current_response_bytes,current_expected_text in ((b'{"error":"rejected"}','rejected'),(b'x'*17000,'오류 응답 일부만 표시'),(b'[]','[]')):
            with self.subTest(response=current_response_bytes[:20]):
                current_error_stream=io.BytesIO(current_response_bytes)
                current_http_error=HTTPError('http://127.0.0.1',400,'Bad Request',{},current_error_stream)
                with patch('urllib.request.urlopen',side_effect=current_http_error):
                    with self.assertRaises(ValueError) as current_exception_context:
                        call_management_api('http://127.0.0.1:8771','/wan22-fun-control/jobs',{'action':'prepare'})
                self.assertIn(current_expected_text,str(current_exception_context.exception))
                self.assertLess(len(str(current_exception_context.exception)),16200)
                self.assertTrue(current_error_stream.closed)

    def test_model_cli_reuses_registered_service_operations(self):
        with contextlib.redirect_stdout(io.StringIO()) as model_list_stream:
            self.assertEqual(execute_gateway_cli(['model', 'list']), 0)
        current_model_list = json.loads(model_list_stream.getvalue())
        self.assertEqual(current_model_list['hermes-model']['prepare'], 'prepare')
        self.assertEqual(current_model_list['music-heartmula']['prepare'], 'download-model')
        self.assertEqual(current_model_list['dwpose']['prepare'], 'prepare')
        self.assertEqual(current_model_list['flux-image']['prepare'], 'prepare')
        self.assertTrue(current_model_list['qwen-21']['qwen_archived'])
        self.assertIsNone(current_model_list['qwen-21']['prepare'])
        self.assertIsNone(current_model_list['qwen-2511']['status'])
        self.assertIsNone(current_model_list['expression-lora']['prepare'])
        self.assertTrue(current_model_list['floor-tile']['retired'])
        for current_service_name, current_model_record in current_model_list.items():
            for current_action_name in ('status', 'prepare'):
                current_operation_name = current_model_record[current_action_name]
                if current_operation_name is not None:
                    current_payload_value = {'action':'prepare'} if current_operation_name == 'prepare' else {}
                    resolve_management_command(current_service_name, current_operation_name, current_payload_value)
        for current_retired_name in ('music-minimax', 'music-magenta'):
            self.assertTrue(current_model_list[current_retired_name]['retired'])
            self.assertIsNone(current_model_list[current_retired_name]['prepare'])
        with patch('workflow.common.management_gateway.execute_gateway_arguments', return_value=7) as gateway_arguments_mock:
            self.assertEqual(execute_gateway_cli(['model', 'prepare', 'music-heartmula']), 7)
            gateway_arguments_mock.assert_called_once_with('music-heartmula', ['download-model'])
        with patch('workflow.common.management_gateway.execute_gateway_arguments', return_value=0) as gateway_arguments_mock:
            self.assertEqual(execute_gateway_cli(['model', 'status', 'hermes-model', '--server-url', 'http://127.0.0.1:8771']), 0)
            gateway_arguments_mock.assert_called_once_with('hermes-model', ['--server-url', 'http://127.0.0.1:8771', 'model-status'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_cli(['model', 'prepare', 'not-a-service'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_cli(['model', 'prepare', 'qwen-21'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_cli(['model', 'prepare', 'music-minimax'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_cli(['model', 'prepare', 'expression-lora'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_cli(['model', 'status', 'qwen-2511'])

    def test_help_describes_retired_services_consistently_with_policy(self):
        from workflow.common.management_gateway import ARCHIVED_QWEN_IMAGE_SERVICES, inspect_management_policy_rejection
        with contextlib.redirect_stdout(io.StringIO()) as current_help_output:
            self.assertEqual(execute_gateway_cli(['help']),0)
        current_help_lines=current_help_output.getvalue().splitlines()
        for current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES:
            current_matching_lines=[current_line for current_line in current_help_lines if current_line.strip().startswith(current_service_name+':')]
            self.assertEqual(len(current_matching_lines),1)
            self.assertIn('아카이브',current_matching_lines[0])
            for current_command_name in ('generate','resume','prepare'):
                self.assertIsNotNone(inspect_management_policy_rejection(current_service_name,current_command_name))
        current_qwen_line=next(current_line for current_line in current_help_lines if current_line.strip().startswith('qwen-2511:'))
        self.assertIn('폐기',current_qwen_line)
        self.assertIsNotNone(inspect_management_policy_rejection('qwen-2511','status'))
        current_lora_line=next(current_line for current_line in current_help_lines if current_line.strip().startswith('expression-lora:'))
        self.assertIn('다운로드 중단',current_lora_line)
        self.assertIsNotNone(inspect_management_policy_rejection('expression-lora','prepare'))

    def test_gateway_health_identifies_current_launch(self):
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        from workflow.gateway_server import create_gateway_request_handler
        with patch.dict(os.environ, {'SLIME_MANAGEMENT_STACK_TOKEN':'fixture-token'}):
            current_gateway_server = ThreadingHTTPServer(('127.0.0.1', 0), create_gateway_request_handler(lambda current_handler: False))
            current_gateway_server.emit_gateway_trace = lambda *current_trace_values: None
            current_gateway_thread = threading.Thread(target=current_gateway_server.serve_forever, daemon=True)
            current_gateway_thread.start()
            try:
                with urlopen(f'http://127.0.0.1:{current_gateway_server.server_port}/management/health', timeout=5) as current_health_response:
                    current_health_record = json.load(current_health_response)
                self.assertEqual(current_health_record['role'], 'management-gateway')
                self.assertEqual(current_health_record['launch_token'], 'fixture-token')
                self.assertIn('hermes-gpu-queue-v1',current_health_record['features'])
                from workflow.common.management_stack import wait_management_stack_endpoint
                current_process_handle=SimpleNamespace(poll=lambda:None)
                with patch('workflow.common.gpu_status.read_gpu_status',side_effect=AssertionError('GPU 조회 금지')) as current_gpu_mock:
                    wait_management_stack_endpoint(current_process_handle,f'http://127.0.0.1:{current_gateway_server.server_port}/management/health','management-gateway','fixture-token',Path('/tmp/unused-health.log'))
                    current_gpu_mock.assert_not_called()
            finally:
                current_gateway_server.shutdown()
                current_gateway_thread.join(timeout=5)
                current_gateway_server.server_close()

    def test_gpu_queue_observation_failure_returns_explicit_503(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.error import HTTPError
        from urllib.request import urlopen
        from workflow.gateway_server import create_gateway_request_handler
        current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(lambda current_handler:False))
        current_server_value.emit_gateway_trace=lambda *current_values:None
        current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_thread_value.start()
        try:
            with patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',side_effect=ValueError('private path')) as current_queue_mock:
                with self.assertRaises(HTTPError) as current_error:
                    urlopen(f'http://127.0.0.1:{current_server_value.server_port}/management/gpu-queue',timeout=5)
                with current_error.exception as current_error_response:
                    self.assertEqual(current_error_response.code,503)
                    self.assertEqual(json.loads(current_error_response.read()),{'error':'GPU 대기열을 확인할 수 없습니다.'})
                current_queue_mock.assert_called_once_with(observation_limits=True)
        finally:
            current_server_value.shutdown()
            current_thread_value.join(timeout=5)
            current_server_value.server_close()

    def test_loopback_hosts_require_matching_origin(self):
        from workflow.common.management_environment import validate_gateway_address
        from workflow.common.management_transport import validate_management_http_request
        for current_host_name in ('127.0.0.1', 'localhost'):
            with self.subTest(host=current_host_name):
                current_server_address = f'http://{current_host_name}:8770'
                self.assertEqual(validate_gateway_address(current_server_address), current_server_address)
                current_request_handler = self.create_request_handler('/management/command', {})
                current_request_handler.headers['Host'] = f'{current_host_name}:8770'
                current_request_handler.headers['Origin'] = current_server_address
                self.assertEqual(validate_management_http_request(current_request_handler), 2)
                current_request_handler.headers['Origin'] = 'http://other.example:8770'
                with self.assertRaises(ValueError):
                    validate_management_http_request(current_request_handler)
                current_other_host = 'localhost' if current_host_name == '127.0.0.1' else '127.0.0.1'
                current_request_handler.headers['Origin'] = f'http://{current_other_host}:8770'
                with self.assertRaises(ValueError):
                    validate_management_http_request(current_request_handler)
        with self.assertRaises(ValueError):
            validate_gateway_address('http://example.com:8770')

    def test_connection_failure_diagnostic(self):
        from unittest.mock import patch
        from urllib.error import URLError
        from workflow.common.management_gateway import call_management_api
        for current_failure_error in (URLError(ConnectionRefusedError(111, 'Connection refused')), TimeoutError('timed out')):
            current_error_output = io.StringIO()
            with self.subTest(error=type(current_failure_error).__name__):
                with patch('urllib.request.urlopen', side_effect=current_failure_error) as current_request_mock:
                    with contextlib.redirect_stderr(current_error_output), self.assertRaisesRegex(ValueError, '게이트웨이 연결 실패'):
                        call_management_api('http://127.0.0.1:8771', '/wan22-fun-control/jobs', {'prompt':'private-prompt'})
                    self.assertEqual(current_request_mock.call_count, 1)
                current_logged_record = current_error_output.getvalue()
                self.assertIn('/management-client/connection-failed', current_logged_record)
                self.assertIn('wan22-fun-control', current_logged_record)
                self.assertIn('elapsed_seconds', current_logged_record)
                self.assertNotIn('private-prompt', current_logged_record)

    def test_retired_stretch_cli_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as command_exit_context:
            execute_gateway_cli(['command','momask','generate','--action','stretch'])
        self.assertEqual(command_exit_context.exception.code,2)

    def test_retired_qwen_2512_service_is_unavailable(self):
        for current_command_name in ('generate', 'prepare', 'resume', 'model-status', 'history', 'status'):
            with self.subTest(command=current_command_name), self.assertRaises(ValueError):
                resolve_management_command('qwen-2512', current_command_name, {})

    def create_request_handler(self,path,body,origin='http://127.0.0.1:8770'):
        data=json.dumps(body).encode()
        handler=SimpleNamespace(path=path,command='POST',headers={'Host':'127.0.0.1:8770','Origin':origin,'Content-Type':'application/json','Content-Length':str(len(data))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(data),wfile=io.BytesIO(),responses=[])
        handler.send_response=handler.responses.append
        handler.send_header=lambda *args:None
        handler.end_headers=lambda:None
        return handler

    def test_nonfinite_json_is_rejected_before_service(self):
        from workflow.common.management_gateway import parse_management_request_json
        current_service_calls=[]
        current_gateway_value=ManagementCommandGateway({'qwen-21':lambda current_request_handler:current_service_calls.append(current_request_handler)})
        for current_invalid_value in (float('nan'),float('inf'),float('-inf')):
            for current_request_path in ('/management/command','/image-generation-21/jobs'):
                current_payload_record={'seed':current_invalid_value}
                current_request_record={'service':'qwen-21','command':'generate','payload':current_payload_record} if current_request_path=='/management/command' else current_payload_record
                current_request_handler=self.create_request_handler(current_request_path,current_request_record)
                current_gateway_value.handle(current_request_handler)
                self.assertEqual(current_request_handler.responses,[400])
                self.assertIn('유한한',json.loads(current_request_handler.wfile.getvalue())['error'])
        self.assertEqual(current_service_calls,[])
        for current_invalid_text in ('{"nested":{"seed":1,"seed":2}}','{"nested":[NaN]}','{"seed":1e999}','{"seed":-1e999}'):
            with self.assertRaises(ValueError):
                parse_management_request_json(current_invalid_text)
        self.assertEqual(parse_management_request_json('{"nested":[0.25,12]}'),{'nested':[0.25,12]})

    def test_http_client_rejects_nonfinite_payload_before_network(self):
        from unittest.mock import patch
        from workflow.common.management_gateway import call_management_api
        for current_invalid_number in (float('nan'),float('inf'),float('-inf')):
            with patch('workflow.common.management_gateway.urllib.request.urlopen') as current_transport_mock:
                with self.assertRaises(ValueError):
                    call_management_api('http://127.0.0.1:8771','/image-generation/jobs',{'nested':[current_invalid_number]})
                current_transport_mock.assert_not_called()

    def test_cli_rejects_invalid_json_before_dispatch(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_input_path=Path(current_directory_name)/'input.json'
            for current_invalid_text in ('{"rotation_y":NaN}','{"rotation_y":1e999}','{"rotation_y":1,"rotation_y":2}'):
                current_input_path.write_text(current_invalid_text)
                with patch('workflow.common.management_gateway.execute_management_command') as current_dispatch_mock:
                    with self.assertRaises(ValueError):
                        execute_gateway_cli(['command','map-assets','asset-list','--payload-file',str(current_input_path)])
                    current_dispatch_mock.assert_not_called()

    def test_cli_help_matches_gateway_commands(self):
        for service_name_value,command_name_values in MANAGEMENT_SERVICE_COMMANDS.items():
            for command_name_value in command_name_values:
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as command_exit_context:
                    execute_gateway_cli(['help',service_name_value,command_name_value])
                self.assertEqual(command_exit_context.exception.code,0)

    @patch('workflow.common.management_gateway.ARCHIVED_QWEN_IMAGE_SERVICES', frozenset())
    def test_gui_and_cli_reach_same_operation(self):
        calls=[]
        def backend_handler(request):
            calls.append((request.command,request.path,json.load(request.rfile)))
            return True
        gateway=ManagementCommandGateway({'qwen-21':backend_handler})
        payload={'action':'generate','prompt':'test','steps':4,'width':512,'height':512,'seed':1}
        gateway.handle(self.create_request_handler('/image-generation-21/jobs',payload))
        gateway.handle(self.create_request_handler('/management/command',{'service':'qwen-21','command':'generate','payload':payload}))
        self.assertEqual(calls[0],calls[1])



    def test_retired_momask_command_is_rejected_before_service(self):
        import tempfile
        from unittest.mock import patch
        from workflow.common.retired_momask import RetiredMoMaskHandler as MoMaskGenerationManager
        current_job_identifier='2026-10-08_00-00-00-12345678'
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_root_path=Path(current_temporary_path)
            current_job_path=current_root_path/'jobs'/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_history_path=current_root_path/'history'
            current_history_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            current_history_file=current_history_path/(current_job_identifier+'.json')
            current_history_file.write_text('{}')
            current_gateway_value=ManagementCommandGateway({'momask':MoMaskGenerationManager().handle})
            current_request_value=self.create_request_handler('/management/command',{'service':'momask','command':'history-delete','payload':{'id':current_job_identifier}})
            current_gateway_value.handle(current_request_value)
            self.assertEqual(current_request_value.responses,[400])
            self.assertTrue(current_history_file.exists())
            self.assertTrue(current_job_path.exists())
            self.assertIn('폐기',json.loads(current_request_value.wfile.getvalue())['error'])

    @patch('workflow.common.management_gateway.ARCHIVED_QWEN_IMAGE_SERVICES', frozenset())
    def test_circular_invalid_prompt_returns_client_error_without_launch(self):
        from unittest.mock import patch
        from workflow.domains.image.qwen_circular_generation import QwenCircularGenerationManager
        current_service_manager = QwenCircularGenerationManager()
        current_gateway_value = ManagementCommandGateway({'qwen-21-circular': current_service_manager.handle_image_request})
        with patch.object(current_service_manager, 'validate_generation_runtime', side_effect=AssertionError('잘못된 입력이 실행 단계에 도달함')) as current_runtime_mock:
            for current_invalid_prompt in (None, 1, [], {}):
                for current_request_path in ('/management/command', '/image-generation-21-circular/jobs'):
                    current_payload_record = {'action': 'generate', 'prompt': current_invalid_prompt, 'images': [], 'steps': 40, 'width': 512, 'height': 512, 'seed': 42}
                    current_request_body = {'service': 'qwen-21-circular', 'command': 'generate', 'payload': current_payload_record} if current_request_path == '/management/command' else current_payload_record
                    current_request_handler = self.create_request_handler(current_request_path, current_request_body)
                    current_gateway_value.handle(current_request_handler)
                    self.assertEqual(current_request_handler.responses, [400])
                    self.assertIn('프롬프트는 문자열', json.loads(current_request_handler.wfile.getvalue())['error'])
            current_runtime_mock.assert_not_called()

    def test_invalid_origin_does_not_dispatch(self):
        gateway=ManagementCommandGateway({})
        handler=self.create_request_handler('/management/command',{'service':'momask','command':'history','payload':{}},'http://evil.example')
        gateway.handle(handler)
        self.assertEqual(handler.responses,[400])

    def test_unsupported_commands_and_traversal(self):
        for service,command,payload in [('qwen-2511','prepare',{}),('shell','run',{}),('momask','status',{'id':'../secret'})]:
            with self.assertRaises(ValueError):resolve_management_command(service,command,payload)

    def test_asset_requests_bypass_command_gateway(self):
        gateway=ManagementCommandGateway({})
        request=SimpleNamespace(path='/image-generation/jobs/2026-09-24_23-01-01-12345678/result.png',command='GET')
        self.assertFalse(gateway.handle(request))


if __name__=='__main__':unittest.main()


class RemovedWan21ServiceTests(unittest.TestCase):
    def test_removed_services_reject_all_commands(self):
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, resolve_management_command
        for current_service_name in ('wan21-vace', 'wan21-vace-v2v', 'wan21-vace-f2v', 'wan21-vace-fl2v', 'phantom'):
            self.assertNotIn(current_service_name, MANAGEMENT_SERVICE_ROUTES)
            with self.assertRaises(ValueError):
                resolve_management_command(current_service_name, 'generate', {})
