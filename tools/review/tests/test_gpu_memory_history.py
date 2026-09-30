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
            self.assertEqual(memory.estimate_required_memory('momask',4096)['required_memory_mib'],1021)

    def test_failed_or_unmeasured_samples_do_not_lower_or_inflate_estimate(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(directory)):
            memory.save_memory_observation('image','good',8000,3,'completed')
            memory.save_memory_observation('image','failed',30000,3,'failed')
            memory.save_memory_observation('image','error',40000,3,'completed','query failed')
            estimate=memory.estimate_required_memory('image',6144)
            self.assertEqual(estimate['samples'],1)
            self.assertEqual(estimate['required_memory_mib'],8000)

    def test_command_histories_are_retained_independently(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(directory)):
            for index in range(22):
                memory.save_memory_observation('image',f'job-{index}',8000,2,'completed',command_identity_name='first.py')
            memory.save_memory_observation('image','other',12000,2,'completed',command_identity_name='second.py')
            self.assertEqual(len(memory.load_recent_observations('image','first.py')),20)
            self.assertEqual(len(memory.load_recent_observations('image','second.py')),1)
            self.assertEqual(memory.estimate_required_memory('image',6144,'first.py')['observed_peak_mib'],8000)
            self.assertEqual(memory.identify_execution_command(['python','/repo/first.py','--job','one']),'first.py')

    def test_image_resolution_steps_and_legacy_request_profiles(self):
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            temporary_root_path = Path(temporary_directory_value)
            with patch.object(memory,'MEMORY_HISTORY_DIRECTORY',temporary_root_path/'history'),patch.object(memory,'IMAGE_HISTORY_ROOT_PATHS',(temporary_root_path,)):
                for job_identifier_value,width_pixel_value,inference_step_count,measured_peak_value in (('small',1024,4,4500),('large',1280,4,6202),('slow',1024,30,5500)):
                    generation_job_directory = temporary_root_path/job_identifier_value
                    generation_job_directory.mkdir()
                    (generation_job_directory/'request.json').write_text(json.dumps({'width':width_pixel_value,'height':width_pixel_value,'steps':inference_step_count}))
                    memory.save_memory_observation('image',generation_job_directory,measured_peak_value,3,'completed',command_identity_name='run_qwen_2512.py')
                for job_identifier_value,expected_peak_value in (('small',4500),('large',6202),('slow',5500)):
                    command_identity_value = memory.identify_execution_command(['python','run_qwen_2512.py'],temporary_root_path/job_identifier_value)
                    estimated_memory_record = memory.estimate_required_memory('image',6144,command_identity_value)
                    self.assertEqual(estimated_memory_record['samples'],1)
                    self.assertEqual(estimated_memory_record['required_memory_mib'],expected_peak_value)
                unknown_estimate_record = memory.estimate_required_memory('image',6144,'run_qwen_2512.py:768x768:steps=30:references=0')
                self.assertEqual(unknown_estimate_record['samples'],0)
                self.assertEqual(unknown_estimate_record['method'],'configured-initial-estimate')
                self.assertEqual(unknown_estimate_record['required_memory_mib'],6144)

    def test_image_profiles_keep_twenty_samples_independently(self):
        with tempfile.TemporaryDirectory() as temporary_directory_value,patch.object(memory,'MEMORY_HISTORY_DIRECTORY',Path(temporary_directory_value)):
            for sample_index_value in range(22):
                memory.save_memory_observation('image',f'large-{sample_index_value}',6202,2,'completed',command_identity_name='run_qwen_2512.py:1280x1280:steps=4:references=0')
            memory.save_memory_observation('image','small',4500,2,'completed',command_identity_name='run_qwen_2512.py:1024x1024:steps=4:references=0')
            self.assertEqual(len(memory.load_recent_observations('image','run_qwen_2512.py:1280x1280:steps=4:references=0')),20)
            self.assertEqual(len(memory.load_recent_observations('image','run_qwen_2512.py:1024x1024:steps=4:references=0')),1)
