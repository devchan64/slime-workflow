"""최초 시드는 모든 파일 검증 후 한 요청으로 전달한다."""
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets import database_commands


class DatabaseSeedCommandTests(unittest.TestCase):
    def test_map_validation_failure_never_submits_billboards(self):
        with patch.object(database_commands, 'build_billboard_database_seed', return_value={'assets': []}), \
                patch.object(database_commands, 'build_map_database_seed', side_effect=ValueError('맵 오류')), \
                patch.object(database_commands, 'execute_content_api_request') as current_api_mock:
            with self.assertRaisesRegex(ValueError, '맵 오류'):
                database_commands.execute_content_database_command('database-seed', {'assetRoot': '/tmp/assets', 'publicAssetPrefix': '/registered-assets'})
            current_api_mock.assert_not_called()

    def test_complete_seed_uses_one_atomic_request(self):
        with patch.object(database_commands, 'build_billboard_database_seed', return_value={'assets': []}), \
                patch.object(database_commands, 'build_map_database_seed', return_value={'documents': {}}), \
                patch.object(database_commands, 'execute_content_api_request', return_value={'generation': 2}) as current_api_mock:
            database_commands.execute_content_database_command('database-seed', {'assetRoot': '/tmp/assets', 'publicAssetPrefix': '/registered-assets'})
            current_api_mock.assert_called_once_with('POST', '/internal/v1/content/seed/bundle',
                {'billboards': {'assets': []}, 'maps': {'documents': {}}})
