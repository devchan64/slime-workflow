"""복장 착용 생성기 폐기 계약."""
import tempfile
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from fastapi.testclient import TestClient
from tools.review.common.management_asgi import build_management_application
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command

class OutfitRetirementTests(unittest.TestCase):
    def test_retired_commands_and_mode(self):
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        self.assertNotIn('outfit-transfer', MANAGEMENT_SERVICE_COMMANDS)
        for current_command_name in ('generate', 'resume', 'history', 'history-reset'):
            with self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('outfit-transfer', current_command_name, {})
        with self.assertRaisesRegex(ValueError, '폐기'):
            build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, outfit_transfer_enabled=True)

    def test_retired_routes(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            with patch('tools.review.common.management_asgi.build_management_blocks') as current_builder_mock:
                current_application_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_root_path / 'missing.json', 8770, [])
                with TestClient(current_application_value) as current_test_client:
                    for current_request_path in ('/outfit-transfer/', '/outfit-transfer/jobs', '/management/frame/outfit-transfer-generator/', '/management/?tool=outfit-transfer-generator'):
                        for current_request_method in ('get', 'post'):
                            self.assertEqual(getattr(current_test_client, current_request_method)(current_request_path).status_code, 410)
                current_builder_mock.assert_not_called()
