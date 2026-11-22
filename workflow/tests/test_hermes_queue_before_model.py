from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.service import HermesServiceManager


class QueueBeforeModelTests(unittest.TestCase):
    def test_new_receipt_wakes_dispatcher_without_poll_delay(self):
        from threading import Event
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            called = Event()
            with patch.object(manager, 'dispatch_chat_queue', side_effect=lambda _:called.set()):
                stop = manager.start_chat_queue_dispatcher()
                try:
                    manager.execute_hermes_command('hermes-session-queue-submit', {'session_id':session,'request_id':'request_123','prompt':'hello','model_profile':'qwen3.8-27b'})
                    self.assertTrue(called.wait(2))
                finally:
                    stop.set()
                    manager.chat_queue_wakeup.set()

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
                resident.assert_called_with(session, 'request_123', queue_order_ns=first['request']['queue_order_ns'])
            self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'dispatched')
