"""원장 반영 성공 전 DB 완료를 기록하지 않는 계약."""
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.database_snapshot import execute_content_snapshot_cycle, encode_content_snapshot_payload


class ContentLedgerSyncTests(unittest.TestCase):
    def test_ledger_failure_never_marks_complete(self):
        current_payload_record={'generation':4}
        current_export_record={'needed':True,'runId':'run-id','payload':current_payload_record,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export_record,{}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',side_effect=ValueError('원장 오류')):
            with self.assertRaisesRegex(ValueError,'원장 오류'):
                execute_content_snapshot_cycle(current_directory_name)
            self.assertTrue(current_api_mock.call_args_list[-1].args[1].endswith('/fail'))

    def test_sync_writes_ledger_without_generation_bundle(self):
        current_payload_record={'generation':4}
        current_export_record={'needed':True,'runId':'run-id','payload':current_payload_record,
            'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.dict('os.environ',{'SLIME_ASSETS_ROOT':current_directory_name}), \
                patch('tools.review.domains.map_assets.database_snapshot.execute_content_api_request',side_effect=[current_export_record,{}, {'needed':False,'generation':4}]) as current_api_mock, \
                patch('tools.review.domains.map_assets.database_ledger.publish_content_asset_ledger',return_value={'generation':4,'updatedFiles':3}) as current_ledger_mock, \
                patch('tools.review.domains.map_assets.database_snapshot.publish_content_snapshot_bundle') as current_bundle_mock:
            self.assertTrue(execute_content_snapshot_cycle(current_directory_name)['ledgerSynced'])
            self.assertTrue(execute_content_snapshot_cycle(current_directory_name)['ledgerSynced'])
            current_bundle_mock.assert_not_called()
            current_ledger_mock.assert_called_once()
            self.assertTrue(current_api_mock.call_args_list[1].args[1].endswith('/complete'))
