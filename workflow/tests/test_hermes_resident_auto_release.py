"""상주 반환 후보가 실제 공용 예약과 메모리에 묶이는지 확인한다."""
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent import resident_auto_release


class ResidentAutomaticReleaseTests(unittest.TestCase):
    def test_chat_guard_blocks_release_until_dispatched_job_finishes(self):
        from contextlib import nullcontext
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            queue_directory = root_directory / 'queue'
            active_directory = queue_directory / 'active'
            active_directory.mkdir(parents=True)
            resident_directory = root_directory / 'resident_123'
            resident_directory.mkdir()
            write_record_atomically(resident_directory / 'request.json', {'context':{'session_id':'a'*32}})
            write_record_atomically(active_directory / 'active.json', {'path':str(resident_directory),'service':'hermes-agent'})
            chat_job_directory = root_directory / 'chat_job'
            chat_job_directory.mkdir()
            write_record_atomically(chat_job_directory / 'status.json', {'status':'queued'})
            service_manager_mock = Mock()
            service_manager_mock.hermes_session_root = root_directory / 'sessions'
            service_manager_mock.hold_hermes_service_lock.side_effect = lambda: nullcontext()
            service_manager_mock.resolve_hermes_job_path.return_value = chat_job_directory
            session_store_mock = Mock()
            session_store_mock.read_session_record.return_value = {'messages':[{'job_id':'chat_123'}]}
            queue_module = resident_auto_release.gpu_job_queue
            with patch.object(queue_module, 'GPU_QUEUE_DIRECTORY', queue_directory), \
                 patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch('workflow.domains.hermes_agent.session_store.HermesSessionStore', return_value=session_store_mock), \
                 patch.object(resident_auto_release, 'release_resident_for_waiting_generation', return_value={'state':'requested'}) as release_mock:
                self.assertIsNone(resident_auto_release.release_resident_with_chat_guard(service_manager_mock))
                release_mock.assert_not_called()
                write_record_atomically(chat_job_directory / 'status.json', {'status':'completed'})
                self.assertEqual(resident_auto_release.release_resident_with_chat_guard(service_manager_mock), {'state':'requested'})
                release_mock.assert_called_once()

    def test_two_residents_are_released_one_at_a_time(self):
        from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once, request_resident_release
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            residents_directory = root_directory / 'residents'
            queue_directory = root_directory / 'queue'
            active_directory = queue_directory / 'active'
            active_directory.mkdir(parents=True)
            for resident_number in (1, 2):
                resident_identifier = f'resident_{resident_number:03d}'
                enqueue_resident_once(resident_identifier, str(resident_number) * 32, root=residents_directory, launcher=lambda *args, **kwargs: None)
                resident_directory = residents_directory / resident_identifier
                write_record_atomically(resident_directory / 'resident-status.json', {'status':'ready','model':'qwen3.8-27b','worker_pid':40 + resident_number})
                write_record_atomically(active_directory / f'{resident_number}.json', {'path':str(resident_directory.resolve()),'service':'hermes-agent','worker_pgid':40 + resident_number})
            class ImmediateHandoffGuard:
                def run_without_open_session_handoff(self, session_id, callback, *, all_sessions=False):
                    return callback()
            def invoke_scoped_release(request_id, session_id, **release_options):
                return request_resident_release(request_id, session_id, root=residents_directory, **release_options)
            queue_module = resident_auto_release.gpu_job_queue
            with patch.object(queue_module, 'GPU_QUEUE_DIRECTORY', queue_directory), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'inspect_gpu_ticket_executor_identity', return_value='verified'), \
                 patch.object(queue_module, 'open_verified_hermes_process_group', side_effect=lambda _: os.open('/dev/null', os.O_RDONLY)), \
                 patch.object(resident_auto_release, 'GpuHandoffStore', return_value=ImmediateHandoffGuard()), \
                 patch.object(resident_auto_release, 'request_resident_release', side_effect=invoke_scoped_release), \
                 patch.object(resident_auto_release, 'select_resident_release_candidate', return_value='ticket'):
                first_result = resident_auto_release.release_resident_for_waiting_generation()
                self.assertEqual(first_result['state'], 'requested')
                self.assertTrue((residents_directory / first_result['id'] / 'release.request').exists())
                other_identifier = ({'resident_001', 'resident_002'} - {first_result['id']}).pop()
                self.assertFalse((residents_directory / other_identifier / 'release.request').exists())
                (active_directory / ('1.json' if first_result['id'] == 'resident_001' else '2.json')).unlink()
                second_result = resident_auto_release.release_resident_for_waiting_generation()
                self.assertEqual(second_result['id'], other_identifier)
                self.assertTrue((residents_directory / other_identifier / 'release.request').exists())

    def test_two_residents_are_revalidated_before_selecting_generation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            reservation_paths = []
            reservation_records = []
            for resident_number in (1, 2):
                resident_directory = root_directory / f'resident_{resident_number:03d}'
                resident_directory.mkdir()
                write_record_atomically(resident_directory / 'request.json', {'context':{'session_id':str(resident_number) * 32}})
                write_record_atomically(resident_directory / 'resident-status.json', {'status':'ready','worker_pid':resident_number + 40})
                reservation_record = {'path':str(resident_directory), 'service':'hermes-agent', 'worker_pgid':resident_number + 40, 'required_memory_mib':40}
                reservation_path = root_directory / f'reservation_{resident_number}.json'
                write_record_atomically(reservation_path, reservation_record)
                reservation_records.append(reservation_record)
                reservation_paths.append(reservation_path)
            queue_module = resident_auto_release.gpu_job_queue
            with patch.object(resident_auto_release, 'list_chat_queue_intents_locked', return_value=[]), \
                 patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'list_gpu_queue_record_paths', return_value=reservation_paths), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'inspect_gpu_ticket_executor_identity', return_value='verified'), \
                 patch.object(queue_module, 'open_verified_hermes_process_group', side_effect=lambda _: os.open('/dev/null', os.O_RDONLY)), \
                 patch.object(queue_module, 'read_gpu_memory_domain', return_value='vram'), \
                 patch.object(queue_module, 'read_gpu_memory', return_value=(200, 40)), \
                 patch.object(queue_module, 'read_host_available_memory', return_value=40000), \
                 patch.object(queue_module, 'read_worker_memory', return_value=30), \
                 patch.object(queue_module, 'read_worker_group_rss_kib', return_value=16384 * 1024), \
                 patch.object(queue_module, 'select_ticket_after_resident_release', return_value='ticket') as selection_mock:
                self.assertEqual(resident_auto_release.select_resident_release_candidate(root_directory, reservation_records[0]), 'ticket')
                self.assertEqual(selection_mock.call_args.args[:2], (20, 100))
                self.assertEqual(selection_mock.call_args.args[3], ['1'*32, '2'*32])
                write_record_atomically(root_directory / 'resident_002' / 'resident-status.json', {'status':'draining','worker_pid':42})
                self.assertIsNone(resident_auto_release.select_resident_release_candidate(root_directory, reservation_records[0]))

    def test_scheduler_release_revalidates_before_writing_request(self):
        from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once, request_resident_release
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            residents_directory = root_directory / 'residents'
            queue_directory = root_directory / 'queue'
            active_directory = queue_directory / 'active'
            active_directory.mkdir(parents=True)
            enqueue_resident_once('resident_123', 'a' * 32, root=residents_directory, launcher=lambda *args, **kwargs: None)
            resident_directory = residents_directory / 'resident_123'
            write_record_atomically(resident_directory / 'resident-status.json', {'status':'ready','model':'qwen3.8-27b','worker_pid':42})
            reservation_record = {'path':str(resident_directory.resolve()),'service':'hermes-agent','worker_pgid':42}
            write_record_atomically(active_directory / 'active.json', reservation_record)
            class ImmediateHandoffGuard:
                def run_without_open_session_handoff(self, session_id, callback, *, all_sessions=False):
                    self.asserted_session = session_id
                    return callback()
            def invoke_scoped_release(request_id, session_id, **release_options):
                return request_resident_release(request_id, session_id, root=residents_directory, **release_options)
            queue_module = resident_auto_release.gpu_job_queue
            with patch.object(queue_module, 'GPU_QUEUE_DIRECTORY', queue_directory), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'inspect_gpu_ticket_executor_identity', return_value='verified'), \
                 patch.object(queue_module, 'open_verified_hermes_process_group', side_effect=lambda _: os.open('/dev/null', os.O_RDONLY)), \
                 patch.object(resident_auto_release, 'GpuHandoffStore', return_value=ImmediateHandoffGuard()), \
                 patch.object(resident_auto_release, 'request_resident_release', side_effect=invoke_scoped_release), \
                 patch.object(resident_auto_release, 'select_resident_release_candidate', side_effect=[None, 'ticket']) as candidate_mock:
                self.assertEqual(resident_auto_release.release_resident_for_waiting_generation()['state'], 'deferred')
                self.assertFalse((resident_directory / 'release.request').exists())
                self.assertEqual(resident_auto_release.release_resident_for_waiting_generation()['state'], 'requested')
                self.assertTrue((resident_directory / 'release.request').is_file())
                self.assertEqual(candidate_mock.call_count, 2)
                write_record_atomically(resident_directory / 'resident-status.json', {'status':'draining','model':'qwen3.8-27b','worker_pid':42})
                self.assertIsNone(resident_auto_release.release_resident_for_waiting_generation())
                self.assertEqual(candidate_mock.call_count, 2)

    def test_candidate_rechecks_single_reservation_and_memory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            resident_directory = root_directory / 'resident_123'
            resident_directory.mkdir()
            write_record_atomically(resident_directory / 'request.json', {'context':{'session_id':'a' * 32}})
            reservation_record = {'path':str(resident_directory), 'service':'hermes-agent', 'worker_pgid':42, 'required_memory_mib':40}
            reservation_path = root_directory / 'reservation.json'
            write_record_atomically(reservation_path, reservation_record)
            queue_module = resident_auto_release.gpu_job_queue
            with patch.object(resident_auto_release, 'list_chat_queue_intents_locked', return_value=[]), \
                 patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'list_gpu_queue_record_paths', return_value=[reservation_path]), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'read_gpu_memory_domain', return_value='vram'), \
                 patch.object(queue_module, 'read_gpu_memory', return_value=(100, 40)), \
                 patch.object(queue_module, 'read_host_available_memory', return_value=20000), \
                 patch.object(queue_module, 'read_worker_memory', return_value=30), \
                 patch.object(queue_module, 'read_worker_group_rss_kib', return_value=1024), \
                 patch.object(queue_module, 'select_ticket_after_resident_release', return_value='ticket') as selection_mock:
                self.assertEqual(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record), 'ticket')
                self.assertEqual(selection_mock.call_args.args[:2], (30, 70))
                self.assertGreater(selection_mock.call_args.args[5], selection_mock.call_args.args[4])
                self.assertIsNone(resident_auto_release.select_resident_release_candidate(root_directory, {**reservation_record, 'worker_pgid':43}))
                with patch.object(queue_module, 'read_host_available_memory', return_value=5000), \
                     patch.object(queue_module, 'read_worker_group_rss_kib', return_value=4096 * 1024):
                    self.assertEqual(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record), 'ticket')
                    self.assertEqual(selection_mock.call_args.args[:2], (0, 70))
                earlier_chat_record = {'resident_id':'another_resident', 'session_id':'a'*32, 'order_ns':1}
                later_ticket_path = Path('00000000000000000002-42.json')
                with patch.object(resident_auto_release, 'list_chat_queue_intents_locked', return_value=[earlier_chat_record]), \
                     patch.object(queue_module, 'read_gpu_priority_order', return_value={}):
                    selection_mock.return_value = later_ticket_path
                    self.assertIsNone(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record))
                    with patch.object(queue_module, 'read_gpu_priority_order', return_value={later_ticket_path.name:-1}):
                        self.assertEqual(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record), later_ticket_path)
            with patch.object(resident_auto_release, 'list_chat_queue_intents_locked', return_value=[{'resident_id':'resident_123'}]), \
                 patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'list_gpu_queue_record_paths', return_value=[reservation_path]), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'read_gpu_memory') as memory_mock:
                self.assertIsNone(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record))
                memory_mock.assert_not_called()
            with patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'list_gpu_queue_record_paths', return_value=[reservation_path, reservation_path]):
                self.assertIsNone(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record))
            with patch.object(resident_auto_release, 'list_chat_queue_intents_locked', return_value=[]), \
                 patch.object(queue_module, 'read_priority_tickets', return_value=['waiting-ticket']), \
                 patch.object(queue_module, 'list_gpu_queue_record_paths', return_value=[reservation_path]), \
                 patch.object(queue_module, 'verify_hermes_resident_queue_job_path', return_value=True), \
                 patch.object(queue_module, 'read_gpu_memory_domain', return_value='gtt'), \
                 patch.object(queue_module, 'read_gpu_memory', return_value=(20000, 3000)), \
                 patch.object(queue_module, 'read_host_available_memory', return_value=7000), \
                 patch.object(queue_module, 'read_worker_memory', return_value=5000), \
                 patch.object(queue_module, 'read_worker_group_rss_kib', return_value=4096 * 1024), \
                 patch.object(queue_module, 'select_ticket_after_resident_release', return_value='ticket') as selection_mock:
                self.assertEqual(resident_auto_release.select_resident_release_candidate(root_directory, reservation_record), 'ticket')
                host_reserve_memory = queue_module.HOST_MEMORY_RESERVE_KIB // 1024
                self.assertEqual(selection_mock.call_args.args[0], min(3000, max(0, 7000 - host_reserve_memory)))
                self.assertEqual(selection_mock.call_args.args[1], min(8000, max(0, 11096 - host_reserve_memory)))
