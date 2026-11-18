"""모델 준비 접수 중복과 응답 유실 회귀 검사."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore


class HermesModelPreparationStoreTest(unittest.TestCase):
    def test_duplicate_and_cross_service_are_rejected_or_reused(self):
        with TemporaryDirectory() as temporary_root_path:
            current_store_value = HermesModelPreparationStore(temporary_root_path)
            current_calls_list = []
            def validate_current_service(model_service_name):
                self.assertEqual(model_service_name, 'flux-image')
            def submit_current_service(model_service_name):
                current_calls_list.append(model_service_name)
                return {'preparation_status': 'running', 'private_path': '/private'}
            def execute_current_request(unused_index_value):
                return current_store_value.execute_model_preparation_once('request_123', 'flux-image', validate_current_service, submit_current_service)
            with ThreadPoolExecutor(max_workers=8) as current_executor_value:
                current_results_list = list(current_executor_value.map(execute_current_request, range(8)))
            self.assertEqual(len(current_calls_list), 1)
            self.assertEqual(sum(not result['duplicate'] for result in current_results_list), 1)
            self.assertNotIn('private_path', str(current_results_list))
            with self.assertRaises(ValueError):
                current_store_value.read_model_preparation_receipt('request_123', 'kimodo')
            self.assertEqual(HermesDelegationStore(temporary_root_path).list_delegation_receipts()['records'], [])

    def test_lost_response_stays_unknown_and_is_not_resent(self):
        with TemporaryDirectory() as temporary_root_path:
            current_store_value = HermesModelPreparationStore(temporary_root_path)
            current_calls_list = []
            def submit_current_service(model_service_name):
                current_calls_list.append(model_service_name)
                raise OSError('response lost')
            with self.assertRaises(OSError):
                current_store_value.execute_model_preparation_once('request_456', 'flux-image', lambda current_service_name: None, submit_current_service)
            current_result_value = current_store_value.execute_model_preparation_once('request_456', 'flux-image', lambda current_service_name: None, submit_current_service)
            self.assertEqual(current_result_value['state'], 'unknown')
            self.assertEqual(len(current_calls_list), 1)

    def test_preparation_history_recovers_request_and_excludes_corruption(self):
        with TemporaryDirectory() as temporary_root_path:
            current_store_value = HermesModelPreparationStore(temporary_root_path)
            current_store_value.execute_model_preparation_once('request_hist_123', 'wan22-fun-control', lambda current_service_name:None, lambda current_service_name:{'id':'2026-11-18_12-00-19-05056f95'})
            (Path(temporary_root_path) / 'badrecord_123.json').write_text('{')
            current_records_list = current_store_value.list_model_preparation_receipts()['records']
            self.assertEqual(len(current_records_list), 1)
            self.assertEqual(current_records_list[0]['request_id'], 'request_hist_123')
            self.assertEqual(current_records_list[0]['job_id'], '2026-11-18_12-00-19-05056f95')

    def test_policy_rejection_does_not_create_receipt(self):
        with TemporaryDirectory() as temporary_root_path:
            current_store_value = HermesModelPreparationStore(temporary_root_path)
            def reject_current_service(model_service_name):
                raise ValueError('policy blocked')
            with self.assertRaises(ValueError):
                current_store_value.execute_model_preparation_once('request_789', 'flux-image', reject_current_service, lambda current_service_name: {})
            self.assertFalse((Path(temporary_root_path) / 'request_789.json').exists())


if __name__ == '__main__':
    unittest.main()
