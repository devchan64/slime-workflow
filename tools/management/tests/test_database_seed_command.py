"""최초 시드는 모든 파일 검증 후 한 요청으로 전달한다."""
import unittest
from unittest.mock import patch
from tools.management.domains.map_assets import database_commands


class DatabaseSeedCommandTests(unittest.TestCase):
    def test_deprecated_snapshot_restore_is_blocked_before_read_or_database_request(self):
        from tools.management.common.management_gateway import resolve_management_command
        with patch('tools.management.domains.map_assets.database_restore.read_verified_snapshot_payload') as current_restore_mock, patch.object(database_commands,'execute_content_api_request') as current_api_mock:
            with self.assertRaisesRegex(ValueError,'폐기된 파일 스냅샷'):
                database_commands.execute_content_database_command('database-restore',{'snapshotRoot':'/tmp/old-snapshot'})
            with self.assertRaisesRegex(ValueError,'폐기된 파일 스냅샷'):
                resolve_management_command('map-assets','database-restore',{'snapshotRoot':'/tmp/old-snapshot'})
            current_restore_mock.assert_not_called()
            current_api_mock.assert_not_called()

    def test_ledger_commands_do_not_require_snapshot_directory(current_test_case):
        with patch.dict('os.environ', {}, clear=True), \
                patch.object(database_commands, 'execute_content_snapshot_cycle', return_value={'ledgerSynced': True}) as current_cycle_mock:
            for current_command_name in ('database-sync', 'database-snapshot'):
                current_test_case.assertEqual(database_commands.execute_content_database_command(current_command_name, {}), {'ledgerSynced': True})
            current_test_case.assertEqual(current_cycle_mock.call_count, 2)

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
                patch.object(database_commands, 'load_unique_yaml_document', return_value={'effects': [{'id':'test-effect'}]}), \
                patch.object(database_commands, 'execute_content_api_request', return_value={'generation': 2}) as current_api_mock:
            database_commands.execute_content_database_command('database-seed', {'assetRoot': '/tmp/assets', 'publicAssetPrefix': '/registered-assets'})
            current_api_mock.assert_called_once_with('POST', '/internal/v1/content/seed/bundle',
                {'billboards': {'assets': []}, 'maps': {'documents': {}}, 'effects': [{'id':'test-effect'}]})

    def test_effect_validation_failure_never_submits_bundle(current_test_case):
        with patch.object(database_commands, 'build_billboard_database_seed', return_value={'assets': []}), \
                patch.object(database_commands, 'build_map_database_seed', return_value={'documents': {}}), \
                patch.object(database_commands, 'load_unique_yaml_document', side_effect=ValueError('이펙트 오류')), \
                patch.object(database_commands, 'execute_content_api_request') as current_api_mock:
            with current_test_case.assertRaisesRegex(ValueError, '이펙트 오류'):
                database_commands.execute_content_database_command('database-seed', {'assetRoot':'/tmp/assets','publicAssetPrefix':'/registered-assets'})
            current_api_mock.assert_not_called()
