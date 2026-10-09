"""실제 작업을 건드리지 않는 공용 대기열 우선 실행 검사."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common import gpu_job_queue
from tools.review.common.management_gateway import resolve_management_command


class QueuePriorityContractTests(unittest.TestCase):
    def test_priority_order_and_running_rejection(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_queue_directory = Path(current_temp_directory) / 'queue'
            current_queue_directory.mkdir()
            for current_job_index in range(3):
                current_job_directory = Path(current_temp_directory) / f'job-{current_job_index}'
                current_job_directory.mkdir()
                (current_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
                (current_queue_directory / f'{current_job_index}.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', current_queue_directory):
                gpu_job_queue.prioritize_waiting_generation('job-2')
                self.assertEqual([current_ticket_path.name for current_ticket_path in gpu_job_queue.read_priority_tickets()], ['2.json','0.json','1.json'])
                gpu_job_queue.prioritize_waiting_generation('job-1')
                self.assertEqual([current_ticket_path.name for current_ticket_path in gpu_job_queue.read_priority_tickets()], ['1.json','2.json','0.json'])
                (Path(current_temp_directory)/'job-0/status.json').write_text(json.dumps({'status':'running'}))
                with self.assertRaises(ValueError):
                    gpu_job_queue.prioritize_waiting_generation('job-0')

    def test_gateway_priority_route(self):
        self.assertEqual(resolve_management_command('hy-motion','prioritize',{'id':'2026-10-09_21-13-20-1a356bbd'}), ('POST','/hy-motion-generator/history/2026-10-09_21-13-20-1a356bbd/prioritize'))
        with self.assertRaises(ValueError):
            resolve_management_command('hy-motion','prioritize',{'id':'../invalid'})
