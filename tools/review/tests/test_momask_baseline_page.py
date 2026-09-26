"""프로필 선택 설정으로 MoMask 화면이 정상 응답하는지 검증한다."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.review.domains.momask.momask_generation import MoMaskGenerationManager


class MoMaskBaselinePageTests(unittest.TestCase):
    def test_page_displays_active_profile(self):
        manager = MoMaskGenerationManager()
        for route in ('/momask-generator', '/momask-generator/'):
            request = SimpleNamespace(path=route, command='GET',
                headers={'Host': '127.0.0.1:8770'},
                server=SimpleNamespace(server_port=8770))
            with self.subTest(route=route), patch.object(manager, 'send') as response:
                self.assertTrue(manager.handle(request))
                self.assertEqual(response.call_args.args[1], 200)
                page = response.call_args.args[2].decode()
                self.assertIn('새 생성 기준 모델: 중성형 v4', page)
                self.assertNotIn('__ANNY_BASELINE_MODEL__', page)
                self.assertNotIn('ANNY 쇄골·어깨 적용 방식', page)
