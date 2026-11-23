from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.service import HermesServiceManager


class QueueBeforeModelTests(unittest.TestCase):
    def setUp(self):
        from workflow.common import gpu_job_queue
        queue_temporary_directory = TemporaryDirectory()
        self.addCleanup(queue_temporary_directory.cleanup)
        queue_directory_patch = patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', Path(queue_temporary_directory.name) / 'gpu-queue')
        queue_directory_patch.start()
        self.addCleanup(queue_directory_patch.stop)
        resident_lookup_patch = patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value=None)
        resident_lookup_patch.start()
        self.addCleanup(resident_lookup_patch.stop)
        resident_root_patch = patch('workflow.domains.hermes_agent.resident_queue.RESIDENT_ROOT', Path(queue_temporary_directory.name) / 'residents')
        resident_root_patch.start()
        self.addCleanup(resident_root_patch.stop)
        runtime_validation_patch = patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
        runtime_validation_patch.start()
        self.addCleanup(runtime_validation_patch.stop)

    def test_slow_model_preflight_does_not_block_submission_or_cancelled_request(self):
        from threading import Event, Thread
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'first', 'model_profile':'qwen3.8-27b'})
            preflight_started_event = Event()
            preflight_release_event = Event()
            def wait_for_preflight(model_profile_value):
                preflight_started_event.set()
                if not preflight_release_event.wait(3):
                    raise RuntimeError('preflight test timed out')
            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', side_effect=wait_for_preflight), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident') as resident_launch_mock:
                dispatcher_thread_instance = Thread(target=service_manager_instance.dispatch_chat_queue, args=(chat_session_identifier,))
                dispatcher_thread_instance.start()
                try:
                    self.assertTrue(preflight_started_event.wait(2))
                    second_request_receipt = service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_456', 'prompt':'second', 'model_profile':'qwen3.8-27b'})
                    self.assertTrue(second_request_receipt['queued'])
                    cancelled_request_record = service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier, 'request_id':'request_123', 'revision':1, 'cancel':True})
                    self.assertEqual(cancelled_request_record['state'], 'cancelled')
                finally:
                    preflight_release_event.set()
                    dispatcher_thread_instance.join(3)
                self.assertFalse(dispatcher_thread_instance.is_alive())
                resident_launch_mock.assert_not_called()

    def test_stopped_dispatcher_does_not_launch_after_slow_preflight(self):
        from threading import Event
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'})
            preflight_started_event = Event()
            preflight_release_event = Event()
            dispatcher_finished_event = Event()
            original_dispatch_function = service_manager_instance.dispatch_chat_queue
            def wait_for_preflight(model_profile_value):
                preflight_started_event.set()
                preflight_release_event.wait(3)
            def observe_dispatch_completion(chat_session_identifier, **dispatch_options):
                try:
                    return original_dispatch_function(chat_session_identifier, **dispatch_options)
                finally:
                    dispatcher_finished_event.set()
            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', side_effect=wait_for_preflight), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident') as resident_launch_mock, \
                 patch.object(service_manager_instance, 'dispatch_chat_queue', side_effect=observe_dispatch_completion):
                dispatcher_stop_event = service_manager_instance.start_chat_queue_dispatcher()
                try:
                    self.assertTrue(preflight_started_event.wait(2))
                    dispatcher_stop_event.set()
                    preflight_release_event.set()
                    self.assertTrue(dispatcher_finished_event.wait(2))
                    resident_launch_mock.assert_not_called()
                    session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
                    self.assertEqual(session_store_instance.read_session_record(chat_session_identifier)['chat_queue'][0]['state'], 'queued')
                finally:
                    dispatcher_stop_event.set()
                    preflight_release_event.set()
                    service_manager_instance.chat_queue_wakeup.set()

    def test_interrupted_terminal_intent_cleanup_recovers_without_removing_pending(self):
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            for chat_request_identifier in ('request_123', 'request_456'):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':chat_request_identifier, 'prompt':'hello', 'model_profile':'qwen3.8-27b'})
            intent_directory_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents'
            cancelled_intent_path = intent_directory_path / (derive_chat_resident_identifier(chat_session_identifier, 'request_123') + '.json')
            pending_intent_path = intent_directory_path / (derive_chat_resident_identifier(chat_session_identifier, 'request_456') + '.json')
            with patch('workflow.common.gpu_chat_admission.retire_chat_queue_intent', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier, 'request_id':'request_123', 'revision':1, 'cancel':True})
            self.assertTrue(cancelled_intent_path.exists())
            service_manager_instance.retire_terminal_chat_queue_intents()
            self.assertFalse(cancelled_intent_path.exists())
            self.assertTrue(pending_intent_path.exists())

    def test_cancelling_chat_retires_its_shared_queue_intent(self):
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            queued_request_payload = {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'}
            queued_request_receipt = service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            queue_intent_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents' / (derive_chat_resident_identifier(chat_session_identifier, 'request_123') + '.json')
            self.assertTrue(queue_intent_path.exists())
            updated_queue_record = service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier,'request_id':'request_123','revision':queued_request_receipt['request']['revision'],'cancel':True})
            self.assertEqual(updated_queue_record['state'], 'cancelled')
            self.assertFalse(queue_intent_path.exists())
            with self.assertRaisesRegex(ValueError, '취소된'):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)

    def test_last_cancelled_chat_stops_only_its_unstarted_resident(self):
        import json
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            resident_root_directory = temporary_root_path / '.local/hermes-agent/residents'
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            first_request_receipt = service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'first', 'model_profile':'qwen3.8-27b'})
            service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_456', 'prompt':'second', 'model_profile':'qwen3.8-27b'})
            resident_request_identifier = derive_chat_resident_identifier(chat_session_identifier, 'request_123')
            resident_job_directory = resident_root_directory / resident_request_identifier
            resident_job_directory.mkdir(parents=True)
            (resident_job_directory / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b', 'context':{'session_id':chat_session_identifier}, 'queue_order_ns':first_request_receipt['request']['queue_order_ns']}))
            (resident_job_directory / 'launch.json').write_text(json.dumps({'id':resident_request_identifier, 'state':'accepted'}))
            (resident_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
                 patch('workflow.domains.hermes_agent.resident_queue.RESIDENT_ROOT', resident_root_directory):
                service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier, 'request_id':'request_123', 'revision':1, 'cancel':True})
                self.assertFalse((resident_job_directory / 'cancel.request').exists())
                service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier, 'request_id':'request_456', 'revision':1, 'cancel':True})
                self.assertTrue((resident_job_directory / 'cancel.request').is_file())

    def test_retry_of_edited_dispatched_request_uses_original_receipt(self):
        from workflow.domains.hermes_agent.chat_queue_store import transition
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            queued_request_payload = {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'original', 'model_profile':'qwen3.8-27b'}
            service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            service_manager_instance.execute_hermes_command('hermes-chat-queue-update', {'session_id':chat_session_identifier, 'request_id':'request_123', 'revision':1, 'prompt':'edited'})
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            transition(session_store_instance, chat_session_identifier, 'request_123', 'queued', 'dispatching')
            session_store_instance.append_session_request(chat_session_identifier, 'request_123', 'edited', model_profile='qwen3.8-27b')
            transition(session_store_instance, chat_session_identifier, 'request_123', 'dispatching', 'dispatched', 'job_123')
            duplicate_request_receipt = service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            self.assertTrue(duplicate_request_receipt['duplicate'])
            self.assertFalse(duplicate_request_receipt['queued'])
            with self.assertRaisesRegex(ValueError, '같은 접수 ID'):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {**queued_request_payload, 'prompt':'different'})

    def test_dispatch_recovers_interrupted_shared_intent_registration(self):
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            queued_request_payload = {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'}
            with patch('workflow.common.gpu_chat_admission.register_chat_queue_intent', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            self.assertEqual(session_store_instance.read_session_record(chat_session_identifier)['chat_queue'][0]['state'], 'queued')
            with patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}), \
                 patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'queued'}):
                self.assertIsNone(service_manager_instance.dispatch_chat_queue(chat_session_identifier))
            queue_intent_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents' / (derive_chat_resident_identifier(chat_session_identifier, 'request_123') + '.json')
            self.assertTrue(queue_intent_path.is_file())

    def test_interrupted_intent_recovers_even_when_model_is_unavailable(self):
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
            queued_request_payload = {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'}
            with patch('workflow.common.gpu_chat_admission.register_chat_queue_intent', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', side_effect=ValueError('model unavailable')):
                with self.assertRaisesRegex(ValueError, 'model unavailable'):
                    service_manager_instance.dispatch_chat_queue(chat_session_identifier)
            queue_intent_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents' / (derive_chat_resident_identifier(chat_session_identifier, 'request_123') + '.json')
            self.assertTrue(queue_intent_path.is_file())

    def test_legacy_pending_request_enters_common_queue_before_model_load(self):
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
        from workflow.domains.hermes_agent.chat_queue_store import enqueue
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, chat_session_identifier, 'request_123', 'legacy request')
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            with patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}) as resident_launch_mock, \
                 patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'queued'}):
                self.assertIsNone(service_manager_instance.dispatch_chat_queue(chat_session_identifier))
            upgraded_request_record = session_store_instance.read_session_record(chat_session_identifier)['chat_queue'][0]
            self.assertTrue(upgraded_request_record['require_resident'])
            self.assertEqual(upgraded_request_record['state'], 'queued')
            queue_intent_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents' / (derive_chat_resident_identifier(chat_session_identifier, 'request_123') + '.json')
            self.assertTrue(queue_intent_path.is_file())
            self.assertEqual(resident_launch_mock.call_args.kwargs['queue_order_ns'], upgraded_request_record['queue_order_ns'])

    def test_legacy_implicit_model_retry_matches_without_changing_original_record(self):
        from workflow.domains.hermes_agent.chat_queue_store import enqueue
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, chat_session_identifier, 'request_123', 'legacy request')
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            queued_request_payload = {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'legacy request', 'model_profile':'qwen3.8-27b'}
            duplicate_request_receipt = service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)
            self.assertTrue(duplicate_request_receipt['duplicate'])
            self.assertEqual(duplicate_request_receipt['request']['model_profile'], 'qwen3.8-27b')
            self.assertNotIn('model_profile', session_store_instance.read_session_record(chat_session_identifier)['chat_queue'][0])
            self.assertTrue(enqueue(session_store_instance, chat_session_identifier, 'request_123', 'legacy request')['duplicate'])
            with self.assertRaises(ValueError):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {**queued_request_payload, 'prompt':'different'})
            session_store_instance.append_session_request(chat_session_identifier, 'request_123', 'legacy request')
            with self.assertRaises(ValueError):
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', queued_request_payload)

    def test_new_receipt_wakes_dispatcher_without_poll_delay(self):
        from threading import Event
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            called = Event()
            with patch.object(manager, 'dispatch_chat_queue', side_effect=lambda *args, **kwargs:called.set()):
                stop = manager.start_chat_queue_dispatcher()
                try:
                    manager.execute_hermes_command('hermes-session-queue-submit', {'session_id':session,'request_id':'request_123','prompt':'hello','model_profile':'qwen3.8-27b'})
                    self.assertTrue(called.wait(2))
                finally:
                    stop.set()
                    manager.chat_queue_wakeup.set()

    def test_slow_session_does_not_block_another_ready_session(self):
        from threading import Event
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            first_session_identifier, second_session_identifier = 'a' * 32, 'b' * 32
            for chat_session_identifier in (first_session_identifier, second_session_identifier):
                service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'})
            first_session_started = Event()
            first_session_release = Event()
            second_session_started = Event()
            def run_test_dispatch(chat_session_identifier, **dispatch_options):
                if chat_session_identifier == first_session_identifier:
                    first_session_started.set()
                    first_session_release.wait(3)
                else:
                    second_session_started.set()
            with patch.object(service_manager_instance, 'dispatch_chat_queue', side_effect=run_test_dispatch):
                dispatcher_stop_event = service_manager_instance.start_chat_queue_dispatcher()
                try:
                    self.assertTrue(first_session_started.wait(2))
                    self.assertTrue(second_session_started.wait(2))
                finally:
                    first_session_release.set()
                    dispatcher_stop_event.set()
                    service_manager_instance.chat_queue_wakeup.set()

    def test_dispatcher_limits_concurrency_and_rotates_waiting_sessions(self):
        from threading import Event, Lock
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            service_manager_instance = HermesServiceManager(temporary_root_path / 'jobs', temporary_root_path / 'sessions')
            session_identifiers_list = [character_value * 32 for character_value in ('a', 'b', 'c')]
            for chat_session_identifier in session_identifiers_list:
                service_manager_instance.execute_hermes_command('hermes-session-create', {'session_id':chat_session_identifier})
                service_manager_instance.execute_hermes_command('hermes-session-queue-submit', {'session_id':chat_session_identifier, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'})
            dispatch_started_events = {chat_session_identifier:Event() for chat_session_identifier in session_identifiers_list}
            dispatch_release_events = {chat_session_identifier:Event() for chat_session_identifier in session_identifiers_list}
            dispatch_count_records = {chat_session_identifier:0 for chat_session_identifier in session_identifiers_list}
            dispatch_count_lock = Lock()
            def block_test_dispatch(chat_session_identifier, **dispatch_options):
                with dispatch_count_lock:
                    dispatch_count_records[chat_session_identifier] += 1
                dispatch_started_events[chat_session_identifier].set()
                dispatch_release_events[chat_session_identifier].wait(3)
            with patch.object(service_manager_instance, 'dispatch_chat_queue', side_effect=block_test_dispatch):
                dispatcher_stop_event = service_manager_instance.start_chat_queue_dispatcher()
                try:
                    self.assertTrue(dispatch_started_events[session_identifiers_list[0]].wait(2))
                    self.assertTrue(dispatch_started_events[session_identifiers_list[1]].wait(2))
                    self.assertFalse(dispatch_started_events[session_identifiers_list[2]].is_set())
                    service_manager_instance.chat_queue_wakeup.set()
                    dispatch_release_events[session_identifiers_list[0]].set()
                    self.assertTrue(dispatch_started_events[session_identifiers_list[2]].wait(4))
                    with dispatch_count_lock:
                        self.assertEqual(dispatch_count_records[session_identifiers_list[1]], 1)
                finally:
                    dispatcher_stop_event.set()
                    for dispatch_release_event in dispatch_release_events.values():
                        dispatch_release_event.set()
                    service_manager_instance.chat_queue_wakeup.set()

    def test_model_preparation_can_start_while_prior_context_is_pending(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            payload = {'session_id':session, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'}
            manager.execute_hermes_command('hermes-session-queue-submit', payload)
            self.assertTrue(manager.chat_queue_wakeup.is_set())
            with patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}) as resident, \
                 patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'ready'}), \
                 patch.object(manager, 'ensure_context_operation_finished', side_effect=ValueError('대화 정리 중')), \
                 patch.object(manager, 'submit_hermes_session_message_locked') as submit:
                with self.assertRaisesRegex(ValueError, '대화 정리'):
                    manager.dispatch_chat_queue(session)
                resident.assert_called_once()
                submit.assert_not_called()

    def test_verified_resident_is_visible_in_bounded_gpu_queue(self):
        import json
        import os
        from workflow.common import gpu_job_queue
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / '.tmp/gpu-queue'
            queue.mkdir(parents=True)
            resident = root / '.local/hermes-agent/residents/start_123'
            resident.mkdir(parents=True)
            (resident / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':'a'*32}}))
            (resident / 'launch.json').write_text(json.dumps({'id':'start_123','state':'accepted'}))
            (resident / 'status.json').write_text(json.dumps({'status':'queued'}))
            command = {'service':'hermes-agent','command':['python',str(root / 'workflow/domains/hermes_agent/resident_worker.py'),str(resident)]}
            (resident / 'gpu-command.json').write_text(json.dumps(command))
            (queue / '00000000000000000100-1.json').write_text(json.dumps({'pid':os.getpid(),'path':str(resident)}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue):
                rows = gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True)['jobs']
                self.assertEqual([(row['id'], row['service']) for row in rows], [('start_123', 'hermes-agent')])
                command['service'] = 'image'
                (resident / 'gpu-command.json').write_text(json.dumps(command))
                with self.assertRaisesRegex(ValueError, '상주 모델 대기 명령'):
                    gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True)
                (resident / 'launch.json').write_text(json.dumps({'id':'different','state':'accepted'}))
                with self.assertRaises(ValueError):
                    gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True)

    def test_queue_preserves_existing_twelve_thousand_character_limit(self):
        from workflow.domains.hermes_agent.chat_queue_store import enqueue, update
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with TemporaryDirectory() as directory:
            store = HermesSessionStore(directory)
            session = 'a' * 32
            store.create_session_record(session)
            row = enqueue(store, session, 'request_123', 'x' * 12000, 'qwen3.8-27b', require_resident=True)['request']
            self.assertEqual(len(row['prompt']), 12000)
            self.assertEqual(len(update(store, session, 'request_123', row['revision'], prompt='y' * 12000)['prompt']), 12000)
            with self.assertRaises(ValueError):
                enqueue(store, session, 'request_456', 'x' * 12001, 'qwen3.8-27b', require_resident=True)

    def test_resident_ticket_uses_original_chat_order(self):
        import json
        from workflow.common import gpu_job_queue
        with TemporaryDirectory() as directory:
            root = Path(directory)
            resident = root / '.local/hermes-agent/residents/start_123'
            resident.mkdir(parents=True)
            (resident / 'request.json').write_text(json.dumps({'queue_order_ns':100}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root):
                self.assertEqual(gpu_job_queue.queue_ticket_order_ns(resident, 'hermes-agent', 300), 100)
                self.assertEqual(gpu_job_queue.queue_ticket_order_ns(resident, 'image', 300), 300)
                (resident / 'request.json').write_text(json.dumps({'queue_order_ns':301}))
                with self.assertRaises(ValueError):
                    gpu_job_queue.queue_ticket_order_ns(resident, 'hermes-agent', 300)

    def test_resident_receipt_persists_order_before_executor_launch(self):
        import json
        from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once
        with TemporaryDirectory() as directory:
            root = Path(directory)
            observed = []
            def launch(command, job_directory, service, **kwargs):
                observed.append(json.loads((Path(job_directory) / 'request.json').read_text())['queue_order_ns'])
            with patch('time.time_ns', return_value=300):
                result = enqueue_resident_once('request_123', 'a'*32, root=root, launcher=launch, queue_order_ns=100)
                duplicate = enqueue_resident_once('request_123', 'a'*32, root=root, launcher=launch, queue_order_ns=100)
                with self.assertRaises(ValueError):
                    enqueue_resident_once('request_456', 'a'*32, root=root, launcher=launch, queue_order_ns=301)
            self.assertFalse(result['duplicate'])
            self.assertTrue(duplicate['duplicate'])
            self.assertEqual(observed, [100])

    def test_shared_gpu_order_uses_chat_receipt_time_and_skips_unfit_work(self):
        import json
        import os
        from workflow.common import gpu_job_queue
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / 'queue'
            queue.mkdir()
            resident = root / '.local/hermes-agent/residents/start_123'
            resident.mkdir(parents=True)
            (resident / 'request.json').write_text(json.dumps({'queue_order_ns':100, 'context':{'session_id':'a'*32}}))
            (resident / 'gpu-command.json').write_text(json.dumps({'command':['worker'], 'service':'hermes-agent'}))
            image = root / 'image'
            image.mkdir()
            (image / 'gpu-command.json').write_text(json.dumps({'command':['worker'], 'service':'image'}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue), \
                 patch.object(gpu_job_queue, 'estimate_required_memory', side_effect=lambda service, *args: {'required_memory_mib':30 if service == 'hermes-agent' else 10}):
                order = gpu_job_queue.queue_ticket_order_ns(resident, 'hermes-agent', 300)
                chat_ticket = queue / f'{order:020d}-{os.getpid()}.json'
                image_ticket = queue / f'{200:020d}-{os.getpid()}.json'
                for path, job in ((chat_ticket, resident), (image_ticket, image)):
                    path.write_text(json.dumps({'pid':os.getpid(), 'path':str(job)}))
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram'), chat_ticket)
                self.assertEqual(gpu_job_queue.select_runnable_ticket(10, 'vram'), image_ticket)
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram', available_host_memory_mib=gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB-1), image_ticket)
                self.assertEqual(gpu_job_queue.select_runnable_ticket(30, 'vram', available_host_memory_mib=gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB), chat_ticket)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(9, 'vram'))

    def test_sessions_are_ordered_by_first_pending_request_time(self):
        import json
        from workflow.domains.hermes_agent.service import ordered_pending_chat_sessions
        with TemporaryDirectory() as directory:
            root = Path(directory)
            records = {
                'a' * 32: [{'state':'queued', 'created_at':'2026-11-23T09:00:00+09:00'}],
                'b' * 32: [{'state':'queued', 'created_at':'2026-11-22T23:30:00+00:00'}],
                'c' * 32: [{'state':'queued', 'created_at':'invalid'}],
                'd' * 32: [{'state':'dispatched', 'created_at':'2026-11-22T20:00:00+00:00'},
                           {'state':'dispatching', 'created_at':'2026-11-23T00:15:00+00:00'}],
            }
            for session, rows in records.items():
                (root / (session + '.json')).write_text(json.dumps({'chat_queue':rows}))
            self.assertEqual(ordered_pending_chat_sessions(root), ['b' * 32, 'a' * 32, 'd' * 32])
            records['a' * 32] = [{'state':'queued', 'created_at':'2026-11-23T00:00:00+00:00', 'queue_order_ns':2}]
            records['b' * 32] = [{'state':'queued', 'created_at':'2026-11-23T00:00:00+00:00', 'queue_order_ns':1}]
            for session in ('a' * 32, 'b' * 32):
                (root / (session + '.json')).write_text(json.dumps({'chat_queue':records[session]}))
            self.assertEqual(ordered_pending_chat_sessions(root)[:2], ['b' * 32, 'a' * 32])

    def test_request_is_saved_without_gpu_then_dispatched_after_resident_acceptance(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            payload = {'session_id':session, 'request_id':'request_123', 'prompt':'hello', 'model_profile':'qwen3.8-27b'}
            with patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', side_effect=ValueError('GPU 양도 진행 중')) as resident:
                first = manager.execute_hermes_command('hermes-session-queue-submit', payload)
                second = manager.execute_hermes_command('hermes-session-queue-submit', payload)
                self.assertTrue(first['queued'])
                self.assertTrue(second['duplicate'])
                self.assertEqual(first['request']['queue_order_ns'], second['request']['queue_order_ns'])
                from workflow.common import gpu_job_queue
                from workflow.common.gpu_chat_admission import derive_chat_resident_identifier
                queue_intent_path = gpu_job_queue.GPU_QUEUE_DIRECTORY / 'chat-intents' / (derive_chat_resident_identifier(session, 'request_123') + '.json')
                self.assertTrue(queue_intent_path.is_file())
                resident.assert_not_called()
                with self.assertRaisesRegex(ValueError, 'GPU 양도'):
                    manager.dispatch_chat_queue(session)
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            store = HermesSessionStore(root / 'sessions')
            self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'queued')
            with patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}) as resident, \
                 patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'queued'}) as inspect, \
                 patch.object(manager, 'submit_hermes_session_message_locked', return_value={'job_id':'2026-11-23_08-00-00-12345678'}) as submit:
                self.assertIsNone(manager.dispatch_chat_queue(session))
                self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'queued')
                submit.assert_not_called()
                inspect.return_value = {'state':'unknown'}
                with self.assertRaisesRegex(ValueError, '예약'):
                    manager.dispatch_chat_queue(session)
                self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'queued')
                submit.assert_not_called()
                inspect.return_value = {'state':'ready'}
                manager.dispatch_chat_queue(session)
                self.assertEqual(resident.call_count, 3)
                resident.assert_called_with(session, 'request_123', queue_order_ns=first['request']['queue_order_ns'], runtime_prevalidated=True, defer_runtime_validation=True)
            self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'dispatched')
            self.assertFalse(queue_intent_path.exists())
