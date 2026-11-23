import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.chat_queue_store import enqueue, transition, update
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class ChatQueueStoreTests(unittest.TestCase):
    def setUp(self):
        from workflow.common import gpu_job_queue
        queue_temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(queue_temporary_directory.cleanup)
        queue_directory_patch = patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', Path(queue_temporary_directory.name) / 'gpu-queue')
        queue_directory_patch.start()
        self.addCleanup(queue_directory_patch.stop)
        for patch_target_name, patch_return_value in (
                ('workflow.domains.hermes_agent.resident_queue.find_session_resident', None),
                ('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', None),
                ('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', {'state':'accepted','id':'resident_123'}),
                ('workflow.domains.hermes_agent.resident_queue.inspect_resident', {'state':'ready'})):
            current_test_patch = patch(patch_target_name, return_value=patch_return_value)
            current_test_patch.start()
            self.addCleanup(current_test_patch.stop)

    def test_legacy_upgrade_preserves_order_and_already_submitted_work(self):
        from datetime import datetime, timezone
        from workflow.domains.hermes_agent.chat_queue_store import prepare_legacy_chat_request
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            session_store_instance = HermesSessionStore(Path(temporary_directory_name))
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            original_request_record = enqueue(session_store_instance, chat_session_identifier, 'request_01', 'original')['request']
            upgraded_request_record = prepare_legacy_chat_request(session_store_instance, chat_session_identifier)
            request_created_time = datetime.fromisoformat(original_request_record['created_at'])
            request_time_delta = request_created_time - datetime(1970, 1, 1, tzinfo=timezone.utc)
            self.assertEqual(upgraded_request_record['queue_order_ns'], (request_time_delta.days * 86400 + request_time_delta.seconds) * 1_000_000_000 + request_time_delta.microseconds * 1000)
            self.assertTrue(upgraded_request_record['require_resident'])
            self.assertEqual(upgraded_request_record['revision'], original_request_record['revision'])
            self.assertTrue(enqueue(session_store_instance, chat_session_identifier, 'request_01', 'original')['duplicate'])
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            session_store_instance = HermesSessionStore(Path(temporary_directory_name))
            session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, chat_session_identifier, 'request_02', 'existing', 'qwen3.8-27b')
            session_store_instance.append_session_request(chat_session_identifier, 'request_02', 'existing', model_profile='qwen3.8-27b')
            self.assertNotIn('require_resident', prepare_legacy_chat_request(session_store_instance, chat_session_identifier))
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            session_store_instance = HermesSessionStore(Path(temporary_directory_name))
            session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, chat_session_identifier, 'request_03', 'legacy model', 'qwen3.5-4b')
            self.assertNotIn('require_resident', prepare_legacy_chat_request(session_store_instance, chat_session_identifier))

    def test_legacy_upgrade_does_not_overwrite_unknown_order(self):
        import json
        from workflow.domains.hermes_agent.chat_queue_store import prepare_legacy_chat_request
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            session_store_instance = HermesSessionStore(Path(temporary_directory_name))
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, chat_session_identifier, 'request_01', 'original')
            session_record_path = Path(temporary_directory_name) / (chat_session_identifier + '.json')
            session_queue_record = json.loads(session_record_path.read_text())
            session_queue_record['chat_queue'][0]['queue_order_ns'] = 42
            session_record_path.write_text(json.dumps(session_queue_record))
            previous_record_bytes = session_record_path.read_bytes()
            with self.assertRaisesRegex(ValueError, '대기 순서'):
                prepare_legacy_chat_request(session_store_instance, chat_session_identifier)
            self.assertEqual(session_record_path.read_bytes(), previous_record_bytes)
    def test_replayed_queue_update_can_change_a_revision_only_once(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_01', '원래 요청')

            def attempt():
                try:
                    return update(store, session, 'request_01', 1, '변경 요청')
                except ValueError:
                    return None

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda _: attempt(), range(2)))
            self.assertEqual(sum(response is not None for response in responses), 1)
            row = HermesSessionStore(Path(root)).read_session_record(session)['chat_queue'][0]
            self.assertEqual((row['revision'], row['prompt'], row['state']), (2, '변경 요청', 'queued'))

            def cancel():
                try:
                    return update(store, session, 'request_01', 2, cancel=True)
                except ValueError:
                    return None

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda _: cancel(), range(2)))
            self.assertEqual(sum(response is not None for response in responses), 1)
            row = HermesSessionStore(Path(root)).read_session_record(session)['chat_queue'][0]
            self.assertEqual((row['revision'], row['prompt'], row['state']), (3, '변경 요청', 'cancelled'))

    def test_late_edit_cannot_change_a_request_after_dispatch_claim(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_01', '원래 요청')
            transition(store, session, 'request_01', 'queued', 'dispatching')
            with self.assertRaises(ValueError):
                update(store, session, 'request_01', 1, '늦게 도착한 변경')
            row = HermesSessionStore(Path(root)).read_session_record(session)['chat_queue'][0]
            self.assertEqual((row['revision'], row['prompt'], row['state']), (2, '원래 요청', 'dispatching'))

    def test_model_selection_is_preserved_in_queue_and_idempotency(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_01', '코드 수정', 'qwen3.5-4b')
            update(store, session, 'request_01', 1, '코드 수정해줘')
            self.assertEqual(store.read_session_record(session)['chat_queue'][0]['model_profile'], 'qwen3.5-4b')
            self.assertTrue(enqueue(store, session, 'request_01', '코드 수정', 'qwen3.5-4b')['duplicate'])
            with self.assertRaises(ValueError):
                enqueue(store, session, 'request_01', '코드 수정', 'qwen3.8-27b')

    def test_dispatch_passes_selected_model(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            store = HermesSessionStore(root / 'sessions')
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_01', '작업', 'qwen3.8-27b')
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            with patch.object(manager, 'submit_hermes_session_message_locked', return_value={'job_id':'job'}) as submit:
                manager.dispatch_chat_queue(session)
            self.assertEqual(submit.call_args.args[0]['model_profile'], 'qwen3.8-27b')

    def test_fifo_persistence_edit_cancel_and_idempotency(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a'*32
            store.create_session_record(session)
            first = enqueue(store, session, 'request_01', '첫 요청')
            enqueue(store, session, 'request_02', '다음 요청')
            self.assertFalse(first['duplicate'])
            self.assertTrue(enqueue(store, session, 'request_01', '첫 요청')['duplicate'])
            with self.assertRaises(ValueError):
                enqueue(store, session, 'request_01', '다른 요청')
            edited = update(store, session, 'request_01', 1, '수정된 요청')
            self.assertEqual(edited['revision'], 2)
            with self.assertRaises(ValueError):
                update(store, session, 'request_01', 1, '이전 버전')
            update(store, session, 'request_02', 1, cancel=True)
            rows = HermesSessionStore(Path(root)).read_session_record(session)['chat_queue']
            self.assertEqual([(row['prompt'], row['state']) for row in rows], [('수정된 요청','queued'),('다음 요청','cancelled')])
            with self.assertRaises(ValueError):
                update(store, session, 'request_02', 2, '취소된 요청')

    def test_dispatch_waits_for_previous_response_and_recovers_after_restart(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.chat_queue_store import transition
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            store = HermesSessionStore(root/'sessions')
            session = 'b'*32
            store.create_session_record(session)
            store.append_session_request(session, 'previous_1', '앞선 질문')
            previous = '2026-11-21_12-00-00-aaaaaaaa'
            store.attach_session_job(session, 'previous_1', previous)
            enqueue(store, session, 'request_01', '첫 번째')
            enqueue(store, session, 'request_02', '두 번째')
            manager = HermesServiceManager(root/'jobs', root/'sessions')
            jobs = {previous:{'status':{'status':'running'},'final_response':None,'final_response_truncated':False}}
            with patch.object(manager, 'read_context_job', side_effect=lambda job:jobs[job]), patch.object(manager, 'submit_hermes_session_message_locked') as submit:
                with self.assertRaisesRegex(ValueError, '이전 작업'):
                    manager.dispatch_chat_queue(session)
                submit.assert_not_called()
                jobs[previous] = {'status':{'status':'completed'},'final_response':'완료 답변','final_response_truncated':False}
                # A prior server died after claiming the request. A new manager can resume it.
                transition(store, session, 'request_01', 'queued', 'dispatching')
                def submit_job(payload):
                    store.append_session_request(session, payload['request_id'], payload['prompt'])
                    job = '2026-11-21_12-01-00-bbbbbbbb'
                    store.attach_session_job(session, payload['request_id'], job)
                    jobs[job] = {'status':{'status':'running'},'final_response':None,'final_response_truncated':False}
                    return {'job_id':job}
                submit.side_effect = submit_job
                manager.dispatch_chat_queue(session)
                submit.assert_called_once()
                with self.assertRaisesRegex(ValueError, '이전 작업'):
                    manager.dispatch_chat_queue(session)
                self.assertEqual([row['state'] for row in store.read_session_record(session)['chat_queue']], ['dispatched','queued'])

    def test_service_enqueues_edits_cancels_and_deduplicates_while_busy(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = HermesSessionStore(root/'sessions')
            session = 'c'*32
            store.create_session_record(session)
            store.append_session_request(session, 'previous_1', '진행 중인 요청')
            store.attach_session_job(session, 'previous_1', '2026-11-21_12-00-00-aaaaaaaa')
            manager = HermesServiceManager(root/'jobs', root/'sessions')
            running = {'status':{'status':'running'},'final_response':None,'final_response_truncated':False}
            payload = {'session_id':session,'request_id':'queued_001','prompt':'대기 요청'}
            with patch.object(manager, 'read_context_job', return_value=running):
                response = manager.execute_hermes_command('hermes-session-submit', payload)
                self.assertTrue(response['queued'])
                self.assertTrue(manager.execute_hermes_command('hermes-session-submit', payload)['duplicate'])
                edited = manager.execute_hermes_command('hermes-chat-queue-update', {'session_id':session,'request_id':'queued_001','revision':1,'prompt':'변경 요청'})
                self.assertEqual(edited['prompt'],'변경 요청')
                self.assertTrue(manager.execute_hermes_command('hermes-session-submit', payload)['duplicate'])
                cancelled = manager.execute_hermes_command('hermes-chat-queue-update', {'session_id':session,'request_id':'queued_001','revision':2,'cancel':True})
                self.assertEqual(cancelled['state'],'cancelled')
