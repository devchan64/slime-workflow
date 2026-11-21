import unittest

from workflow.domains.map_assets.map_recovery_assessment import assess_map_recovery_evidence


class MapRecoveryAssessmentTests(unittest.TestCase):
    def test_receipt_and_each_file_are_classified_without_assuming_retry_is_safe(self):
        current_request_hash = 'a' * 64
        current_file_records = [
            {'name': 'map', 'before_sha256': '1' * 64, 'after_sha256': '2' * 64, 'observed_sha256': '2' * 64},
            {'name': 'registry', 'before_sha256': '3' * 64, 'after_sha256': '4' * 64, 'observed_sha256': '3' * 64},
        ]
        for current_receipt_state, current_expected_state in (('matched', 'files_incomplete'), ('not_found', 'receipt_unconfirmed'), ('unavailable', 'receipt_unconfirmed'), ('mismatch', 'receipt_mismatch')):
            with self.subTest(receipt=current_receipt_state):
                current_receipt_record = {'state': current_receipt_state, 'request_sha256': current_request_hash}
                current_result_value = assess_map_recovery_evidence(current_request_hash, current_receipt_record, current_file_records)
                self.assertEqual(current_result_value['state'], current_expected_state)
                self.assertEqual([current_file_value['state'] for current_file_value in current_result_value['files']], ['after', 'before'])
        current_receipt_record = {'state': 'matched', 'request_sha256': current_request_hash}
        current_file_records[1]['observed_sha256'] = '4' * 64
        self.assertEqual(assess_map_recovery_evidence(current_request_hash, current_receipt_record, current_file_records)['state'], 'files_match_receipt')
        current_file_records[1]['observed_sha256'] = '5' * 64
        self.assertEqual(assess_map_recovery_evidence(current_request_hash, current_receipt_record, current_file_records)['state'], 'file_conflict')

    def test_rejects_missing_duplicate_or_untrusted_evidence(self):
        current_request_hash = 'a' * 64
        current_receipt_record = {'state': 'matched', 'request_sha256': current_request_hash}
        current_file_record = {'name': 'map', 'before_sha256': '1' * 64, 'after_sha256': '2' * 64, 'observed_sha256': '1' * 64}
        for current_receipt_value, current_files_value in (({'state': 'matched', 'request_sha256': 'b' * 64}, [current_file_record]), (current_receipt_record, []), (current_receipt_record, [current_file_record, current_file_record]), (current_receipt_record, [{**current_file_record, 'observed_sha256': None}])):
            with self.subTest(receipt=current_receipt_value, files=current_files_value):
                with self.assertRaises(ValueError):
                    assess_map_recovery_evidence(current_request_hash, current_receipt_value, current_files_value)

    def test_plan_observation_verifies_request_and_exact_file_set(self):
        import hashlib
        import json
        from workflow.domains.map_assets.map_recovery_assessment import assess_map_plan_evidence
        current_database_request = {'requestId': 'request-123', 'documents': []}
        current_request_hash = hashlib.sha256(json.dumps(current_database_request, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        current_plan_record = {'database_request': current_database_request, 'request_sha256': current_request_hash, 'pending_files': {'map': b'after', 'registry': b'new registry'}}
        current_before_files = {'map': b'before', 'registry': b'old registry'}
        current_observed_files = {'map': b'after', 'registry': b'old registry'}
        current_receipt_record = {'state': 'matched', 'request_sha256': current_request_hash}
        self.assertEqual(assess_map_plan_evidence(current_plan_record, current_before_files, current_observed_files, current_receipt_record)['state'], 'files_incomplete')
        with self.assertRaisesRegex(ValueError, '파일 목록'):
            assess_map_plan_evidence(current_plan_record, current_before_files, {'map': b'after'}, current_receipt_record)
        current_database_request['requestId'] = 'different'
        with self.assertRaisesRegex(ValueError, '요청 해시 불일치'):
            assess_map_plan_evidence(current_plan_record, current_before_files, current_observed_files, current_receipt_record)
