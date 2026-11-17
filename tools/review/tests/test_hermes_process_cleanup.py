import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from unittest.mock import patch
from tools.review.common.gpu_job_queue import stop_hermes_worker_process_group, recover_stale_hermes_reservation, is_gpu_queue_executor_alive


class HermesProcessCleanupTests(unittest.TestCase):
    def test_zombie_and_reused_pid_are_not_live_executors(self):
        hermes_child_process = subprocess.Popen([sys.executable, '-c', 'pass'])
        try:
            os.waitid(os.P_PID, hermes_child_process.pid, os.WEXITED | os.WNOWAIT)
            self.assertFalse(is_gpu_queue_executor_alive(hermes_child_process.pid))
        finally:
            hermes_child_process.wait()
        self.assertFalse(is_gpu_queue_executor_alive(os.getpid(), 'not-the-current-start-time'))
        self.assertTrue(is_gpu_queue_executor_alive(os.getpid()))

    def test_stale_reservation_without_group_stays_blocked(self):
        self.assertFalse(recover_stale_hermes_reservation({'service':'hermes-agent'}))
        hermes_pid_descriptor = os.open('/dev/null', os.O_RDONLY)
        with patch('tools.review.common.gpu_job_queue.open_verified_hermes_process_group', return_value=hermes_pid_descriptor), patch('tools.review.common.gpu_job_queue.stop_hermes_worker_process_group') as hermes_stop_mock:
            self.assertTrue(recover_stale_hermes_reservation({'service':'hermes-agent', 'worker_pgid':12345}))
            hermes_stop_mock.assert_called_once_with(12345, hermes_pid_descriptor)

    def test_recovered_orphan_is_marked_failed(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_root_path = Path(hermes_temporary_root)
            hermes_job_path = hermes_root_path / '.tmp/test/job'
            hermes_job_path.mkdir(parents=True)
            (hermes_job_path / 'status.json').write_text('{"status":"running"}')
            hermes_pid_descriptor = os.open('/dev/null', os.O_RDONLY)
            with patch('tools.review.common.gpu_job_queue.WORKFLOW_ROOT_DIRECTORY', hermes_root_path), patch('tools.review.common.gpu_job_queue.open_verified_hermes_process_group', return_value=hermes_pid_descriptor), patch('tools.review.common.gpu_job_queue.stop_hermes_worker_process_group'):
                self.assertTrue(recover_stale_hermes_reservation({'service':'hermes-agent', 'worker_pgid':12345, 'path':str(hermes_job_path)}))
            self.assertEqual(json.loads((hermes_job_path / 'status.json').read_text())['status'], 'failed')

    def test_orphaned_child_is_stopped_before_release(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_child_file = Path(hermes_temporary_root) / 'child.pid'
            hermes_parent_code = "import pathlib,subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid))"
            hermes_parent_process = subprocess.Popen([sys.executable, '-c', hermes_parent_code, str(hermes_child_file)], start_new_session=True)
            hermes_pid_descriptor = os.pidfd_open(hermes_parent_process.pid)
            self.assertEqual(hermes_parent_process.wait(timeout=5), 0)
            hermes_child_identifier = int(hermes_child_file.read_text())
            try:
                stop_hermes_worker_process_group(hermes_parent_process.pid, hermes_pid_descriptor)
                hermes_stat_path = Path(f'/proc/{hermes_child_identifier}/stat')
                if hermes_stat_path.exists():
                    self.assertIn(hermes_stat_path.read_text().rpartition(') ')[2].split()[0], ('Z', 'X'))
            finally:
                os.close(hermes_pid_descriptor)
                try:
                    os.kill(hermes_child_identifier, 9)
                except ProcessLookupError:
                    pass

    def test_recovery_requires_matching_process_identity(self):
        hermes_process_token = 'a' * 32
        hermes_process_environment = dict(os.environ, SLIME_HERMES_PROCESS_TOKEN=hermes_process_token)
        hermes_worker_process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], env=hermes_process_environment, start_new_session=True)
        try:
            hermes_stat_fields = Path(f'/proc/{hermes_worker_process.pid}/stat').read_text().rpartition(') ')[2].split()
            hermes_reservation_record = {'service':'hermes-agent', 'worker_pgid':hermes_worker_process.pid, 'worker_start_token':hermes_stat_fields[19], 'worker_process_token':'b' * 32}
            self.assertFalse(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertIsNone(hermes_worker_process.poll())
            hermes_reservation_record['worker_process_token'] = hermes_process_token
            hermes_reservation_record['worker_start_token'] = 'not-the-start-token'
            self.assertFalse(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertIsNone(hermes_worker_process.poll())
            hermes_reservation_record['worker_start_token'] = hermes_stat_fields[19]
            self.assertTrue(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertNotEqual(hermes_worker_process.wait(timeout=5), 0)
        finally:
            if hermes_worker_process.poll() is None:
                hermes_worker_process.kill()
                hermes_worker_process.wait()


if __name__ == '__main__':
    unittest.main()
