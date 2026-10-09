"""페이지 재접속 시 최신 작업 복원 계약."""
import unittest
from unittest.mock import Mock, patch

from tools.review.ui.gradio.hy_motion_app import load_latest_generation


class HyMotionReloadTests(unittest.TestCase):
    def test_latest_history_restores_progress(self):
        for current_job_status in ('running', 'completed', 'failed'):
            with self.subTest(status=current_job_status):
                current_history_reader = Mock(return_value=list(range(8)))
                current_progress_reader = Mock(return_value=(current_job_status, '예상 시간'))
                with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'records': [{'id': 'latest'}, {'id': 'older'}]}) as current_command_mock:
                    current_output_values = load_latest_generation(current_history_reader, current_progress_reader)
                current_command_mock.assert_called_once_with('history', {})
                current_history_reader.assert_called_once_with(1, 'latest')
                current_progress_reader.assert_called_once_with('latest')
                self.assertEqual(current_output_values[-3:], ['latest', current_job_status, '예상 시간'])

    def test_empty_history_preserves_idle_state(self):
        current_history_reader = Mock(return_value=list(range(8)))
        current_progress_reader = Mock()
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'records': []}):
            current_output_values = load_latest_generation(current_history_reader, current_progress_reader)
        current_history_reader.assert_called_once_with(1, None)
        current_progress_reader.assert_not_called()
        self.assertEqual(current_output_values[-3], '')
        self.assertIn('이력이 없습니다', current_output_values[-2])
