import hashlib
import fcntl
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common import gpu_job_queue
from workflow.domains.hermes_agent.chat_queue_store import enqueue
from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.unified_queue import observe_unified_queue


class UnifiedQueueTests(unittest.TestCase):
    def test_existing_chat_gpu_tickets_are_classified_and_deduplicated(self):
        from workflow.domains.hermes_agent.chat_queue_store import transition
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / '.tmp/gpu-queue'
            (queue_root_directory / 'active').mkdir(parents=True)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            own_session_identifier, other_session_identifier = 'a' * 32, 'b' * 32
            for chat_session_identifier in (own_session_identifier, other_session_identifier):
                session_store_instance.create_session_record(chat_session_identifier)
            enqueue(session_store_instance, own_session_identifier, 'request_123', 'private own')
            transition(session_store_instance, own_session_identifier, 'request_123', 'queued', 'dispatching')
            chat_job_records = [(own_session_identifier, 'request_123', '2026-11-23_08-00-00-aaaaaaaa'),
                                (other_session_identifier, 'request_456', '2026-11-23_08-00-01-bbbbbbbb')]
            for job_order_index, (chat_session_identifier, chat_request_identifier, chat_job_identifier) in enumerate(chat_job_records, 1):
                session_store_instance.append_session_request(chat_session_identifier, chat_request_identifier, 'private text')
                session_store_instance.attach_session_job(chat_session_identifier, chat_request_identifier, chat_job_identifier)
                chat_job_directory = temporary_root_path / '.tmp/test/hermes-agent/jobs' / chat_job_identifier
                chat_job_directory.mkdir(parents=True)
                (chat_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
                (chat_job_directory / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['worker']}))
                (queue_root_directory / f'{job_order_index:020d}-{os.getpid()}.json').write_text(json.dumps({'pid':os.getpid(), 'path':str(chat_job_directory)}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory):
                unified_queue_result = observe_unified_queue(session_store_instance, own_session_identifier)
            self.assertEqual([(queue_entry_record['kind'],queue_entry_record['id']) for queue_entry_record in unified_queue_result['entries']], [('chat','request_456'),('chat','request_123')])
            self.assertEqual(unified_queue_result['entries'][0]['own_session'], False)
            self.assertEqual(unified_queue_result['entries'][1]['ticket_id'], chat_job_records[0][2])
            self.assertNotIn('private', json.dumps(unified_queue_result))

    def test_session_scan_does_not_hold_gpu_execution_lock(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / 'queue'
            (queue_root_directory / 'active').mkdir(parents=True)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            original_read_session = session_store_instance.read_session_record_locked
            def read_session_without_gpu_lock(session_identifier):
                with (queue_root_directory / 'execution.lock').open('a') as queue_lock_stream:
                    fcntl.flock(queue_lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(queue_lock_stream, fcntl.LOCK_UN)
                return original_read_session(session_identifier)
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(session_store_instance, 'read_session_record_locked', side_effect=read_session_without_gpu_lock):
                self.assertEqual(observe_unified_queue(session_store_instance, chat_session_identifier)['entries'], [])

    def test_session_change_during_gpu_snapshot_requires_retry(self):
        with TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            queue_root_directory = temporary_root_path / 'queue'
            (queue_root_directory / 'active').mkdir(parents=True)
            session_store_instance = HermesSessionStore(temporary_root_path / 'sessions')
            chat_session_identifier = 'a' * 32
            session_store_instance.create_session_record(chat_session_identifier)
            def mutate_session_during_observation(**observation_options):
                enqueue(session_store_instance, chat_session_identifier, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)
                return {'jobs':[]}
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue_root_directory), \
                 patch.object(gpu_job_queue, 'list_waiting_gpu_jobs', side_effect=mutate_session_during_observation):
                with self.assertRaisesRegex(ValueError, '조회 중 변경'):
                    observe_unified_queue(session_store_instance, chat_session_identifier)

    def test_management_command_returns_session_bound_snapshot(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', root / 'missing'):
                result = manager.execute_hermes_command('hermes-unified-queue-observe', {'session_id':session})
                self.assertEqual(result['session_id'], session)
                self.assertEqual(result['entries'], [])
                with self.assertRaises(ValueError):
                    manager.execute_hermes_command('hermes-unified-queue-observe', {'session_id':session,'extra':True})
            self.assertTrue(any(row['command']=='hermes-unified-queue-observe' for row in list_hermes_capability_catalog()['records']))

    def test_merges_physical_and_chat_receipts_without_duplicate_or_prompt_leak(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / '.tmp/gpu-queue'
            (queue / 'active').mkdir(parents=True)
            store = HermesSessionStore(root / 'sessions')
            first, other = 'a' * 32, 'b' * 32
            store.create_session_record(first)
            store.create_session_record(other)
            with patch('time.time_ns', side_effect=[100, 200]):
                enqueue(store, first, 'request_123', 'private one', 'qwen3.8-27b', require_resident=True)
                enqueue(store, other, 'request_456', 'private two', 'qwen3.8-27b', require_resident=True)
            from workflow.common.gpu_chat_admission import register_chat_queue_intent
            register_chat_queue_intent(queue, first, 'request_123', 100)
            register_chat_queue_intent(queue, other, 'request_456', 200)
            resident_id = 'start_' + hashlib.sha256((first + ':request_123').encode()).hexdigest()
            resident = root / '.local/hermes-agent/residents' / resident_id
            resident.mkdir(parents=True)
            (resident / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':first},'queue_order_ns':100}))
            (resident / 'launch.json').write_text(json.dumps({'id':resident_id,'state':'accepted'}))
            (resident / 'status.json').write_text(json.dumps({'status':'queued','message':'Qwen 적재에 필요한 시스템 메모리와 보호 여유가 부족해 대기 중입니다.'}))
            (resident / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['python',str(root / 'workflow/domains/hermes_agent/resident_worker.py'),str(resident)]}))
            image = root / '.tmp/test/wan22-vace/job_123'
            image.mkdir(parents=True)
            (image / 'status.json').write_text(json.dumps({'status':'queued','message':'private status should not be exposed'}))
            (image / 'gpu-command.json').write_text(json.dumps({'service':'image','command':['worker']}))
            chat_ticket = queue / f'{100:020d}-{os.getpid()}.json'
            image_ticket = queue / f'{150:020d}-{os.getpid()}.json'
            for ticket, job in ((chat_ticket,resident), (image_ticket,image)):
                ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(job)}))
            (queue / 'priority-order').write_text(json.dumps({image_ticket.name:-1}))
            with patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue):
                result = observe_unified_queue(store, first)
            entries = result['entries']
            self.assertEqual([(row['kind'],row['id']) for row in entries], [('task','job_123'),('chat','request_123'),('chat','request_456')])
            self.assertEqual(entries[0]['service'], 'wan22-vace')
            self.assertEqual(entries[1]['state'], 'gpu_queued')
            self.assertTrue(entries[1]['indexed'])
            self.assertIn('시스템 메모리', entries[1]['wait_reason'])
            self.assertNotIn('wait_reason', entries[0])
            self.assertTrue(entries[2]['indexed'])
            self.assertEqual(entries[1]['ticket_id'], resident_id)
            self.assertFalse(entries[2]['own_session'])
            self.assertNotIn('private', json.dumps(result))

    def test_invalid_chat_order_fails_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = HermesSessionStore(root / 'sessions')
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_123', 'hello', 'qwen3.8-27b', require_resident=True)
            path = root / 'sessions' / (session + '.json')
            record = json.loads(path.read_text())
            record['chat_queue'][0]['queue_order_ns'] = False
            path.write_text(json.dumps(record))
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', root / 'missing'):
                with self.assertRaisesRegex(ValueError, '순서'):
                    observe_unified_queue(store, session)
