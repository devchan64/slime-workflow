"""프로필 선택 설정으로 MoMask 화면이 정상 응답하는지 검증한다."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.review.domains.momask.momask_generation import MoMaskGenerationManager


class MoMaskBaselinePageTests(unittest.TestCase):
    def test_retired_page_returns_gone(self):
        manager = MoMaskGenerationManager()
        for route in ('/momask-generator', '/momask-generator/'):
            request = SimpleNamespace(path=route, command='GET',
                headers={'Host': '127.0.0.1:8770'},
                server=SimpleNamespace(server_port=8770))
            with self.subTest(route=route), patch.object(manager, 'send') as response:
                self.assertTrue(manager.handle(request))
                self.assertEqual(response.call_args.args[1], 410)
                self.assertIn('이전 관리 화면은 폐기되었습니다.',response.call_args.args[2]['error'])
