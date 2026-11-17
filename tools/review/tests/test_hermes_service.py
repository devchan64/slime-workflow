import json
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from tools.review.domains.hermes_agent.service import HermesServiceManager
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class HermesServiceTests(unittest.TestCase):
    def setUp(self):
        self.hermes_temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.hermes_temporary_root.cleanup)
        self.hermes_service_manager = HermesServiceManager(Path(self.hermes_temporary_root.name) / 'jobs')

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_duplicate_submission_is_single_queue_job(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'same-request-1234', 'prompt':'작은 테스트'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({hermes_result_record['id'] for hermes_result_record in hermes_result_values}), 1)
        self.assertEqual(sum(hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 3)
        with self.assertRaisesRegex(ValueError, '다른 지시'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'same-request-1234', 'prompt':'다른 테스트'})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_unknown_acceptance_is_not_relaunched(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'unknown-request-1234', 'prompt':'테스트'}
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        hermes_job_status = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(hermes_job_status['status']['status'], 'unknown')
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        hermes_launch_mock.assert_called_once()

    def test_gateway_command_round_trip(self):
        hermes_payload_record = {'request_id':'test-request-1234', 'prompt':'테스트'}
        hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', 'hermes-submit', hermes_payload_record)
        self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_payload_record), ('hermes-agent', 'hermes-submit', hermes_payload_record))

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_detail_includes_agent_response_and_tool_result(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'trace-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_event_values = [{'type':'tool_use','name':'terminal','input':{'command':'python -m unittest'}}, {'type':'tool_result','output':'OK'}, {'type':'result','text':'검사 완료'}]
        (hermes_job_path / 'hermes-events.jsonl').write_text(''.join(json.dumps(hermes_event_record, ensure_ascii=False) + '\n' for hermes_event_record in hermes_event_values))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertIn('python -m unittest', hermes_detail_record['log'])
        self.assertIn('검사 완료', hermes_detail_record['log'])

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_diff_chunks_preserve_unicode_bytes_and_require_completion(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'diff-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_diff_bytes = '가나다'.encode('utf-8')
        (hermes_job_path / 'change.diff').write_bytes(hermes_diff_bytes)
        hermes_chunk_request = {'id':hermes_job_result['id'], 'offset':0, 'limit':2}
        with self.assertRaisesRegex(ValueError, '종료된 뒤'):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
        (hermes_job_path / 'status.json').write_text('{"status":"completed"}')
        hermes_collected_bytes = bytearray()
        while hermes_chunk_request['offset'] is not None:
            hermes_chunk_record = self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
            hermes_collected_bytes.extend(base64.b64decode(hermes_chunk_record['data_base64']))
            hermes_chunk_request['offset'] = hermes_chunk_record['next_offset']
        self.assertEqual(bytes(hermes_collected_bytes), hermes_diff_bytes)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', {'id':hermes_job_result['id'], 'offset':0, 'limit':999999})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_verification_modules_are_allowlisted_and_idempotent(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'verify-request-1234', 'prompt':'테스트', 'verification_modules':['tools.review.tests.test_hermes_service']}
        hermes_first_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        self.assertFalse(hermes_first_result['duplicate'])
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'verify-request-1234', 'prompt':'테스트'})
        with self.assertRaisesRegex(ValueError, '등록된 검증 모듈'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'bad-module-1234', 'prompt':'테스트', 'verification_modules':['os.system']})
        hermes_launch_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
