"""폐기한 바닥 타일 생성기는 기존 이력을 제공하고 모든 시드의 신규 접수를 차단한다."""
import unittest

from tools.management.common.management_gateway import resolve_management_command


class FloorSeedControlTests(unittest.TestCase):
    def test_history_available_and_generation_blocked_for_every_seed(self):
        self.assertEqual(resolve_management_command('floor-tile', 'history', {})[0], 'GET')
        for request in ({}, {'seed': 0}, {'seed': 42}, {'seed': 123}):
            with self.subTest(request=request), self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('floor-tile', 'generate', request)
