import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common import gpu_chat_admission, gpu_job_queue
from workflow.domains.hermes_agent.chat_queue_store import enqueue, update
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class ChatAdmissionTests(unittest.TestCase):
    def test_cancel_then_requeue_same_session_end_to_end(self):
        from workflow.domains.hermes_agent import resident_queue
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_root_directory = temporary_root_path / '.local/hermes-agent/sessions'
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            handoff_store_instance = GpuHandoffStore(temporary_root_path / 'handoffs')
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', session_root_directory)
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            original_find_resident = resident_queue.find_session_resident
            original_inspect_resident = resident_queue.inspect_resident
            original_ensure_resident = resident_queue.ensure_session_resident
            launched_job_directories = []
            def record_resident_launch(command_arguments, job_directory_path, service_name, **process_options):
                resident_job_directory = Path(job_directory_path)
                launched_job_directories.append(resident_job_directory)
                (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':service_name,'command':command_arguments}))
                (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            def find_test_resident(session_identifier, **resident_options):
                return original_find_resident(session_identifier, root=resident_root_directory)
            def inspect_test_resident(resident_identifier, session_identifier, **resident_options):
                return original_inspect_resident(resident_identifier, session_identifier, root=resident_root_directory)
            def ensure_test_resident(session_identifier, request_identifier, **resident_options):
                return original_ensure_resident(session_identifier, request_identifier, root=resident_root_directory,
                    handoff_store=handoff_store_instance, launcher=record_resident_launch, **resident_options)
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(resident_queue, 'RESIDENT_ROOT', resident_root_directory), \
                 patch.object(resident_queue, 'find_session_resident', side_effect=find_test_resident), \
                 patch.object(resident_queue, 'inspect_resident', side_effect=inspect_test_resident), \
                 patch.object(resident_queue, 'ensure_session_resident', side_effect=ensure_test_resident), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier,'request_id':'request_123','prompt':'first','model_profile':'qwen3.8-27b'})
                self.assertIsNone(service_manager_instance.dispatch_chat_queue(chat_session_identifier))
                self.assertEqual(len(launched_job_directories), 1)
                first_resident_directory = launched_job_directories[0]
                service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier,'request_id':'request_123','revision':1,'cancel':True})
                self.assertTrue((first_resident_directory / 'cancel.request').is_file())
                self.assertEqual(gpu_job_queue.execute_queued_generation(first_resident_directory), 0)
                self.assertEqual(json.loads((first_resident_directory / 'status.json').read_text())['status'], 'cancelled')
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier,'request_id':'request_456','prompt':'second','model_profile':'qwen3.8-27b'})
                self.assertIsNone(service_manager_instance.dispatch_chat_queue(chat_session_identifier))
                self.assertEqual(len(launched_job_directories), 2)
                self.assertNotEqual(launched_job_directories[0], launched_job_directories[1])
                self.assertEqual(json.loads((launched_job_directories[1] / 'status.json').read_text())['status'], 'queued')

    def test_completed_queued_cancellation_allows_later_resident_only_after_cleanup(self):
        import fcntl
        from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once, inspect_resident
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            active_reservation_directory = queue_root_directory / 'active'
            active_reservation_directory.mkdir(parents=True)
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            chat_session_identifier = 'a' * 32
            resident_request_identifier = gpu_chat_admission.derive_chat_resident_identifier(chat_session_identifier, 'request_123')
            resident_job_directory = resident_root_directory / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':chat_session_identifier},'queue_order_ns':100}))
            (resident_job_directory / 'launch.json').write_text(json.dumps({'id':resident_request_identifier,'state':'accepted'}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'cancelled'}))
            (resident_job_directory / 'cancel.request').touch()
            (resident_job_directory / 'execution.lock').touch()
            def record_resident_launch(command_arguments, job_directory_path, service_name, **process_options):
                pass
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory):
                self.assertEqual(inspect_resident(resident_request_identifier, chat_session_identifier, root=resident_root_directory)['state'], 'released')
                with (resident_job_directory / 'execution.lock').open('a') as execution_lock_stream:
                    fcntl.flock(execution_lock_stream, fcntl.LOCK_EX)
                    self.assertEqual(inspect_resident(resident_request_identifier, chat_session_identifier, root=resident_root_directory)['state'], 'unknown')
                active_reservation_path = active_reservation_directory / 'active.json'
                active_reservation_path.write_text(json.dumps({'path':str(resident_job_directory)}))
                self.assertEqual(inspect_resident(resident_request_identifier, chat_session_identifier, root=resident_root_directory)['state'], 'unknown')
                active_reservation_path.unlink()
                next_resident_record = enqueue_resident_once('next_request_123', chat_session_identifier, root=resident_root_directory, launcher=record_resident_launch)
                self.assertEqual(next_resident_record['state'], 'accepted')

    def test_cancel_queued_resident_preserves_started_or_reserved_models(self):
        from workflow.domains.hermes_agent.resident_queue import cancel_unused_queued_resident
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            active_reservation_directory = queue_root_directory / 'active'
            active_reservation_directory.mkdir(parents=True)
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            chat_session_identifier = 'a' * 32
            resident_request_identifier = gpu_chat_admission.derive_chat_resident_identifier(chat_session_identifier, 'request_123')
            resident_job_directory = resident_root_directory / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':chat_session_identifier},'queue_order_ns':100}))
            (resident_job_directory / 'launch.json').write_text(json.dumps({'id':resident_request_identifier,'state':'accepted'}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            active_reservation_path = active_reservation_directory / 'active.json'
            active_reservation_path.write_text(json.dumps({'path':str(resident_job_directory)}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory):
                self.assertFalse(cancel_unused_queued_resident(chat_session_identifier, 'request_123', 100, root=resident_root_directory))
                active_reservation_path.unlink()
                (resident_job_directory / 'status.json').write_text(json.dumps({'status':'running'}))
                self.assertFalse(cancel_unused_queued_resident(chat_session_identifier, 'request_123', 100, root=resident_root_directory))
                self.assertFalse((resident_job_directory / 'cancel.request').exists())
                (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
                self.assertTrue(cancel_unused_queued_resident(chat_session_identifier, 'request_123', 100, root=resident_root_directory))
                self.assertTrue((resident_job_directory / 'cancel.request').is_file())

    def test_resident_executor_waits_for_host_memory_without_launch(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents/start_test123'
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text('{}')
            (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            queue_root_directory.mkdir(parents=True)
            generated_job_directory = temporary_root_path / '.tmp/test/image/job_123'
            generated_job_directory.mkdir(parents=True)
            (generated_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'image','command':['worker']}))
            generated_ticket_path = queue_root_directory / f'{1:020d}-{os.getpid()}.json'
            generated_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(generated_job_directory)}))
            observed_wait_records = []
            def stop_after_memory_wait(wait_interval_seconds):
                observed_wait_records.append(json.loads((resident_job_directory / 'status.json').read_text()))
                (resident_job_directory / 'cancel.request').touch()
            host_reserve_mib = gpu_job_queue.HOST_MEMORY_RESERVE_KIB // 1024
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(gpu_job_queue, 'read_gpu_memory_domain', return_value='vram'), \
                 patch.object(gpu_job_queue, 'read_gpu_memory', return_value=(98304, 80000)), \
                 patch.object(gpu_job_queue, 'read_host_available_memory', return_value=host_reserve_mib + gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB - 1), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', return_value={'required_memory_mib':32768, 'samples':0}), \
                 patch.object(gpu_job_queue.time, 'sleep', side_effect=stop_after_memory_wait), \
                 patch.object(gpu_job_queue.subprocess, 'Popen') as worker_launch_mock:
                self.assertEqual(gpu_job_queue.execute_queued_generation(resident_job_directory), 0)
                worker_launch_mock.assert_not_called()
            self.assertEqual(len(observed_wait_records), 1)
            self.assertIn('시스템 메모리', observed_wait_records[0]['message'])

    def test_loading_resident_reserves_unconsumed_host_memory(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            active_reservation_directory = queue_root_directory / 'active'
            active_reservation_directory.mkdir(parents=True)
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            existing_resident_directory = resident_root_directory / 'start_existing'
            existing_resident_directory.mkdir(parents=True)
            (existing_resident_directory / 'request.json').write_text(json.dumps({'context':{'session_id':'a' * 32}}))
            active_reservation_record = {'pid':os.getpid(), 'service':'hermes-agent', 'path':str(existing_resident_directory), 'worker_pgid':os.getpid(), 'required_memory_mib':32768}
            (active_reservation_directory / 'existing.json').write_text(json.dumps(active_reservation_record))
            next_resident_directory = resident_root_directory / 'start_next123'
            next_resident_directory.mkdir()
            (next_resident_directory / 'request.json').write_text(json.dumps({'context':{'session_id':'b' * 32}}))
            (next_resident_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
            (next_resident_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            observed_wait_records = []
            def stop_after_reservation_wait(wait_interval_seconds):
                observed_wait_records.append(json.loads((next_resident_directory / 'status.json').read_text()))
                (next_resident_directory / 'cancel.request').touch()
            host_reserve_mib = gpu_job_queue.HOST_MEMORY_RESERVE_KIB // 1024
            remaining_existing_host_mib = gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB - 4096
            available_host_memory_mib = host_reserve_mib + gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB + remaining_existing_host_mib - 1
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(gpu_job_queue, 'read_gpu_memory_domain', return_value='vram'), \
                 patch.object(gpu_job_queue, 'read_gpu_memory', return_value=(98304, 80000)), \
                 patch.object(gpu_job_queue, 'read_host_available_memory', return_value=available_host_memory_mib), \
                 patch.object(gpu_job_queue, 'read_worker_memory', return_value=0), \
                 patch.object(gpu_job_queue, 'read_worker_group_rss_kib', return_value=4096 * 1024), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', return_value={'required_memory_mib':32768, 'samples':0}), \
                 patch.object(gpu_job_queue.time, 'sleep', side_effect=stop_after_reservation_wait), \
                 patch.object(gpu_job_queue.subprocess, 'Popen') as worker_launch_mock:
                self.assertEqual(gpu_job_queue.execute_queued_generation(next_resident_directory), 0)
                worker_launch_mock.assert_not_called()
            self.assertEqual(observed_wait_records[0]['reserved_host_memory_mib'], remaining_existing_host_mib)
            self.assertIn('시스템 메모리', observed_wait_records[0]['message'])

    def test_unprepared_runtime_preserves_chat_for_later_model_launch(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.resident_queue import ensure_session_resident
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            handoff_store_instance = GpuHandoffStore(temporary_root_path / 'handoffs')
            launcher_call_records = []
            def record_model_launch(command_arguments, job_directory_path, service_name, **process_options):
                launcher_call_records.append(job_directory_path)
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', side_effect=[ValueError('runtime unavailable'), None]):
                with self.assertRaisesRegex(ValueError, 'runtime unavailable'):
                    ensure_session_resident('a' * 32, 'request_123', root=resident_root_directory, handoff_store=handoff_store_instance, launcher=record_model_launch, queue_order_ns=100)
                self.assertFalse(queue_root_directory.exists())
                self.assertFalse(launcher_call_records)
                accepted_resident_record = ensure_session_resident('a' * 32, 'request_123', root=resident_root_directory, handoff_store=handoff_store_instance, launcher=record_model_launch, queue_order_ns=100)
                self.assertEqual(accepted_resident_record['state'], 'accepted')
                self.assertEqual(len(launcher_call_records), 1)

    def test_missing_resident_after_preflight_defers_without_launch(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.resident_queue import ensure_session_resident
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready') as runtime_validation_mock, \
                 patch('workflow.domains.hermes_agent.resident_queue.enqueue_resident_once') as resident_launch_mock:
                deferred_resident_record = ensure_session_resident('a' * 32, 'request_123', root=resident_root_directory,
                    handoff_store=GpuHandoffStore(temporary_root_path / 'handoffs'), queue_order_ns=100, defer_runtime_validation=True)
                self.assertEqual(deferred_resident_record['state'], 'retry')
                runtime_validation_mock.assert_not_called()
                resident_launch_mock.assert_not_called()
                self.assertFalse(queue_root_directory.exists())

    def test_first_chat_intent_initializes_active_reservation_directory(self):
        with TemporaryDirectory() as temporary_directory_name:
            queue_root_directory = Path(temporary_directory_name) / 'gpu-queue'
            gpu_chat_admission.register_chat_queue_intent(queue_root_directory, 'a' * 32, 'request_123', 100)
            self.assertTrue((queue_root_directory / 'active').is_dir())

    def test_real_executor_publishes_ticket_before_removing_admission(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            chat_session_identifier = 'a' * 32
            resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', 100)
            resident_job_directory = resident_root_directory / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'queue_order_ns':100, 'context':{'session_id':chat_session_identifier}}))
            (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent', 'command':['worker']}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            original_clear_admission = gpu_chat_admission.clear_chat_admission_locked
            def verify_ticket_before_clear(queue_root_path, resident_identifier, session_identifier, queue_order_nanoseconds):
                self.assertTrue(list(queue_root_path.glob(f'{queue_order_nanoseconds:020d}-*.json')))
                original_clear_admission(queue_root_path, resident_identifier, session_identifier, queue_order_nanoseconds)
                (resident_job_directory / 'cancel.request').touch()
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(gpu_chat_admission, 'clear_chat_admission_locked', side_effect=verify_ticket_before_clear) as clear_admission_mock:
                self.assertEqual(gpu_job_queue.execute_queued_generation(resident_job_directory), 0)
                clear_admission_mock.assert_called_once()
            self.assertEqual(json.loads((resident_job_directory / 'status.json').read_text())['status'], 'cancelled')
            self.assertFalse((queue_root_directory / 'chat-admissions' / (resident_request_identifier + '.json')).exists())
            self.assertFalse(list(queue_root_directory.glob('*.json')))

    def test_mismatched_admission_rolls_back_new_gpu_ticket(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            chat_session_identifier = 'a' * 32
            resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', 100)
            admission_record_path = queue_root_directory / 'chat-admissions' / (resident_request_identifier + '.json')
            original_admission_bytes = admission_record_path.read_bytes()
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents' / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'queue_order_ns':101, 'context':{'session_id':chat_session_identifier}}))
            (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(gpu_job_queue.subprocess, 'Popen') as worker_launch_mock:
                self.assertEqual(gpu_job_queue.execute_queued_generation(resident_job_directory), 1)
                worker_launch_mock.assert_not_called()
            self.assertEqual(json.loads((resident_job_directory / 'status.json').read_text())['status'], 'failed')
            self.assertFalse(list(queue_root_directory.glob('*.json')))
            self.assertEqual(admission_record_path.read_bytes(), original_admission_bytes)

    def test_executor_handoff_excludes_competing_queue_selection(self):
        from threading import Event, Thread
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_store_instance = HermesSessionStore(temporary_root_path / '.local/hermes-agent/sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            with patch('time.time_ns', return_value=100):
                queued_chat_record = enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', queued_chat_record['queue_order_ns'])
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents' / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'queue_order_ns':100, 'context':{'session_id':chat_session_identifier}}))
            (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            generated_job_directory = temporary_root_path / '.tmp/test/image/job_123'
            generated_job_directory.mkdir(parents=True)
            (generated_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'image','command':['worker']}))
            generated_ticket_path = queue_root_directory / f'{200:020d}-{os.getpid()}.json'
            generated_ticket_path.write_text(json.dumps({'pid':os.getpid(), 'path':str(generated_job_directory)}))
            admission_removed_event = Event()
            allow_handoff_release = Event()
            selector_acquired_event = Event()
            selector_finished_event = Event()
            selected_ticket_values = []
            original_clear_admission = gpu_chat_admission.clear_chat_admission_locked
            def pause_after_admission_clear(*clear_arguments):
                original_clear_admission(*clear_arguments)
                admission_removed_event.set()
                if not allow_handoff_release.wait(3):
                    raise RuntimeError('handoff test timed out')
            def stop_before_real_gpu_observation():
                if not selector_finished_event.wait(3):
                    raise RuntimeError('selection test timed out')
                raise ValueError('test stops before GPU observation')
            def select_competing_ticket():
                try:
                    with gpu_chat_admission.hold_gpu_queue_lock(queue_root_directory):
                        selector_acquired_event.set()
                        selected_ticket_values.append(gpu_job_queue.select_runnable_ticket(30, 'vram'))
                finally:
                    selector_finished_event.set()
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue.signal, 'signal'), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', side_effect=lambda service_name,*args:{'required_memory_mib':30 if service_name == 'hermes-agent' else 10}), \
                 patch.object(gpu_job_queue, 'read_gpu_memory_domain', side_effect=stop_before_real_gpu_observation), \
                 patch.object(gpu_chat_admission, 'clear_chat_admission_locked', side_effect=pause_after_admission_clear):
                executor_thread_instance = Thread(target=gpu_job_queue.execute_queued_generation, args=(resident_job_directory,))
                selector_thread_instance = Thread(target=select_competing_ticket)
                executor_thread_instance.start()
                try:
                    self.assertTrue(admission_removed_event.wait(2))
                    selector_thread_instance.start()
                    self.assertFalse(selector_acquired_event.wait(0.1))
                    allow_handoff_release.set()
                    self.assertTrue(selector_finished_event.wait(2))
                    self.assertEqual(selected_ticket_values, [queue_root_directory / f'{100:020d}-{os.getpid()}.json'])
                finally:
                    allow_handoff_release.set()
                    selector_finished_event.set()
                    executor_thread_instance.join(3)
                    if selector_thread_instance.ident is not None:
                        selector_thread_instance.join(3)
                self.assertFalse(executor_thread_instance.is_alive())
                self.assertFalse(selector_thread_instance.is_alive())

    def test_resident_launch_handoff_preserves_common_order(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.resident_queue import ensure_session_resident
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_root_directory = temporary_root_path / '.local/hermes-agent/sessions'
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            session_store_instance = HermesSessionStore(session_root_directory)
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            with patch('time.time_ns', return_value=100):
                queued_chat_record = enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            generated_job_directory = temporary_root_path / '.tmp/test/image/job_123'
            generated_job_directory.mkdir(parents=True)
            (generated_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'image','command':['worker']}))
            queue_root_directory.mkdir(parents=True)
            generated_ticket_path = queue_root_directory / f'{200:020d}-{os.getpid()}.json'
            generated_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(generated_job_directory)}))
            def record_resident_launch(command_arguments, job_directory_path, service_name, **process_options):
                pass
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', side_effect=lambda service_name,*args:{'required_memory_mib':30 if service_name == 'hermes-agent' else 10}):
                resident_receipt_record = ensure_session_resident(chat_session_identifier, queued_chat_record['request_id'], root=resident_root_directory,
                    handoff_store=GpuHandoffStore(temporary_root_path / 'handoffs'), launcher=record_resident_launch,
                    queue_order_ns=queued_chat_record['queue_order_ns'])
                self.assertEqual(resident_receipt_record['state'], 'accepted')
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(30, 'vram'))
                resident_job_directory = resident_root_directory / resident_receipt_record['id']
                (resident_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
                resident_ticket_path = queue_root_directory / f'{100:020d}-{os.getpid()}.json'
                with gpu_chat_admission.hold_gpu_queue_lock(queue_root_directory):
                    resident_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(resident_job_directory)}))
                    gpu_chat_admission.clear_chat_admission_locked(queue_root_directory, resident_receipt_record['id'], chat_session_identifier, queued_chat_record['queue_order_ns'])
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram'), resident_ticket_path)

    def test_earlier_chat_holds_gpu_turn_only_when_it_can_fit(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / '.tmp/gpu-queue'
            queue.mkdir(parents=True)
            store = HermesSessionStore(root / '.local/hermes-agent/sessions')
            session = 'a' * 32
            store.create_session_record(session)
            with patch('time.time_ns', return_value=100):
                row = enqueue(store, session, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            image = root / '.tmp/test/image/job_123'
            image.mkdir(parents=True)
            (image / 'gpu-command.json').write_text(json.dumps({'service':'image','command':['worker']}))
            ticket = queue / f'{200:020d}-{os.getpid()}.json'
            ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(image)}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', side_effect=lambda service,*args:{'required_memory_mib':30 if service == 'hermes-agent' else 10}):
                resident = gpu_chat_admission.begin_chat_admission(queue, session, row['request_id'], row['queue_order_ns'])
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(30, 'vram'))
                self.assertEqual(gpu_job_queue.select_runnable_ticket(10, 'vram'), ticket)
                (queue / 'priority-order').write_text(json.dumps({ticket.name:-1}))
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram'), ticket)
                (queue / 'priority-order').unlink()
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram', available_host_memory_mib=gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB-1), ticket)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(30, 'vram', available_host_memory_mib=gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB))
                update(store, session, row['request_id'], row['revision'], cancel=True)
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram'), ticket)
                with gpu_chat_admission.hold_gpu_queue_lock(queue):
                    gpu_chat_admission.clear_chat_admission_locked(queue, resident, session, row['queue_order_ns'])
                self.assertFalse((queue / 'chat-admissions' / (resident + '.json')).exists())

    def test_admission_uses_same_measured_memory_profile_as_resident_ticket(self):
        from workflow.common import gpu_memory_history
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_store_instance = HermesSessionStore(temporary_root_path / '.local/hermes-agent/sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            with patch('time.time_ns', return_value=100):
                queued_chat_record = enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents' / 'profile-check'
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b'}))
            resident_command_identity = gpu_memory_history.identify_execution_command(['python', '/repo/hermes_agent/resident_worker.py'], resident_job_directory, 'vram')
            generated_job_directory = temporary_root_path / '.tmp/test/image/job_123'
            generated_job_directory.mkdir(parents=True)
            (generated_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'image', 'command':['worker']}))
            gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', queued_chat_record['queue_order_ns'])
            generated_ticket_path = queue_root_directory / f'{200:020d}-{os.getpid()}.json'
            generated_ticket_path.write_text(json.dumps({'pid':os.getpid(), 'path':str(generated_job_directory)}))
            original_memory_estimator = gpu_memory_history.estimate_required_memory
            def estimate_shared_memory(service_name_value, configured_memory_floor, command_identity_value):
                if service_name_value == 'image':
                    return {'required_memory_mib':10000}
                return original_memory_estimator(service_name_value, configured_memory_floor, command_identity_value)
            with patch.object(gpu_memory_history, 'MEMORY_HISTORY_DIRECTORY', temporary_root_path / 'memory-history'), \
                 patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', side_effect=estimate_shared_memory):
                gpu_memory_history.save_memory_observation('hermes-agent', resident_job_directory, 40000, 2, 'completed', command_identity_name=resident_command_identity)
                self.assertEqual(gpu_job_queue.select_runnable_ticket(35000, 'vram'), generated_ticket_path)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(40000, 'vram'))

    def test_expired_admission_does_not_block_other_work(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / '.tmp/gpu-queue'
            store = HermesSessionStore(root / '.local/hermes-agent/sessions')
            session = 'a' * 32
            store.create_session_record(session)
            with patch('time.time_ns', return_value=100):
                row = enqueue(store, session, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000):
                gpu_chat_admission.begin_chat_admission(queue, session, row['request_id'], row['queue_order_ns'])
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000+gpu_chat_admission._ADMISSION_LEASE_NANOSECONDS+1):
                self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue, root), [])

    def test_recent_resident_progress_extends_admission_but_stalls_do_not(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_store_instance = HermesSessionStore(temporary_root_path / '.local/hermes-agent/sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            with patch('time.time_ns', return_value=100):
                queued_chat_record = enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            with patch.object(gpu_chat_admission.time, 'time_ns', return_value=100_000_000_000), \
                 patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000):
                resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', queued_chat_record['queue_order_ns'])
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents' / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            resident_request_path = resident_job_directory / 'request.json'
            resident_request_path.write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':chat_session_identifier},'queue_order_ns':100}))
            os.utime(resident_request_path, ns=(102_000_000_000, 102_000_000_000))
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000 + 6_000_000_000), \
                 patch.object(gpu_chat_admission.time, 'time_ns', return_value=106_000_000_000):
                live_admission_records = gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path)
                self.assertEqual([admission_record_value['resident_id'] for admission_record_value in live_admission_records], [resident_request_identifier])
                resident_request_path.write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':'b' * 32},'queue_order_ns':100}))
                os.utime(resident_request_path, ns=(102_000_000_000, 102_000_000_000))
                self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path), [])
                resident_request_path.write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':chat_session_identifier},'queue_order_ns':100}))
                os.utime(resident_request_path, ns=(102_000_000_000, 102_000_000_000))
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000 + 8_000_000_000), \
                 patch.object(gpu_chat_admission.time, 'time_ns', return_value=108_000_000_000):
                self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path), [])

    def test_gateway_exit_keeps_recent_locked_resident_admission(self):
        import fcntl
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            session_store_instance = HermesSessionStore(temporary_root_path / '.local/hermes-agent/sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            with patch('time.time_ns', return_value=100):
                queued_chat_record = enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            with patch.object(gpu_chat_admission.time, 'time_ns', return_value=100_000_000_000), \
                 patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000):
                resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, chat_session_identifier, 'request_123', queued_chat_record['queue_order_ns'])
            resident_job_directory = temporary_root_path / '.local/hermes-agent/residents' / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            resident_request_path = resident_job_directory / 'request.json'
            resident_request_path.write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':chat_session_identifier},'queue_order_ns':100}))
            os.utime(resident_request_path, ns=(102_000_000_000, 102_000_000_000))
            execution_lock_path = resident_job_directory / 'execution.lock'
            execution_lock_path.touch()
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000 + 6_000_000_000), \
                 patch.object(gpu_chat_admission.time, 'time_ns', return_value=106_000_000_000), \
                 patch.object(gpu_chat_admission.os, 'kill', side_effect=ProcessLookupError):
                with execution_lock_path.open('a+') as execution_lock_stream:
                    fcntl.flock(execution_lock_stream, fcntl.LOCK_EX)
                    live_admission_records = gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path)
                    self.assertEqual([admission_record_value['resident_id'] for admission_record_value in live_admission_records], [resident_request_identifier])
                self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path), [])

    def test_admission_lease_begins_after_gpu_lock_is_acquired(self):
        from contextlib import contextmanager
        with TemporaryDirectory() as temporary_directory_name:
            queue_root_directory = Path(temporary_directory_name) / 'gpu-queue'
            original_queue_lock = gpu_chat_admission.hold_gpu_queue_lock
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=9000) as monotonic_clock_mock:
                @contextmanager
                def observe_queue_lock(queue_directory_path):
                    with original_queue_lock(queue_directory_path) as locked_queue_path:
                        self.assertEqual(monotonic_clock_mock.call_count, 0)
                        yield locked_queue_path
                with patch.object(gpu_chat_admission, 'hold_gpu_queue_lock', side_effect=observe_queue_lock):
                    resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, 'a' * 32, 'request_123', 100)
            admission_record_path = queue_root_directory / 'chat-admissions' / (resident_request_identifier + '.json')
            self.assertEqual(json.loads(admission_record_path.read_text())['created_monotonic_ns'], 9000)

    def test_expired_or_interrupted_records_do_not_exhaust_live_admission_limit(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            with patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000):
                resident_request_identifier = gpu_chat_admission.begin_chat_admission(queue_root_directory, 'a' * 32, 'request_123', 100)
            admission_directory_path = queue_root_directory / 'chat-admissions'
            expired_admission_path = admission_directory_path / (resident_request_identifier + '.json')
            interrupted_record_path = admission_directory_path / ('start_' + 'a' * 64 + '.json.' + 'b' * 32 + '.tmp')
            with patch.object(Path, 'iterdir', return_value=iter([expired_admission_path] * 1001 + [interrupted_record_path] * 1001)), \
                 patch.object(gpu_chat_admission.time, 'monotonic_ns', return_value=1000 + gpu_chat_admission._ADMISSION_LEASE_NANOSECONDS + 1):
                self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path), [])

    def test_malformed_live_owner_fails_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / '.tmp/gpu-queue'
            store = HermesSessionStore(root / '.local/hermes-agent/sessions')
            session = 'a' * 32
            store.create_session_record(session)
            with patch('time.time_ns', return_value=100):
                row = enqueue(store, session, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)['request']
            resident = gpu_chat_admission.begin_chat_admission(queue, session, row['request_id'], row['queue_order_ns'])
            marker = queue / 'chat-admissions' / (resident + '.json')
            record = json.loads(marker.read_text())
            record['pid'] = True
            marker.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                gpu_chat_admission.list_live_chat_admissions(queue, root)

    def test_interrupted_atomic_write_does_not_block_other_tickets(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            admission_directory_path = queue_root_directory / 'chat-admissions'
            admission_directory_path.mkdir(parents=True)
            temporary_record_name = 'start_' + 'a' * 64 + '.json.' + 'b' * 32 + '.tmp'
            (admission_directory_path / temporary_record_name).write_text('{')
            self.assertEqual(gpu_chat_admission.list_live_chat_admissions(queue_root_directory, temporary_root_path), [])
