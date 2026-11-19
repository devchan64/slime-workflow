"""원장 반영 성공 전 DB 완료를 기록하지 않는 계약."""
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.database_snapshot import execute_content_snapshot_cycle, encode_content_snapshot_payload


class ContentLedgerSyncTests(unittest.TestCase):
    def test_sync_distinguishes_publication_and_completion_failures(self):
        from pathlib import Path
        current_payload={'generation':4}
        current_export={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload,'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_root,patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_root}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export,OSError('fail unavailable')]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',side_effect=ValueError('맵 해시 불일치')):
            with self.assertRaisesRegex(RuntimeError,'맵 해시 불일치'):
                execute_content_snapshot_cycle(current_root)
            self.assertTrue(current_api_mock.call_args_list[-1].args[1].endswith('/fail'))
            self.assertFalse((Path(current_root)/'.local/content-ledger/synced.yaml').exists())
        with tempfile.TemporaryDirectory() as current_root,patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_root}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export,OSError('lost')]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':4,'updatedFiles':1}):
            with self.assertRaisesRegex(RuntimeError,'파일 원장은 반영됐으나'):
                execute_content_snapshot_cycle(current_root)
            self.assertTrue(current_api_mock.call_args_list[-1].args[1].endswith('/complete'))
            self.assertFalse((Path(current_root)/'.local/content-ledger/synced.yaml').exists())

    def test_wrong_publication_generation_never_marks_database_complete(self):
        current_payload={'generation':4}
        current_export={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload,'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_root,patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_root}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export,{}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':5,'updatedFiles':1}):
            with self.assertRaisesRegex(ValueError,'반영 세대'):
                execute_content_snapshot_cycle(current_root)
            self.assertTrue(current_api_mock.call_args_list[-1].args[1].endswith('/fail'))

    def test_invalid_export_identity_is_rejected_before_publication(self):
        current_valid_export={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':{'generation':4},'payloadHash':'a'*64}
        for current_bad_export in ({**current_valid_export,'runId':'../../wrong'}, {**current_valid_export,'payloadHash':'bad'},
                {**current_valid_export,'payload':{'generation':True}}, {'needed':False,'generation':True}, {'needed':'yes'}):
            with self.subTest(export=current_bad_export),tempfile.TemporaryDirectory() as current_root,patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_root}), \
                    patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',return_value=current_bad_export) as current_api_mock, \
                    patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger') as current_publish_mock:
                with self.assertRaises(ValueError):execute_content_snapshot_cycle(current_root)
                current_publish_mock.assert_not_called()
                self.assertEqual(current_api_mock.call_count,1)

    def test_completion_response_must_match_published_generation(self):
        from pathlib import Path
        current_payload={'generation':4}
        current_export={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload,'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload)).hexdigest()}
        for current_completion in ({'completed':False,'generation':4},{'completed':True,'generation':5},{'completed':True,'generation':True},{}):
            with self.subTest(completion=current_completion),tempfile.TemporaryDirectory() as current_root,patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_root}), \
                    patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export,current_completion]) as current_api_mock, \
                    patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':4,'updatedFiles':1}):
                with self.assertRaisesRegex(ValueError,'완료 응답'):
                    execute_content_snapshot_cycle(current_root)
                self.assertFalse((Path(current_root)/'.local/content-ledger/synced.yaml').exists())
                self.assertEqual(current_api_mock.call_count,2)

    def test_existing_receipt_rechecks_map_sources(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',return_value={'needed':False,'generation':4}) as current_api_mock, \
                patch('tools.review.domains.map_assets.source_consistency.inspect_hermes_map_sources',return_value={'status':'mismatch'}):
            current_receipt_path=Path(current_directory_name)/'.local/content-ledger/synced.yaml'
            current_receipt_path.parent.mkdir(parents=True)
            current_receipt_path.write_text('generation: 4\n')
            with self.assertRaisesRegex(ValueError,'일치를 확인할 수 없습니다'):
                execute_content_snapshot_cycle(current_directory_name)
            self.assertEqual(current_api_mock.call_count,1)

    def test_ledger_failure_never_marks_complete(self):
        current_payload_record={'generation':4}
        current_export_record={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload_record,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export_record,{}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',side_effect=ValueError('원장 오류')):
            with self.assertRaisesRegex(ValueError,'원장 오류'):
                execute_content_snapshot_cycle(current_directory_name)
            self.assertTrue(current_api_mock.call_args_list[-1].args[1].endswith('/fail'))

    def test_sync_writes_ledger_without_generation_bundle(self):
        current_payload_record={'generation':4}
        current_export_record={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload_record,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export_record,{'completed':True,'generation':4}, {'needed':False,'generation':4}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':4,'updatedFiles':3}) as current_ledger_mock, \
                patch('tools.review.domains.map_assets.source_consistency.inspect_hermes_map_sources',return_value={'status':'matched'}), \
                patch('tools.review.domains.map_assets.database_snapshot.publish_content_snapshot_bundle') as current_bundle_mock:
            self.assertTrue(execute_content_snapshot_cycle(current_directory_name)['ledgerSynced'])
            self.assertTrue(execute_content_snapshot_cycle(current_directory_name)['ledgerSynced'])
            current_bundle_mock.assert_not_called()
            current_ledger_mock.assert_called_once()
            self.assertTrue(current_api_mock.call_args_list[1].args[1].endswith('/complete'))

    def test_missing_receipt_replays_current_database_without_backup(current_test_case):
        current_payload_record={'generation':4}
        current_export_record={'needed':True,'runId':'12345678-1234-4234-8234-123456789abc','payload':current_payload_record,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[{'needed':False,'generation':4},current_export_record,{'completed':True,'generation':4}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':4,'updatedFiles':0}), \
                patch('tools.review.domains.map_assets.database_restore.read_verified_snapshot_payload') as current_restore_mock:
            current_test_case.assertTrue(execute_content_snapshot_cycle('/nonexistent-backup')['ledgerSynced'])
            current_test_case.assertTrue(current_api_mock.call_args_list[1].args[1].endswith('?replay=true'))
            current_restore_mock.assert_not_called()

    def test_replay_unsupported_fails_without_restore(current_test_case):
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',return_value={'needed':False,'generation':4}), \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger') as current_publish_mock:
            with current_test_case.assertRaisesRegex(ValueError,'재출력을 지원하지 않습니다'):
                execute_content_snapshot_cycle('/nonexistent-backup')
            current_publish_mock.assert_not_called()
