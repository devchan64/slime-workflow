"""중단된 영상 작업의 복구와 활성 작업 보호를 검증한다."""
import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.management.common.video_job_recovery import normalize_recovered_video_metrics, recover_interrupted_video_job


class VideoJobRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.current_temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temporary_directory.cleanup)
        self.current_job_directory = Path(self.current_temporary_directory.name)
        (self.current_job_directory / 'status.json').write_text('{"status":"running"}')
        (self.current_job_directory / 'execution.lock').touch()
        (self.current_job_directory / 'gpu-command.json').write_text(json.dumps({'command':['python','/worker.py','--job-dir',str(self.current_job_directory)],'service':'image'}))

    def test_recovery_rejects_symlinked_resume_lock(self):
        current_target_path=self.current_job_directory/'unrelated-file'
        current_target_path.write_text('변경 금지')
        (self.current_job_directory/'resume.lock').symlink_to(current_target_path)
        with patch('tools.management.common.video_job_recovery.has_live_video_worker') as current_worker_mock:
            with self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                recover_interrupted_video_job(self.current_job_directory)
            current_worker_mock.assert_not_called()
        self.assertEqual(current_target_path.read_text(),'변경 금지')
        self.assertEqual(json.loads((self.current_job_directory/'status.json').read_text())['status'],'running')

    def test_interrupted_worker_becomes_failed(self):
        with patch('tools.management.common.video_job_recovery.has_live_video_worker', return_value=False):
            recover_interrupted_video_job(self.current_job_directory)
        current_status_record = json.loads((self.current_job_directory / 'status.json').read_text())
        self.assertEqual(current_status_record['status'], 'failed')
        self.assertIn('예기치 않게 종료', current_status_record['error'])

    def test_live_worker_and_executor_lock_are_preserved(self):
        with patch('tools.management.common.video_job_recovery.has_live_video_worker', return_value=True):
            recover_interrupted_video_job(self.current_job_directory)
        with (self.current_job_directory / 'execution.lock').open('r+') as current_lock_handle:
            fcntl.flock(current_lock_handle, fcntl.LOCK_EX)
            with patch('tools.management.common.video_job_recovery.has_live_video_worker') as current_worker_mock:
                recover_interrupted_video_job(self.current_job_directory)
                current_worker_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_directory / 'status.json').read_text())['status'], 'running')

    def test_queued_and_unknown_state_are_not_changed(self):
        current_status_path = self.current_job_directory / 'status.json'
        for current_status_name in ('queued', 'completed', 'failed'):
            current_status_path.write_text(json.dumps({'status':current_status_name}))
            recover_interrupted_video_job(self.current_job_directory)
            self.assertEqual(json.loads(current_status_path.read_text())['status'], current_status_name)
        current_status_path.write_text('{"status":"running"}')
        (self.current_job_directory / 'execution.lock').unlink()
        recover_interrupted_video_job(self.current_job_directory)
        self.assertEqual(json.loads(current_status_path.read_text())['status'], 'running')

    def test_process_inspection_failure_does_not_change_state(self):
        with patch('tools.management.common.video_job_recovery.has_live_video_worker', side_effect=ValueError('확인 실패')):
            with self.assertRaises(ValueError):
                recover_interrupted_video_job(self.current_job_directory)
        self.assertEqual(json.loads((self.current_job_directory / 'status.json').read_text())['status'], 'running')

    def test_original_history_can_recover_while_observer_only_reads(self):
        from tools.management.common.generation_records import observe_generation_history_records
        from tools.management.common.reference_video_generation import ReferenceVideoGenerationManager
        current_root_path=Path(self.current_temporary_directory.name)
        current_jobs_root=current_root_path/'jobs'
        current_history_root=current_root_path/'history'
        current_history_root.mkdir()
        current_job_path=current_jobs_root/'2026-11-18_12-00-00-aaaaaaaa'
        current_job_path.mkdir(parents=True)
        (current_job_path/'request.json').write_text('{}')
        (current_job_path/'status.json').write_text('{"status":"running"}')
        (current_job_path/'execution.lock').touch()
        (current_job_path/'gpu-command.json').write_text(json.dumps({'command':['worker'],'service':'dwpose'}))
        current_manager_value=ReferenceVideoGenerationManager('/dwpose',current_jobs_root,'worker',lambda value:value,lambda:None)
        with patch.object(current_manager_value,'history_storage_path',return_value=current_history_root),patch('tools.management.common.video_job_recovery.has_live_video_worker',return_value=False):
            current_observed_record=observe_generation_history_records(current_history_root,current_jobs_root,{})
            self.assertEqual(current_observed_record['records'][0]['recorded_status'],'running')
            self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'running')
            current_original_history=current_manager_value.list_generation_history()
            self.assertEqual(current_original_history[0]['status']['status'],'failed')
            self.assertTrue(json.loads((current_job_path/'status.json').read_text())['recovered_interrupted'])

    def test_recovered_metrics_show_failure_without_live_estimate(self):
        current_status_record = {'recovered_interrupted':True, 'metrics':{'status':'running','estimate':{'remaining':12,'completion':'later','estimated_progress':30}}, 'worker_metrics':{'status':'running'}, 'estimate':{'remaining':12}}
        normalize_recovered_video_metrics(current_status_record)
        self.assertEqual(current_status_record['worker_metrics']['status'], 'failed')
        self.assertIsNone(current_status_record['metrics']['estimate']['remaining'])
        self.assertIsNone(current_status_record['estimate']['remaining'])
