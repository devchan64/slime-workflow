"""PID namespace 차이로 살아 있는 대기 작업이 사라지지 않는지 검사한다."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow.common import gpu_job_queue


class GpuTicketNamespaceTests(unittest.TestCase):
    def test_foreign_pid_uses_live_execution_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = root / 'job'
            job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'service': 'image', 'command': []}))
            lock = (job / 'execution.lock').open('w+')
            self.addCleanup(lock.close)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ticket = root / 'ticket.json'
            ticket.write_text(json.dumps({'pid': 2147483647, 'path': str(job), 'pid_namespace': 'pid:[999999999]'}))
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', root), patch.object(gpu_job_queue, 'identify_execution_command', return_value='test'), patch.object(gpu_job_queue, 'estimate_required_memory', return_value={'required_memory_mib': 1}):
                self.assertEqual(gpu_job_queue.select_runnable_ticket(100, 'vram'), ticket)
                ticket.write_text(json.dumps({'pid': 0, 'path': str(job), 'pid_namespace': 'pid:[999999999]'}))
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(100, 'vram'))
                ticket.write_text(json.dumps({'pid': 2147483647, 'path': str(job), 'pid_namespace': 'bad'}))
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(100, 'vram'))
                ticket.write_text(json.dumps({'pid': 2147483647, 'path': str(job)}))
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(100, 'vram'))
                ticket.write_text(json.dumps({'pid': 2147483647, 'path': str(job), 'pid_namespace': 'pid:[999999999]'}))
                fcntl.flock(lock, fcntl.LOCK_UN)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(100, 'vram'))
                self.assertTrue(ticket.exists())

    def test_unknown_namespace_never_proves_same_namespace(self):
        self.assertFalse(gpu_job_queue.gpu_ticket_same_pid_namespace({'pid': os.getpid()}))
        self.assertFalse(gpu_job_queue.gpu_ticket_same_pid_namespace({'pid_namespace': 'invalid'}))
        self.assertTrue(gpu_job_queue.gpu_ticket_same_pid_namespace({'pid_namespace': os.readlink('/proc/self/ns/pid')}))

    def test_observation_preserves_foreign_live_ticket_as_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / '.tmp/gpu-queue'
            job = root / '.tmp/test/wan22-vace/2026-11-22_21-00-00-12345678'
            queue.mkdir(parents=True)
            job.mkdir(parents=True)
            (job / 'status.json').write_text(json.dumps({'status': 'queued'}))
            (job / 'gpu-command.json').write_text(json.dumps({'service': 'image', 'command': []}))
            ticket = queue / 'ticket.json'
            ticket.write_text(json.dumps({'pid': 2147483647, 'path': str(job), 'pid_namespace': 'pid:[999999999]'}))
            with (job / 'execution.lock').open('w+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', queue), patch.object(gpu_job_queue, 'WORKFLOW_ROOT_DIRECTORY', root):
                    result = gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True)
                self.assertEqual(result['jobs'][0]['executor_identity'], 'unverified')
                self.assertEqual(result['jobs'][0]['id'], job.name)
