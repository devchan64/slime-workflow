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

    def test_anny_generation_routes_preserve_legacy_contract(self):
        current_request_calls=[]
        def capture_service_request(current_request_handler):
            current_request_calls.append((current_request_handler.command,current_request_handler.path,json.load(current_request_handler.rfile)))
            return True
        current_gateway_value=ManagementCommandGateway({'anny':capture_service_request})
        for current_command_name,current_route_name in [('anny-preview','preview'),('anny-render','render')]:
            current_payload_record={'rotation_y':25}
            current_gateway_value.handle(self.create_request_handler('/anny-attributes/'+current_route_name,current_payload_record))
            current_gateway_value.handle(self.create_request_handler('/management/command',{'service':'anny','command':current_command_name,'payload':current_payload_record}))
            self.assertEqual(current_request_calls[-2],current_request_calls[-1])
            self.assertEqual(resolve_management_command('anny',current_command_name,current_payload_record),('POST','/anny-attributes/'+current_route_name))

    def test_anny_cli_payload_matches_gui_and_invalid_fields_are_rejected(self):
        import tempfile
        from unittest.mock import patch
        from tools.review.domains.anny.anny_attributes import AnnyAttributeManager
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_input_path=Path(current_directory_name)/'input.json'
            current_input_path.write_text('{"rotation_y":25}')
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'12345678'}) as current_command_mock,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(execute_gateway_cli(['command','anny','anny-preview','--payload-file',str(current_input_path)]),0)
                self.assertEqual(current_command_mock.call_args.args[:3],('anny','anny-preview',{'rotation_y':25}))
        current_gateway_value=ManagementCommandGateway({'anny':AnnyAttributeManager().handle})
        current_default_record={'phenotype_kwargs':{},'local_changes_kwargs':{},'facial_actions':{}}
        with patch('tools.review.domains.anny.anny_attributes.load_attribute_defaults',return_value=current_default_record),patch('tools.review.domains.anny.anny_attributes.launch_gpu_process') as current_launch_mock:
            for current_invalid_payload in ({'unknown':1},{'rotation_y':181},{'rotation_y':True}):
                current_request_handler=self.create_request_handler('/management/command',{'service':'anny','command':'anny-preview','payload':current_invalid_payload})
                current_gateway_value.handle(current_request_handler)
                self.assertEqual(current_request_handler.responses,[400])
            current_launch_mock.assert_not_called()

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
