"""HY-Motion의 ETA 분리 표시와 공용 VRAM·경고 표시 계약."""
import unittest
from unittest.mock import patch
from tools.review.ui.gradio.hy_motion_app import refresh_current_progress


class HyMotionProgressDisplayTests(unittest.TestCase):
    def test_observed_memory_and_quality_warning_survive_completion(self):
        current_status_record = {'status': 'completed', 'message': '완료', 'eta': {},
            'metrics': {'gpu_observations': {'0': {'process_current_mib': 0,
                'process_peak_mib': 7123, 'scope': '작업과 자식 프로세스'}}},
            'result': {'quality_warnings': ['포즈 검수 필요']}}
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value=current_status_record) as current_command_mock:
            current_status_text, current_eta_text, current_identifier_update = refresh_current_progress('test-generation')
        current_command_mock.assert_called_once_with('status', {'id': 'test-generation'})
        self.assertIn('관측 피크 7123 MiB', current_status_text)
        self.assertIn('작업과 자식 프로세스', current_status_text)
        self.assertIn('포즈 검수 필요', current_status_text)
        self.assertNotIn('예상 시간 갱신 종료', current_status_text)
        self.assertIn('예상 시간 갱신 종료', current_eta_text)

    def test_missing_memory_is_not_reported_as_zero(self):
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'status':'running','eta':{'remaining':12,'basis':'실측'}}):
            current_status_text,current_eta_text,current_identifier_update=refresh_current_progress('test-generation')
        self.assertIn('측정 자료 없음',current_status_text)
        self.assertNotIn('0 MiB',current_status_text)
        self.assertIn('약 12초',current_eta_text)

    def test_service_exposes_queue_observations_only_after_start(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.domains.hy_motion.jobs import read_generation_status
        with TemporaryDirectory() as current_temporary_directory:
            current_job_directory=Path(current_temporary_directory)
            (current_job_directory/'request.json').write_text('{}')
            current_metrics_record={'gpu_observations':{'0':{'process_peak_mib':7123}}}
            with patch('tools.review.domains.hy_motion.jobs.resolve_generation_directory',return_value=current_job_directory), patch('tools.review.domains.hy_motion.jobs.estimate_generation_completion',return_value={}), patch('tools.review.domains.hy_motion.jobs.read_queue_generation_metrics',return_value=current_metrics_record) as current_metrics_reader:
                for current_status_name in ('running','completed','failed','cancelled'):
                    (current_job_directory/'status.json').write_text(json.dumps({'status':current_status_name}))
                    self.assertEqual(read_generation_status('test-generation')['metrics'],current_metrics_record)
                current_metrics_reader.reset_mock()
                (current_job_directory/'status.json').write_text('{"status":"queued"}')
                self.assertNotIn('metrics',read_generation_status('test-generation'))
                current_metrics_reader.assert_not_called()

    def test_deleted_job_stops_polling_without_hiding_existing_failure(self):
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command',side_effect=[ValueError('missing'),{'records':[]}]):
            current_status_text,current_eta_text,current_identifier_update=refresh_current_progress('removed')
        self.assertIn('삭제',current_status_text)
        self.assertEqual(current_identifier_update,'')
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command') as current_command_mock:
            self.assertEqual(len(refresh_current_progress('')),3)
            current_command_mock.assert_not_called()
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command',side_effect=[ValueError('corrupt'),{'records':[{'id':'existing'}]}]):
            with self.assertRaisesRegex(ValueError,'corrupt'):
                refresh_current_progress('existing')
