"""모델 실행 없이 공용 작업의 상태·취소·동시 실행 계약을 검증한다."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

MODULE_FILE_PATH = Path(__file__).resolve().parents[1]/'domains/momask/momask_jobs.py'
MODULE_IMPORT_SPEC = importlib.util.spec_from_file_location('momask_jobs', MODULE_FILE_PATH)
JOB_SERVICE_MODULE = importlib.util.module_from_spec(MODULE_IMPORT_SPEC)
MODULE_IMPORT_SPEC.loader.exec_module(JOB_SERVICE_MODULE)


class SharedGenerationJobsTest(unittest.TestCase):
    def setUp(self):
        self.test_directory_handle = tempfile.TemporaryDirectory()
        self.test_root_directory = Path(self.test_directory_handle.name)
        self.path_patch_handle = patch.multiple(JOB_SERVICE_MODULE, GENERATION_JOB_DIRECTORY=self.test_root_directory/'jobs', GENERATION_HISTORY_DIRECTORY=self.test_root_directory/'history', GENERATION_LOCK_FILE=self.test_root_directory/'generation.lock')
        self.path_patch_handle.start()
        self.addCleanup(self.path_patch_handle.stop)
        self.addCleanup(self.test_directory_handle.cleanup)

    def create_test_record(self):
        with patch.object(JOB_SERVICE_MODULE.subprocess, 'Popen'):
            return JOB_SERVICE_MODULE.start_generation_job('standing', ['down_left'])['id']

    def test_shared_history_and_spawn_failure(self):
        with patch.object(JOB_SERVICE_MODULE.subprocess, 'Popen', side_effect=OSError('test')):
            with self.assertRaises(OSError):
                JOB_SERVICE_MODULE.start_generation_job('standing', ['down_left'])
        records=list((self.test_root_directory/'history').glob('*.json'))
        self.assertEqual(json.loads(records[0].read_text())['status'], 'failed')
        self.assertFalse(JOB_SERVICE_MODULE.check_generation_running())

    def test_lock_blocks_second_entrypoint(self):
        with (self.test_root_directory/'generation.lock').open('a') as lock_handle:
            JOB_SERVICE_MODULE.fcntl.flock(lock_handle, JOB_SERVICE_MODULE.fcntl.LOCK_EX)
            self.assertTrue(JOB_SERVICE_MODULE.check_generation_running())
            with self.assertRaises(ValueError):
                JOB_SERVICE_MODULE.start_generation_job('standing', ['down_left'])

    def test_completion_and_reset_retention(self):
        for clear_history_first in (False, True):
            identifier=self.create_test_record()
            history_path=self.test_root_directory/'history'/(identifier+'.json')
            if clear_history_first:
                history_path.unlink()
            worker_process=Mock(returncode=0)
            worker_process.poll.return_value=0
            with patch.object(JOB_SERVICE_MODULE.subprocess,'Popen',return_value=worker_process), patch.object(JOB_SERVICE_MODULE.os,'close'):
                JOB_SERVICE_MODULE.supervise_generation_job(identifier, 123)
            self.assertEqual(json.loads((self.test_root_directory/'jobs'/identifier/'status.json').read_text())['status'],'completed')
            self.assertEqual(history_path.exists(),not clear_history_first)

    def test_cancel_shared_worker(self):
        identifier=self.create_test_record()
        JOB_SERVICE_MODULE.cancel_generation_job(identifier)
        worker_process=Mock(pid=123,returncode=-15)
        worker_process.poll.return_value=None
        with patch.object(JOB_SERVICE_MODULE.subprocess,'Popen',return_value=worker_process), patch.object(JOB_SERVICE_MODULE.os,'killpg') as kill_process_group, patch.object(JOB_SERVICE_MODULE.os,'close'):
            JOB_SERVICE_MODULE.supervise_generation_job(identifier,123)
        kill_process_group.assert_called_once()
        self.assertEqual(json.loads((self.test_root_directory/'jobs'/identifier/'status.json').read_text())['status'],'cancelled')


if __name__=='__main__':
    unittest.main()
