import unittest
import io
import json
from types import SimpleNamespace

from tools.review.common.management_gateway import (
    ARCHIVED_QWEN_IMAGE_SERVICES,
    ManagementCommandGateway,
    resolve_management_command,
)


class QwenArchivePolicyTests(unittest.TestCase):
    def test_archived_services_reject_new_or_restarted_work(self):
        for current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES:
            for current_operation_name in ('generate', 'resume', 'prioritize', 'prepare'):
                with self.subTest(service=current_service_name, operation=current_operation_name):
                    with self.assertRaisesRegex(ValueError, '아카이브'):
                        resolve_management_command(current_service_name, current_operation_name, {})

    def test_archived_services_keep_history_and_status_access(self):
        for current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES:
            for current_operation_name in ('history', 'active', 'model-status'):
                with self.subTest(service=current_service_name, operation=current_operation_name):
                    current_method_name, current_route_path = resolve_management_command(
                        current_service_name, current_operation_name, {})
                    self.assertEqual(current_method_name, 'GET')
                    self.assertTrue(current_route_path.startswith('/'))

    def test_unrelated_generation_remains_available(self):
        self.assertEqual(resolve_management_command('kimodo', 'generate', {})[0], 'POST')

    def test_expression_adapter_download_is_retired(self):
        with self.assertRaisesRegex(ValueError, '라이선스'):
            resolve_management_command('expression-lora', 'prepare', {'action': 'prepare'})

    def test_legacy_and_enveloped_requests_cannot_start_archived_work(self):
        current_service_calls = []
        current_gateway_value = ManagementCommandGateway({'qwen-21': lambda current_handler: current_service_calls.append(current_handler)})
        for current_path_name, current_body_record in (
            ('/image-generation-21/jobs', {'action': 'generate'}),
            ('/management/command', {'service': 'qwen-21', 'command': 'generate', 'payload': {'action': 'generate'}}),
        ):
            current_body_bytes = json.dumps(current_body_record).encode()
            current_handler = SimpleNamespace(path=current_path_name, command='POST',
                headers={'Host': '127.0.0.1:8770', 'Origin': 'http://127.0.0.1:8770', 'Content-Type': 'application/json', 'Content-Length': str(len(current_body_bytes))},
                server=SimpleNamespace(server_port=8770), rfile=io.BytesIO(current_body_bytes), wfile=io.BytesIO(), responses=[])
            current_handler.send_response = current_handler.responses.append
            current_handler.send_header = lambda *current_values: None
            current_handler.end_headers = lambda: None
            current_gateway_value.handle(current_handler)
            self.assertEqual(current_handler.responses, [400])
            self.assertIn('아카이브', json.loads(current_handler.wfile.getvalue())['error'])
        self.assertEqual(current_service_calls, [])


if __name__ == '__main__':
    unittest.main()
