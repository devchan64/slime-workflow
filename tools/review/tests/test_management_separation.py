"""독립 HTTP 게이트웨이와 GUI의 재시작·보안·명령 전달 계약."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import io
from types import SimpleNamespace
import os
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments
from tools.review.common.management_transport import proxy_management_request, send_management_json_response
from tools.review.gateway_server import create_gateway_request_handler
from tools.review import serve


@contextmanager
def run_test_http_server(request_handler_class):
    with ThreadingHTTPServer(('127.0.0.1', 0), request_handler_class) as current_http_server:
        current_http_server.emit_gateway_trace = lambda *trace_argument_values: None
        current_server_thread = threading.Thread(target=current_http_server.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            yield current_http_server
        finally:
            current_http_server.shutdown()
            current_server_thread.join(timeout=2)


class ManagementSeparationTests(unittest.TestCase):
    def test_gui_restart_keeps_gateway_commands_and_results(self):
        received_command_records = []

        def handle_test_service(current_http_handler):
            request_body_length = int(current_http_handler.headers['Content-Length'])
            received_command_records.append(json.loads(current_http_handler.rfile.read(request_body_length)))
            send_management_json_response(current_http_handler, 202, {'id': 'preserved-job', 'status': 'queued'})
            return True

        management_command_gateway = ManagementCommandGateway({'qwen-2512': handle_test_service})
        with run_test_http_server(create_gateway_request_handler(management_command_gateway.handle)) as gateway_http_server:
            gateway_base_address = f'http://127.0.0.1:{gateway_http_server.server_port}'

            class TestGuiHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    proxy_management_request(self, gateway_base_address)

                def log_message(self, *request_log_arguments):
                    pass

            for restart_attempt_number in range(2):
                with run_test_http_server(TestGuiHandler) as gui_http_server:
                    gui_base_address = f'http://127.0.0.1:{gui_http_server.server_port}'
                    with patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': gui_base_address}):
                        command_result_record = execute_remote_management_command('qwen-2512', 'generate', {'prompt': '잔디'})
                    self.assertEqual(command_result_record['id'], 'preserved-job')
                # GUI 종료 뒤에도 같은 게이트웨이에 CLI/HTTP 접수가 가능하다.
                with patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': gateway_base_address}):
                    self.assertEqual(execute_remote_management_command('qwen-2512', 'generate', {'prompt': '도로'})['status'], 'queued')
            self.assertEqual(received_command_records, [{'prompt': '잔디'}, {'prompt': '도로'}] * 2)

    def test_proxy_rejects_foreign_origin_before_forwarding(self):
        class TestGuiHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                proxy_management_request(self, 'http://127.0.0.1:8771')

            def log_message(self, *request_log_arguments):
                pass

        with run_test_http_server(TestGuiHandler) as gui_http_server:
            request_body_bytes = b'{"service":"qwen-2512","command":"generate","payload":{}}'
            current_http_request = Request(f'http://127.0.0.1:{gui_http_server.server_port}/management/command', data=request_body_bytes,
                                           headers={'Origin': 'http://untrusted.example', 'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as request_error_context:
                urlopen(current_http_request, timeout=2)
            self.assertEqual(request_error_context.exception.code, 400)
            request_error_context.exception.close()

    def test_gui_commands_never_select_local_execution(self):
        with patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': 'http://127.0.0.1:9871'}), patch('tools.review.common.management_client.execute_management_command') as gateway_command_mock:
            execute_remote_management_command('momask', 'history', {})
            gateway_command_mock.assert_called_once_with('momask', 'history', {}, 'http://127.0.0.1:9871')

    def test_cli_uses_gateway_without_gui(self):
        with patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': 'http://127.0.0.1:9871'}), patch('tools.review.common.management_gateway.execute_management_command', return_value=[]) as gateway_command_mock, patch('builtins.print'):
            execute_gateway_arguments('momask', ['history'])
            gateway_command_mock.assert_called_once_with('momask', 'history', {}, 'http://127.0.0.1:9871')

    def test_gui_watch_excludes_runtime_implementation(self):
        parsed_argument_values = serve.parse_review_arguments([])
        watched_root_paths = serve.collect_review_watch_paths(parsed_argument_values)
        runtime_source_paths = [serve.Path(serve.__file__).parent/'gateway_server.py', serve.Path(serve.__file__).parent/'common/management_runtime.py']
        for runtime_source_path in runtime_source_paths:
            self.assertFalse(any(runtime_source_path == watched_root_path or runtime_source_path.is_relative_to(watched_root_path) for watched_root_path in watched_root_paths))

    def test_gateway_failure_does_not_run_local_or_retry(self):
        with patch.dict(os.environ, {'SLIME_MANAGEMENT_GATEWAY_URL': 'http://127.0.0.1:9871'}), patch('tools.review.common.management_gateway.call_management_api', side_effect=ValueError('게이트웨이 종료')) as remote_command_mock, patch('tools.review.common.management_gateway.execute_momask_command') as local_command_mock:
            with self.assertRaisesRegex(ValueError, '게이트웨이 종료'):
                execute_remote_management_command('hy-motion', 'history', {})
            remote_command_mock.assert_called_once()
            local_command_mock.assert_not_called()
