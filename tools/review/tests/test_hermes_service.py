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
        self.hermes_service_manager = HermesServiceManager(Path(self.hermes_temporary_root.name) / 'jobs', Path(self.hermes_temporary_root.name) / 'sessions')

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

    def test_read_only_management_observation_preserves_unknown_and_filters_fields(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('tools.review.common.gpu_status.read_gpu_status', return_value={'status':'busy', 'processes':[{'command':'private'}], 'gtt_free_mib':123, 'vram_free_mib':456, 'unexpected':'private'}), patch('tools.review.common.gpu_job_queue.list_waiting_gpu_jobs', return_value={'jobs':[{'id':'job-1', 'service':'kimodo', 'path':'private'}]}):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'busy')
        self.assertEqual(hermes_observation_record['gpu']['process_count'], 1)
        self.assertEqual(hermes_observation_record['queue']['jobs'], [{'id':'job-1', 'service':'kimodo'}])
        self.assertNotIn('private', str(hermes_observation_record))
        with patch('tools.review.common.gpu_status.read_gpu_status', side_effect=OSError('unavailable')), patch('tools.review.common.gpu_job_queue.list_waiting_gpu_jobs', side_effect=OSError('unavailable')):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'unavailable')
        self.assertEqual(hermes_observation_record['queue']['status'], 'unavailable')

    def test_management_status_uses_shared_observation_and_rejects_input(self):
        from tools.review.domains.hermes_agent import management_observer
        current_snapshot_value = {'model': {'status': 'unavailable'}, 'gpu': {'status': 'busy'}, 'queue': {'status': 'available', 'jobs': []}}
        with patch.object(management_observer, 'read_hermes_management_snapshot', return_value=current_snapshot_value):
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-management-status', {}), current_snapshot_value)
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-management-status', {}), ('POST', '/hermes-agent/hermes-management-status'))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-management-status', {'command':'prepare'})

    def test_generator_observation_uses_only_fixed_read_commands(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_generator_snapshot
        current_job_id = '2026-11-17_10-00-00-12345678'
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[{'ready':True, 'preparation_status':'idle', 'private':'secret'}, {'running':True, 'id':current_job_id, 'private':'secret'}]) as current_gateway_mock:
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model'], {'status':'available', 'ready':True, 'preparation_status':'idle'})
        self.assertEqual(current_generator_value['active'], {'status':'available', 'running':True, 'id':current_job_id})
        self.assertEqual([current_call.args[:3] for current_call in current_gateway_mock.call_args_list], [('kimodo', 'model-status', {}), ('kimodo', 'active', {})])
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=[ValueError('offline'), {'running':True, 'id':'../../bad'}]):
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model']['status'], 'unavailable')
        self.assertEqual(current_generator_value['active']['status'], 'unavailable')

    def test_model_observation_reports_failure_without_ready_claim(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('tools.review.domains.hermes_agent.management_observer.inspect_hermes_model_status', side_effect=OSError('unavailable')):
            current_observation_record = read_hermes_management_snapshot()
        self.assertEqual(current_observation_record['model'], {'status': 'unavailable'})

    def test_reservation_observation_is_filtered_and_conservative(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_root_path = Path(current_temp_root)
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'], [])
            current_active_path = current_root_path / 'active'
            current_active_path.mkdir()
            current_job_id = '2026-11-18_00-00-00-12345678'
            (current_active_path / 'one.json').write_text(json.dumps({'service':'hermes-agent','required_memory_mib':32768,'path':'/private/' + current_job_id,'worker_process_token':'secret','pid':123}))
            (current_active_path / 'two.json').write_text('bad json')
            current_result_value = read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_result_value['status'], 'available')
            self.assertEqual(current_result_value['records'][0], {'state':'recorded','service':'hermes-agent','job_id':current_job_id,'required_memory_mib':32768})
            self.assertEqual(current_result_value['records'][1]['state'], 'unknown')
            self.assertNotIn('secret', str(current_result_value))
            self.assertNotIn('/private/', str(current_result_value))
            (current_active_path / 'two.json').unlink()
            (current_active_path / 'two.json').symlink_to(current_active_path / 'one.json')
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'][1]['state'], 'unknown')
            with patch('os.scandir', side_effect=PermissionError('denied')):
                self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['status'], 'unavailable')

    def test_recent_job_observation_filters_fields_and_handles_missing_status(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_recent_job_snapshot
        current_job_root = self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True, exist_ok=True)
        for current_index in range(12):
            current_job_path = current_job_root / ('2026-11-18_00-00-' + f'{current_index:02d}' + '-12345678')
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{"prompt":"secret"}')
            if current_index != 11:
                (current_job_path / 'status.json').write_text('{"status":"completed","error":"private"}')
        current_result_value = read_hermes_recent_job_snapshot(self.hermes_service_manager)
        self.assertEqual(current_result_value['status'], 'available')
        self.assertEqual(len(current_result_value['jobs']), 10)
        self.assertTrue(current_result_value['truncated'])
        self.assertEqual(current_result_value['jobs'][0]['status'], 'unknown')
        self.assertNotIn('secret', str(current_result_value))
        self.assertNotIn('private', str(current_result_value))
        self.assertNotIn(str(current_job_root), str(current_result_value))
        with patch.object(self.hermes_service_manager, 'list_hermes_job_paths', side_effect=OSError('unavailable')):
            self.assertEqual(read_hermes_recent_job_snapshot(self.hermes_service_manager)['status'], 'unavailable')

    def test_capabilities_use_registered_gateway_and_strict_empty_input(self):
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES
        current_catalog_value = self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        self.assertEqual(current_catalog_value['version'], 1)
        self.assertTrue(current_catalog_value['records'])
        for current_record_value in current_catalog_value['records']:
            self.assertIn(current_record_value['command'], MANAGEMENT_SERVICE_COMMANDS['hermes-agent'])
            self.assertEqual(current_record_value['method'], MANAGEMENT_COMMAND_ROUTES[current_record_value['command']][0])
            self.assertIn(current_record_value['effect'], ('read', 'enqueue', 'recovery_possible', 'cancel_request'))
            self.assertEqual(current_record_value['payload_schema']['required'], current_record_value['required'])
            self.assertFalse(current_record_value['payload_schema']['additionalProperties'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {'extra':True})

    def test_tool_activity_is_bounded_and_reports_command_exit(self):
        from tools.review.domains.hermes_agent.service import read_hermes_tool_activity
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path = Path(current_temp_root)
            current_events = [{'type':'tool_use','name':'terminal','tool_call_id':'call1','input':{'command':'echo test'},'timestamp':1794929185434}, {'type':'tool_result','name':'terminal','tool_call_id':'call1','output':json.dumps({'exit_code':2,'output':'private full text'}),'is_error':False}]
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_event) for current_event in current_events))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(current_activity_record['events'][0]['target'], 'echo test')
            self.assertEqual(current_activity_record['events'][1]['result'], 'error')
            self.assertNotIn('private full text', str(current_activity_record))
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_events[0]) for _ in range(12)))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(len(current_activity_record['events']), 8)
            self.assertTrue(current_activity_record['truncated'])

    def test_memory_capacity_distinguishes_vram_from_host_gtt(self):
        from tools.review.domains.hermes_agent.management_observer import read_hermes_memory_capacity
        current_gpu_value = {'status':'idle', 'vram_total_mib':98304, 'vram_free_mib':90000, 'gtt_total_mib':15000, 'gtt_free_mib':14000}
        with patch('tools.review.common.gpu_job_queue.read_host_available_memory', return_value=20000), patch('tools.review.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'vram')
            self.assertTrue(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 90000)
            current_gpu_value.update(vram_total_mib=1000, gtt_total_mib=100000, gtt_free_mib=90000)
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'gtt')
            self.assertFalse(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 20000)
        with patch('tools.review.common.gpu_job_queue.read_host_available_memory', return_value=5000), patch('tools.review.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_gpu_value.update(vram_total_mib=98304, gtt_total_mib=15000)
            self.assertEqual(read_hermes_memory_capacity(current_gpu_value)['pool_available_mib'], 0)
        self.assertEqual(read_hermes_memory_capacity({'status':'unavailable'})['status'], 'unavailable')

    def test_session_requests_are_idempotent_and_survive_reopen(self):
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_store_path = Path(self.hermes_temporary_root.name) / 'sessions'
        hermes_session_store = HermesSessionStore(hermes_store_path)
        hermes_session_identifier = hermes_session_store.create_session_record()['id']
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: HermesSessionStore(hermes_store_path).append_session_request(hermes_session_identifier, 'session-request-1234', '상태를 확인해 줘'), range(4)))
        self.assertEqual(sum(not hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 1)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            hermes_session_store.append_session_request(hermes_session_identifier, 'session-request-1234', '다른 지시')
        hermes_job_identifier = '2026-11-17_10-00-00-12345678'
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        with self.assertRaisesRegex(ValueError, '다른 작업'):
            hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', '2026-11-17_10-00-01-12345678')
        hermes_session_record = HermesSessionStore(hermes_store_path).read_session_record(hermes_session_identifier)
        self.assertEqual(len(hermes_session_record['messages']), 1)
        self.assertEqual(hermes_session_record['messages'][0]['job_id'], hermes_job_identifier)
        with self.assertRaises(ValueError):
            hermes_session_store.read_session_record('../outside')

    def test_session_creation_and_read_are_gateway_compatible_and_idempotent(self):
        hermes_session_identifier = 'a' * 32
        hermes_session_payload = {'session_id': hermes_session_identifier}
        for hermes_command_name in ('hermes-session-create', 'hermes-session-read'):
            hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', hermes_command_name, hermes_session_payload)
            self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_session_payload), ('hermes-agent', hermes_command_name, hermes_session_payload))
        hermes_first_record = self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload), hermes_first_record)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-read', hermes_session_payload), hermes_first_record)
        hermes_session_list = self.hermes_service_manager.execute_hermes_command('hermes-session-list', {})
        self.assertEqual(hermes_session_list['sessions'][0]['id'], hermes_session_identifier)
        self.assertEqual(hermes_session_list['sessions'][0]['message_count'], 0)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-list', {'extra': 1})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': '../outside'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': None})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier, 'extra': 1})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_session_submit_retries_and_includes_completed_context(self, hermes_launch_mock, hermes_ready_mock):
        hermes_session_identifier = 'b' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_first_payload = {'session_id': hermes_session_identifier, 'request_id': 'first-request-1234', 'prompt': '첫 질문'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_first_results = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_first_payload), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({current_result['job_id'] for current_result in hermes_first_results}), 1)
        self.assertEqual(sum(not current_result['duplicate'] for current_result in hermes_first_results), 1)
        hermes_second_payload = {'session_id': hermes_session_identifier, 'request_id': 'second-request-1234', 'prompt': '그 답을 이어서'}
        with self.assertRaisesRegex(ValueError, '종료된 후'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_second_payload)
        hermes_first_job_path = self.hermes_service_manager.hermes_storage_root / hermes_first_results[0]['job_id']
        (hermes_first_job_path / 'status.json').write_text('{"status":"completed"}')
        (hermes_first_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':'첫 답변'}, ensure_ascii=False))
        hermes_second_result = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_second_payload)
        hermes_second_request = json.loads((self.hermes_service_manager.hermes_storage_root / hermes_second_result['job_id'] / 'request.json').read_text())
        self.assertIn('첫 질문', hermes_second_request['prompt'])
        self.assertIn('첫 답변', hermes_second_request['prompt'])
        hermes_view_record = self.hermes_service_manager.execute_hermes_command('hermes-session-view', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_view_record['messages'][0]['job']['final_response'], '첫 답변')
        self.assertEqual(hermes_view_record['messages'][1]['job']['status']['status'], 'unknown')
        self.assertEqual(hermes_view_record['message_count'], 2)
        self.assertIn('그 답을 이어서', hermes_second_request['prompt'])
        self.assertEqual(hermes_launch_mock.call_count, 2)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**hermes_first_payload, 'prompt':'다른 질문'})

    @patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('tools.review.domains.hermes_agent.service.launch_gpu_process')
    def test_session_retry_after_job_accepted_but_link_failed(self, hermes_launch_mock, hermes_ready_mock):
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_identifier = 'c' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_request_record = {'session_id': hermes_session_identifier, 'request_id': 'retry-request-1234', 'prompt': '테스트'}
        with patch.object(HermesSessionStore, 'attach_session_job', side_effect=OSError('저장 중단')):
            with self.assertRaises(OSError):
                self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        hermes_retry_record = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        self.assertTrue(hermes_retry_record['duplicate'])
        hermes_launch_mock.assert_called_once()
        hermes_saved_record = self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_saved_record['messages'][0]['job_id'], hermes_retry_record['job_id'])

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
        self.assertEqual(hermes_detail_record['final_response'], '검사 완료')
        self.assertFalse(hermes_detail_record['final_response_truncated'])
        (hermes_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':'가' * 8001}, ensure_ascii=False))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(len(hermes_detail_record['final_response']), 8000)
        self.assertTrue(hermes_detail_record['final_response_truncated'])

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
