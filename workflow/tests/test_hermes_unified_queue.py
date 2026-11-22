import hashlib
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
            resident_id = 'start_' + hashlib.sha256((first + ':request_123').encode()).hexdigest()
            resident = root / '.local/hermes-agent/residents' / resident_id
            resident.mkdir(parents=True)
            (resident / 'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':first},'queue_order_ns':100}))
            (resident / 'launch.json').write_text(json.dumps({'id':resident_id,'state':'accepted'}))
            (resident / 'status.json').write_text(json.dumps({'status':'queued'}))
            (resident / 'gpu-command.json').write_text(json.dumps({'service':'hermes-agent','command':['python',str(root / 'workflow/domains/hermes_agent/resident_worker.py'),str(resident)]}))
            image = root / '.tmp/test/image/job_123'
            image.mkdir(parents=True)
            (image / 'status.json').write_text(json.dumps({'status':'queued'}))
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
            self.assertEqual(entries[1]['state'], 'gpu_queued')
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
