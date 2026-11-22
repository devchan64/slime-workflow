"""상주 대화 실행기의 프로세스와 취소 계약을 GPU 없이 검증한다."""
import json
import multiprocessing
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.resident_chat_executor import execute_resident_chat, observe_resident_chat_status


def run_executor(workspace, job):
    with patch('workflow.domains.hermes_agent.resident_chat_executor.ROOT', Path(workspace)):
        execute_resident_chat(job, 'resident_123', 'a'*32)


class ResidentChatExecutorTests(unittest.TestCase):
    def test_real_child_is_gated_and_completion_is_recorded(self):
        with TemporaryDirectory() as root:
            workspace = Path(root)
            child = workspace / 'workflow/domains/hermes_agent/resident_chat_child.py'
            child.parent.mkdir(parents=True)
            child.write_text('import os,sys\nassert os.read(int(sys.argv[5]),1)==b"1"\n')
            job = workspace / 'job'; job.mkdir()
            with patch('workflow.domains.hermes_agent.resident_chat_executor.ROOT', workspace):
                self.assertEqual(execute_resident_chat(job, 'resident_123', 'a'*32), 0)
            self.assertEqual(json.loads((job / 'status.json').read_text())['status'], 'completed')

    def test_preexisting_cancel_never_starts_child(self):
        with TemporaryDirectory() as root:
            job = Path(root)
            (job / 'cancel.request').touch()
            with patch('workflow.domains.hermes_agent.resident_chat_executor.subprocess.Popen') as launch:
                self.assertEqual(execute_resident_chat(job, 'resident_123', 'a'*32), 0)
                launch.assert_not_called()
            self.assertEqual(json.loads((job / 'status.json').read_text())['status'], 'cancelled')

    def test_cancel_stops_real_child_before_marking_cancelled(self):
        with TemporaryDirectory() as root:
            workspace = Path(root)
            child = workspace / 'workflow/domains/hermes_agent/resident_chat_child.py'
            child.parent.mkdir(parents=True)
            child.write_text('import os,sys,time\nassert os.read(int(sys.argv[5]),1)==b"1"\nopen(os.path.join(sys.argv[1],"started"),"w").close()\ntime.sleep(60)\n')
            job = workspace / 'job'; job.mkdir()
            process = multiprocessing.Process(target=run_executor, args=(root, str(job)))
            process.start()
            try:
                deadline = time.monotonic() + 5
                while not (job / 'started').exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue((job / 'started').exists())
                (job / 'cancel.request').touch()
                process.join(5)
                self.assertEqual(process.exitcode, 0)
                self.assertEqual(json.loads((job / 'status.json').read_text())['status'], 'cancelled')
            finally:
                if process.is_alive():
                    process.terminate(); process.join(5)

    def test_service_reuses_same_session_resident_without_new_gpu_job(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with TemporaryDirectory() as root:
            manager = HermesServiceManager(root)
            context = {'session_id':'a'*32}
            with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value='resident_123'), \
                 patch('workflow.domains.hermes_agent.resident_chat_executor.launch_resident_chat') as resident_launch, \
                 patch('workflow.domains.hermes_agent.service.launch_gpu_process') as gpu_launch:
                result = manager.submit_hermes_job_locked({'request_id':'request_123','prompt':'코드 수정'}, context=context, model_profile='qwen3.8-27b')
                job = Path(root) / result['id']
                self.assertEqual(json.loads((job / 'request.json').read_text())['resident_id'], 'resident_123')
                resident_launch.assert_called_once()
                gpu_launch.assert_not_called()
                with self.assertRaisesRegex(ValueError, '상주 모델'):
                    manager.submit_hermes_job_locked({'request_id':'request_456','prompt':'안녕'}, context=context, model_profile='qwen3.5-4b')

    def test_stale_executor_is_reported_unknown_without_resubmitting(self):
        from workflow.common.generation_records import write_record_atomically
        with TemporaryDirectory() as root:
            path = Path(root) / 'resident-executor.json'
            stat_fields = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()
            identity = {'pid':os.getpid(),'pid_start_token':stat_fields[19],
                        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
            write_record_atomically(path, identity)
            self.assertEqual(observe_resident_chat_status(root, {'status':'running'})['status'], 'running')
            identity['pid_start_token'] = '0'
            write_record_atomically(path, identity)
            self.assertEqual(observe_resident_chat_status(root, {'status':'running'})['status'], 'unknown')
            self.assertEqual(observe_resident_chat_status(root, {'status':'completed'})['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
