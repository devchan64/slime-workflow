"""관리 작업 위임 중복 방지와 불확실한 접수 복구 검증."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesDelegationTests(unittest.TestCase):
    def test_proposal_is_strict_and_never_submits(self):
        from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal
        current_answer_text = '생성 제안입니다.\nHERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
        self.assertEqual(parse_hermes_kimodo_proposal(current_answer_text)['prompt'], 'walk forward')
        for current_invalid_text in (current_answer_text + '\n' + current_answer_text, current_answer_text.replace('"seed":42', '"seed":42,"seed":43'), current_answer_text.replace('"seed":42', '"seed":42,"url":"https://invalid"'), current_answer_text.replace('"frames":90', '"frames":1'), current_answer_text.replace('END_HERMES_KIMODO_PROPOSAL', '')):
            with self.subTest(answer=current_invalid_text), self.assertRaises(ValueError):
                parse_hermes_kimodo_proposal(current_invalid_text)

    def test_service_proposal_requires_completed_untruncated_job(self):
        import json
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service_value = HermesServiceManager(Path(current_temp_root))
            current_job_identifier = '2026-11-18_00-00-00-12345678'
            current_job_path = Path(current_temp_root) / current_job_identifier
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{}')
            (current_job_path / 'status.json').write_text('{"status":"running"}')
            current_final_answer = 'HERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':current_final_answer}))
            with self.assertRaisesRegex(ValueError, '완료된'):
                current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})
            (current_job_path / 'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})['proposal']['seed'], 42)
            (current_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':current_final_answer + 'x' * 8001}))
            with self.assertRaisesRegex(ValueError, '잘려'):
                current_service_value.execute_hermes_command('hermes-kimodo-proposal', {'id':current_job_identifier})

    def test_receipt_history_includes_unknown_and_hides_input_hash(self):
        import json
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_store_value.execute_delegation_once('request_123456', {'prompt':'private text'}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('request_654321', {}, Mock(side_effect=TimeoutError()))
            (Path(current_temp_root) / 'corrupt_123456.json').write_text('not json')
            (Path(current_temp_root) / 'linked_123456.json').symlink_to(Path(current_temp_root) / 'request_123456.json')
            current_result_value = current_store_value.list_delegation_receipts()
            current_records_by_id = {current_record['request_id']: current_record for current_record in current_result_value['records']}
            self.assertEqual(current_records_by_id['request_123456']['state'], 'accepted')
            self.assertEqual(current_records_by_id['request_654321']['state'], 'unknown')
            self.assertEqual(current_records_by_id['corrupt_123456']['state'], 'unavailable')
            self.assertNotIn('linked_123456', current_records_by_id)
            self.assertNotIn('private text', json.dumps(current_result_value))
            self.assertNotIn('request_sha256', json.dumps(current_result_value))

    def test_job_status_only_queries_accepted_receipt(self):
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = CurrentStore(Path(current_temp_root) / 'delegations')
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore', return_value=current_store_value), patch('tools.review.common.management_gateway.execute_management_command', return_value={'status':'completed'}) as current_gateway_mock:
                self.assertEqual(current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})['receipt']['state'], 'not_found')
                current_gateway_mock.assert_not_called()
                current_store_value.execute_delegation_once('request_123456', {}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
                current_result_value = current_service_value.execute_hermes_command('hermes-delegation-job-status', {'request_id':'request_123456'})
                self.assertEqual(current_result_value['job']['status'], 'completed')
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'status', {'id':'2026-11-18_00-00-00-12345678'}))

    def test_separate_processes_reuse_receipt_and_crash_remains_unknown(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_child_source = """import json, pathlib, sys, time
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
root=pathlib.Path(sys.argv[1])
def submit(record):
 with (root/'calls').open('a') as stream: stream.write('called\\n')
 time.sleep(.15)
 return {'id':'2026-11-18_00-00-00-12345678'}
print(json.dumps(HermesDelegationStore(root/'records').execute_delegation_once('request_123456', {'service':'kimodo'}, submit)))
"""
            current_children = [subprocess.Popen([sys.executable, '-c', current_child_source, current_temp_root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
            current_results = []
            for current_child_process in current_children:
                current_stdout_text, current_stderr_text = current_child_process.communicate(timeout=15)
                self.assertEqual(current_child_process.returncode, 0, current_stderr_text)
                current_results.append(json.loads(current_stdout_text))
            self.assertEqual(sum(not current_result_value['duplicate'] for current_result_value in current_results), 1)
            self.assertEqual((Path(current_temp_root) / 'calls').read_text().count('called'), 1)
            current_crash_source = """import os,sys
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
HermesDelegationStore(sys.argv[1]).execute_delegation_once('crash_request_123', {}, lambda request: os._exit(37))
"""
            current_crash_process = subprocess.run([sys.executable, '-c', current_crash_source, str(Path(current_temp_root) / 'records')], timeout=15)
            self.assertEqual(current_crash_process.returncode, 37)
            self.assertEqual(HermesDelegationStore(Path(current_temp_root) / 'records').read_delegation_status('crash_request_123')['state'], 'unknown')

    def test_cancel_requires_matching_accepted_delegation(self):
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = CurrentStore(Path(current_temp_root) / 'delegations')
            current_store_value.execute_delegation_once('request_123456', {}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore', return_value=current_store_value), patch('tools.review.common.management_gateway.execute_management_command', return_value={'status':'running','cancel_requested':True}) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'2026-11-18_00-00-01-12345678'})
                with self.assertRaises(ValueError):
                    current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_654321', 'job_id':'2026-11-18_00-00-00-12345678'})
                current_gateway_mock.assert_not_called()
                current_cancel_result = current_service_value.execute_hermes_command('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'2026-11-18_00-00-00-12345678'})
                self.assertTrue(current_cancel_result['cancel_requested'])
                self.assertEqual(current_cancel_result['status'], 'running')
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'cancel', {'id':'2026-11-18_00-00-00-12345678'}))

    def test_receipt_lookup_does_not_submit_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            self.assertEqual(current_store_value.read_delegation_status('request_123456')['state'], 'not_found')
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_store_value.execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            self.assertEqual(HermesDelegationStore(current_temp_root).read_delegation_status('request_123456'), {'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'})
            self.assertEqual(current_submit_mock.call_count, 1)
            current_failed_submit = Mock(side_effect=TimeoutError('lost'))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('request_654321', {}, current_failed_submit)
            self.assertEqual(current_store_value.read_delegation_status('request_654321')['state'], 'unknown')
            self.assertEqual(current_failed_submit.call_count, 1)
            with self.assertRaises(ValueError):
                current_store_value.read_delegation_status('../outside')

    def test_parallel_retries_use_one_submission_and_same_job(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            def submit_same_request(current_unused_value):
                return HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo', 'prompt':'걷기'}, current_submit_mock)
            with ThreadPoolExecutor(max_workers=6) as current_thread_pool:
                current_results = list(current_thread_pool.map(submit_same_request, range(6)))
            self.assertEqual(current_submit_mock.call_count, 1)
            self.assertEqual(sum(not current_result['duplicate'] for current_result in current_results), 1)
            self.assertEqual({current_result['job_id'] for current_result in current_results}, {'2026-11-18_00-00-00-12345678'})
            with self.assertRaisesRegex(ValueError, '다른 입력'):
                HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo', 'prompt':'달리기'}, current_submit_mock)

    def test_lost_response_is_never_submitted_again_after_reopen(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_submit_mock = Mock(side_effect=TimeoutError('응답 유실'))
            with self.assertRaises(TimeoutError):
                HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            current_recovery_result = HermesDelegationStore(current_temp_root).execute_delegation_once('request_123456', {'service':'kimodo'}, current_submit_mock)
            self.assertEqual(current_recovery_result['state'], 'unknown')
            self.assertEqual(current_submit_mock.call_count, 1)
            self.assertNotIn('kimodo', (Path(current_temp_root) / 'request_123456.json').read_text())

    def test_validation_failure_precedes_dispatch_record_and_retry_skips_validation(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'2026-11-18_00-00-00-12345678'})
            current_validate_mock = Mock(side_effect=ValueError('invalid'))
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock, current_validate_mock)
            self.assertFalse((Path(current_temp_root) / 'request_123456.json').exists())
            current_submit_mock.assert_not_called()
            current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)
            self.assertEqual(current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock, current_validate_mock)['state'], 'accepted')
            self.assertEqual(current_validate_mock.call_count, 1)

    def test_service_dispatches_to_registered_kimodo_command_once(self):
        from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore as CurrentStore
        current_request_value = {current_key: current_value for current_key, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key != 'schema_version'}
        current_request_value['action'] = 'generate'
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service_value = HermesServiceManager(Path(current_temp_root) / 'jobs')
            with patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore', side_effect=lambda: CurrentStore(Path(current_temp_root) / 'delegations')), patch('tools.review.common.management_gateway.execute_management_command', return_value={'id':'2026-11-18_00-00-00-12345678'}) as current_gateway_mock:
                current_payload_value = {'request_id':'request_123456', 'request':current_request_value}
                self.assertFalse(current_service_value.execute_hermes_command('hermes-delegate-kimodo', current_payload_value)['duplicate'])
                self.assertTrue(current_service_value.execute_hermes_command('hermes-delegate-kimodo', current_payload_value)['duplicate'])
                self.assertEqual(current_gateway_mock.call_count, 1)
                self.assertEqual(current_gateway_mock.call_args.args[:3], ('kimodo', 'generate', current_request_value))

    def test_invalid_identifier_and_bad_response_do_not_allow_relaunch(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_store_value = HermesDelegationStore(current_temp_root)
            current_submit_mock = Mock(return_value={'id':'../outside'})
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('../outside', {}, current_submit_mock)
            current_submit_mock.assert_not_called()
            with self.assertRaises(ValueError):
                current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)
            self.assertEqual(current_store_value.execute_delegation_once('request_123456', {}, current_submit_mock)['state'], 'unknown')
            self.assertEqual(current_submit_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
