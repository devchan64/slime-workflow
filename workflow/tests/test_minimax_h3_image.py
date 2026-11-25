"""H3 Image input, service, and queue contracts without starting GPU work."""
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from generators.minimax_h3_image.contracts import validate_request, verify_saved_request
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES, ManagementCommandGateway
from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager


class MiniMaxH3ImageTests(unittest.TestCase):
    def setUp(self):
        self.request = {'action': 'generate', 'prompt': 'a small red house', 'images': [],
                        'width': 1024, 'height': 1024, 'steps': 6, 'seed': 42}

    def test_service_request_and_queue_identity(self):
        manager = MiniMaxH3ImageManager()
        with patch('workflow.domains.minimax_h3_image.generation.inspect_runtime', return_value={'ready': True, 'generation_ready': True}):
            manager.validate_generation_runtime()
        result = manager.validate_generation_request(self.request)
        self.assertEqual(result['user_prompt'], self.request['prompt'])
        self.assertIn(result['common_style']['prompt'], result['prompt'])
        verify_saved_request(result)
        self.assertEqual(manager.select_generation_service(), 'minimax-h3-image')
        self.assertEqual(manager.job_storage_root.name, 'minimax-h3-image')
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['minimax-h3-image'], '/minimax-h3-image')
        self.assertIn('generate', MANAGEMENT_SERVICE_COMMANDS['minimax-h3-image'])
        self.assertIn('history-delete', MANAGEMENT_SERVICE_COMMANDS['minimax-h3-image'])

    def test_rejects_invalid_or_unsupported_inputs(self):
        result = validate_request({**self.request, 'width': 512, 'height': 512})
        self.assertEqual((result['width'], result['height']), (512, 512))
        verify_saved_request(result)
        landscape = validate_request({**self.request, 'width': 832, 'height': 480})
        self.assertEqual((landscape['width'], landscape['height']), (832, 480))
        for changes in ({'steps': 8}, {'width': 1040}, {'width': 448}, {'images': ['not-an-image']},
                        {'seed': -1}, {'prompt': '  '}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_request({**self.request, **changes})

    def test_missing_runtime_is_rejected(self):
        manager = MiniMaxH3ImageManager()
        with patch('workflow.domains.minimax_h3_image.generation.inspect_runtime',
                   return_value={'ready': False, 'generation_ready': False, 'message': 'missing'}):
            with self.assertRaisesRegex(ValueError, 'missing'):
                manager.validate_generation_runtime()

    def test_preview_hash_locks_composition_and_saved_snapshot(self):
        result = validate_request(self.request)
        self.assertEqual(validate_request({**self.request, 'expected_prompt_sha256': result['prompt_sha256']})['prompt'], result['prompt'])
        with self.assertRaisesRegex(ValueError, '다시 검토'):
            validate_request({**self.request, 'expected_prompt_sha256': '0' * 64})
        with self.assertRaises(ValueError):
            verify_saved_request({**result, 'prompt': result['prompt'] + ' changed'})

    def test_existing_style_is_not_duplicated(self):
        first = validate_request(self.request)
        second = validate_request({**self.request, 'prompt': first['prompt']})
        self.assertEqual(second['prompt'], first['prompt'])
        self.assertTrue(second['common_style']['already_present'])
        verify_saved_request(second)

    def test_preview_through_gateway_matches_submitted_prompt(self):
        payload = json.dumps({'service': 'minimax-h3-image', 'command': 'preview', 'payload': self.request}).encode()
        handler = SimpleNamespace(path='/management/command', command='POST',
            headers={'Host': '127.0.0.1:8770', 'Origin': 'http://127.0.0.1:8770',
                     'Content-Type': 'application/json', 'Content-Length': str(len(payload))},
            server=SimpleNamespace(server_port=8770), rfile=io.BytesIO(payload), wfile=io.BytesIO(), responses=[])
        handler.send_response = handler.responses.append
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        manager = MiniMaxH3ImageManager()
        ManagementCommandGateway({'minimax-h3-image': manager.handle_image_request}).handle(handler)
        self.assertEqual(handler.responses, [200])
        preview = json.loads(handler.wfile.getvalue())
        saved = manager.validate_generation_request({**self.request, 'expected_prompt_sha256': preview['prompt_sha256']})
        self.assertEqual(preview['prompt'], saved['prompt'])
