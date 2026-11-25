import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common import gpu_job_queue as queue


class PixalGpuQueueTest(unittest.TestCase):
    def test_minimax_image_shares_with_hermes_only_if_reservation_fits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); job=root/'job'; job.mkdir()
            (job/'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'],'service':'minimax-h3-image'}))
            ticket=root/'ticket.json'; ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(job)}))
            with patch.object(queue,'read_priority_tickets',return_value=[ticket]), patch.object(queue,'estimate_required_memory',return_value={'required_memory_mib':81920}):
                self.assertEqual(queue.select_runnable_ticket(81920,'vram',['hermes-agent']),ticket)
                self.assertIsNone(queue.select_runnable_ticket(81919,'vram',['hermes-agent']))
                self.assertIsNone(queue.select_runnable_ticket(999999,'vram',['image']))
                self.assertIsNone(queue.select_runnable_ticket(999999,'vram',['minimax-h3-image']))
    def test_pixal_can_share_only_with_hermes_when_memory_fits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = root / 'job'
            job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'command': ['python', 'worker.py'], 'service': 'pixal-experiment'}))
            ticket = root / 'ticket.json'
            ticket.write_text(json.dumps({'pid': os.getpid(), 'path': str(job)}))
            with patch.object(queue, 'read_priority_tickets', return_value=[ticket]), patch.object(queue, 'estimate_required_memory', return_value={'required_memory_mib': 65536}):
                self.assertEqual(queue.select_runnable_ticket(65536, 'vram', ['hermes-agent']), ticket)
                self.assertIsNone(queue.select_runnable_ticket(65535, 'vram', ['hermes-agent']))
                self.assertIsNone(queue.select_runnable_ticket(100000, 'vram', ['image']))
                self.assertIsNone(queue.select_runnable_ticket(100000, 'vram', ['pixal-experiment']))
                self.assertIsNone(queue.select_runnable_ticket(100000, 'vram', ['unreadable']))

    def test_running_pixal_does_not_block_hermes_but_blocks_other_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = root / 'job'
            job.mkdir()
            command = job / 'gpu-command.json'
            ticket = root / 'ticket.json'
            ticket.write_text(json.dumps({'pid': os.getpid(), 'path': str(job)}))
            with patch.object(queue, 'read_priority_tickets', return_value=[ticket]), patch.object(queue, 'estimate_required_memory', return_value={'required_memory_mib': 16}):
                command.write_text(json.dumps({'command': ['python', 'worker.py'], 'service': 'hermes-agent'}))
                self.assertEqual(queue.select_runnable_ticket(16, 'vram', ['pixal-experiment']), ticket)
                self.assertIsNone(queue.select_runnable_ticket(15, 'vram', ['pixal-experiment']))
                command.write_text(json.dumps({'command': ['python', 'worker.py'], 'service': 'image'}))
                self.assertIsNone(queue.select_runnable_ticket(100, 'vram', ['pixal-experiment']))


if __name__ == '__main__':
    unittest.main()
