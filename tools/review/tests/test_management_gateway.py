"""브라우저 호환 요청과 CLI 명령 봉투가 같은 서비스로 연결되는지 검증."""
import contextlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.common.management_gateway import ManagementCommandGateway, resolve_management_command, execute_gateway_cli, MANAGEMENT_SERVICE_COMMANDS


class GatewayContractTest(unittest.TestCase):
    def test_retired_stretch_cli_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as command_exit_context:
            execute_gateway_cli(['command','momask','generate','--action','stretch'])
        self.assertEqual(command_exit_context.exception.code,2)

    def create_request_handler(self,path,body,origin='http://127.0.0.1:8770'):
        data=json.dumps(body).encode()
        handler=SimpleNamespace(path=path,command='POST',headers={'Host':'127.0.0.1:8770','Origin':origin,'Content-Type':'application/json','Content-Length':str(len(data))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(data),wfile=io.BytesIO(),responses=[])
        handler.send_response=handler.responses.append
        handler.send_header=lambda *args:None
        handler.end_headers=lambda:None
        return handler

    def test_nonfinite_json_is_rejected_before_service(self):
        from tools.review.common.management_gateway import parse_management_request_json
        current_service_calls=[]
        current_gateway_value=ManagementCommandGateway({'qwen-2512':lambda current_request_handler:current_service_calls.append(current_request_handler)})
        for current_invalid_value in (float('nan'),float('inf'),float('-inf')):
            for current_request_path in ('/management/command','/image-generation/jobs'):
                current_payload_record={'seed':current_invalid_value}
                current_request_record={'service':'qwen-2512','command':'generate','payload':current_payload_record} if current_request_path=='/management/command' else current_payload_record
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
        from tools.review.common.management_gateway import call_management_api
        for current_invalid_number in (float('nan'),float('inf'),float('-inf')):
            with patch('tools.review.common.management_gateway.urllib.request.urlopen') as current_transport_mock:
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
                with patch('tools.review.common.management_gateway.execute_management_command') as current_dispatch_mock:
                    with self.assertRaises(ValueError):
                        execute_gateway_cli(['command','map-assets','asset-list','--payload-file',str(current_input_path)])
                    current_dispatch_mock.assert_not_called()

    def test_cli_help_matches_gateway_commands(self):
        for service_name_value,command_name_values in MANAGEMENT_SERVICE_COMMANDS.items():
            for command_name_value in command_name_values:
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as command_exit_context:
                    execute_gateway_cli(['help',service_name_value,command_name_value])
                self.assertEqual(command_exit_context.exception.code,0)

    def test_gui_and_cli_reach_same_operation(self):
        calls=[]
        def backend_handler(request):
            calls.append((request.command,request.path,json.load(request.rfile)))
            return True
        gateway=ManagementCommandGateway({'qwen-2512':backend_handler})
        payload={'action':'generate','prompt':'test','steps':4,'width':512,'height':512,'seed':1}
        gateway.handle(self.create_request_handler('/image-generation/jobs',payload))
        gateway.handle(self.create_request_handler('/management/command',{'service':'qwen-2512','command':'generate','payload':payload}))
        self.assertEqual(calls[0],calls[1])



    def test_retired_momask_command_is_rejected_before_service(self):
        import tempfile
        from unittest.mock import patch
        from tools.review.common.retired_momask import RetiredMoMaskHandler as MoMaskGenerationManager
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

    def test_circular_invalid_prompt_returns_client_error_without_launch(self):
        from unittest.mock import patch
        from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
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
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, resolve_management_command
        for current_service_name in ('wan21-vace', 'wan21-vace-v2v', 'wan21-vace-f2v', 'wan21-vace-fl2v', 'phantom'):
            self.assertNotIn(current_service_name, MANAGEMENT_SERVICE_ROUTES)
            with self.assertRaises(ValueError):
                resolve_management_command(current_service_name, 'generate', {})
