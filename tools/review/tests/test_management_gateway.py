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
