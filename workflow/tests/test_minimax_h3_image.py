"""H3 Image input, service, and queue contracts without starting GPU work."""
import unittest
from unittest.mock import patch

from generators.minimax_h3_image.contracts import validate_request
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES
from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager


class MiniMaxH3ImageTests(unittest.TestCase):
    def setUp(self):
        self.request = {'action': 'generate', 'prompt': 'a small red house', 'images': [],
                        'width': 1024, 'height': 1024, 'steps': 6, 'seed': 42}

    def test_service_request_and_queue_identity(self):
        manager = MiniMaxH3ImageManager()
        with patch('workflow.domains.minimax_h3_image.generation.inspect_runtime', return_value={'ready': True, 'generation_ready': True}):
            manager.validate_generation_runtime()
        self.assertEqual(manager.validate_generation_request(self.request)['prompt'], self.request['prompt'])
        self.assertEqual(manager.select_generation_service(), 'minimax-h3-image')
        self.assertEqual(manager.job_storage_root.name, 'minimax-h3-image')
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['minimax-h3-image'], '/minimax-h3-image')
        self.assertIn('generate', MANAGEMENT_SERVICE_COMMANDS['minimax-h3-image'])
        self.assertIn('history-delete', MANAGEMENT_SERVICE_COMMANDS['minimax-h3-image'])

    def test_rejects_invalid_or_unsupported_inputs(self):
        for changes in ({'steps': 8}, {'width': 1040}, {'images': ['not-an-image']},
                        {'seed': -1}, {'prompt': '  '}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_request({**self.request, **changes})

    def test_missing_runtime_is_rejected(self):
        manager = MiniMaxH3ImageManager()
        with patch('workflow.domains.minimax_h3_image.generation.inspect_runtime',
                   return_value={'ready': False, 'generation_ready': False, 'message': 'missing'}):
            with self.assertRaisesRegex(ValueError, 'missing'):
                manager.validate_generation_runtime()
