import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.common import gpu_memory_history as memory

class MemoryHistoryTests(unittest.TestCase):
    def test_recent_twenty_and_summary_refresh_per_service(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(directory)):
            for index in range(22):
                memory.save_memory_observation('momask',f'job-{index}',1000+index,2,'completed')
            memory.save_memory_observation('anny','another',3000,2,'completed')
            records=memory.load_recent_observations('momask')
            self.assertEqual(len(records),20)
            self.assertEqual(records[-1][1]['job_id'],'job-2')
            summary=json.loads((Path(directory)/'summary.json').read_text())
            self.assertEqual(summary['momask']['retained_runs'],20)
            self.assertEqual(summary['anny']['retained_runs'],1)
            self.assertEqual(memory.estimate_required_memory('momask',4096)['required_memory_mib'],4096)

    def test_failed_or_unmeasured_samples_do_not_lower_or_inflate_estimate(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(directory)):
            memory.save_memory_observation('image','good',8000,3,'completed')
            memory.save_memory_observation('image','failed',30000,3,'failed')
            memory.save_memory_observation('image','error',40000,3,'completed','query failed')
            estimate=memory.estimate_required_memory('image',6144)
            self.assertEqual(estimate['samples'],1)
            self.assertEqual(estimate['required_memory_mib'],9856)

    def test_command_histories_are_retained_independently(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(directory)):
            for index in range(22):
                memory.save_memory_observation('image',f'job-{index}',8000,2,'completed',command_identity_name='first.py')
            memory.save_memory_observation('image','other',12000,2,'completed',command_identity_name='second.py')
            self.assertEqual(len(memory.load_recent_observations('image','first.py')),20)
            self.assertEqual(len(memory.load_recent_observations('image','second.py')),1)
            self.assertEqual(memory.estimate_required_memory('image',6144,'first.py')['observed_peak_mib'],8000)
            self.assertEqual(memory.identify_execution_command(['python','/repo/first.py','--job','one']),'first.py')
