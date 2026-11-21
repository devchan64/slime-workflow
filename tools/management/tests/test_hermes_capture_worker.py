import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.management.domains.hermes_agent.capture_worker import execute_capture_worker_job


class HermesCaptureWorkerTests(unittest.TestCase):
    def test_termination_marks_partial_capture_failed_and_removes_token(self):
        import json
        import subprocess
        import sys
        import yaml
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'job'
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':'character-review','settings':{}}))
            current_program_text="""import sys,time
from pathlib import Path
from tools.management.domains.hermes_agent import capture_worker
from tools.management.domains.character_review import capture
import tools.management.build_block_map_review as review_builder
capture.CAPTURE_STORAGE_DIRECTORY=Path(sys.argv[1])/'captures'
capture.shutil.which=lambda current_name:'/bin/false'
def mock_prepare_capture(current_output_path,**current_keywords):
    Path(current_output_path).mkdir(parents=True)
    return Path(current_output_path)
def mock_probe_capture(*current_arguments,**current_keywords):
    print('PREPARING',flush=True)
    time.sleep(30)
review_builder.build_block_map_review=mock_prepare_capture
import urllib.request
urllib.request.urlopen=mock_probe_capture
sys.argv=['capture_worker','--job-dir',sys.argv[1]+'/job']
capture_worker.main_capture_worker_command()
"""
            current_process_value=subprocess.Popen([sys.executable,'-c',current_program_text,str(current_root_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
            try:
                current_observed_lines=[]
                while 'PREPARING' not in current_observed_lines:
                    current_line_value=current_process_value.stdout.readline()
                    if not current_line_value:break
                    current_observed_lines.append(current_line_value.strip())
                self.assertIn('PREPARING',current_observed_lines)
                current_live_directories=list((current_root_path/'captures').iterdir())
                self.assertEqual(len(current_live_directories),1)
                self.assertTrue((current_live_directories[0]/'active-token').is_file())
                current_process_value.terminate()
                current_process_value.communicate(timeout=8)
                self.assertNotEqual(current_process_value.returncode,0)
                current_capture_directories=list((current_root_path/'captures').iterdir())
                self.assertEqual(len(current_capture_directories),1)
                current_capture_path=current_capture_directories[0]
                self.assertEqual(yaml.safe_load((current_capture_path/'result.yaml').read_text())['status'],'failed')
                self.assertFalse((current_capture_path/'active-token').exists())
                self.assertFalse((current_job_path/'capture-result.json').exists())
            finally:
                if current_process_value.poll() is None:
                    current_process_value.kill()
                    current_process_value.wait(timeout=5)

    def test_worker_sigterm_runs_capture_cleanup(self):
        import subprocess
        import sys
        current_program_text="""import sys,time
from tools.management.domains.hermes_agent import capture_worker
def mock_capture_job(current_job_directory):
    try:
        print('READY',flush=True)
        time.sleep(30)
    finally:
        print('CLEANED',flush=True)
capture_worker.execute_capture_worker_job=mock_capture_job
sys.argv=['capture_worker','--job-dir','fixture']
capture_worker.main_capture_worker_command()
"""
        current_process_value=subprocess.Popen([sys.executable,'-c',current_program_text],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            self.assertEqual(current_process_value.stdout.readline().strip(),'READY')
            current_process_value.terminate()
            current_stdout_value,current_stderr_value=current_process_value.communicate(timeout=8)
            self.assertIn('CLEANED',current_stdout_value)
            self.assertNotEqual(current_process_value.returncode,0)
        finally:
            if current_process_value.poll() is None:
                current_process_value.kill()
                current_process_value.wait(timeout=5)

    def test_worker_validates_inputs_dispatches_service_and_records_result(self):
        for current_service_name,current_settings_value,current_mock_path in (
            ('map-review',{'map':'ash-edge'},'tools.management.domains.map_review.capture.capture_map_review'),
            ('character-review',{},'tools.management.domains.character_review.capture.capture_character_review')):
            with self.subTest(service=current_service_name),tempfile.TemporaryDirectory() as current_directory_name:
                current_job_path=Path(current_directory_name)
                (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':current_service_name,'settings':current_settings_value}))
                current_mock_result={'status':'completed','images':{'image':'fixture.png'}}
                with patch(current_mock_path,return_value=current_mock_result) as current_capture_mock:
                    self.assertEqual(execute_capture_worker_job(current_job_path),current_mock_result)
                    current_capture_mock.assert_called_once()
                self.assertEqual(json.loads((current_job_path/'capture-result.json').read_text()),current_mock_result)

    def test_worker_rejects_invalid_request_or_existing_result_before_dispatch(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path=Path(current_directory_name)
            current_request_path=current_job_path/'request.json'
            with patch('tools.management.domains.map_review.capture.capture_map_review') as current_capture_mock:
                current_request_path.write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':{'map':'../invalid'}}))
                with self.assertRaises(ValueError):execute_capture_worker_job(current_job_path)
                current_request_path.write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':{'map':'ash-edge'}}))
                (current_job_path/'capture-result.json').write_text('{}')
                with self.assertRaises(ValueError):execute_capture_worker_job(current_job_path)
                current_capture_mock.assert_not_called()
