"""페이지 재접속 시 최신 작업 복원 계약."""
import unittest
from unittest.mock import Mock, patch

from tools.review.ui.gradio.hy_motion_app import load_latest_generation


class HyMotionReloadTests(unittest.TestCase):
    def test_model_readiness_does_not_unlock_pending_confirmation(self):
        import inspect
        from tools.review.ui.gradio.hy_motion_app import build_hymotion_interface
        current_interface_blocks = build_hymotion_interface('http://127.0.0.1:9988')
        current_callbacks = [current_record.fn for current_record in current_interface_blocks.fns.values() if current_record.fn]
        current_model_callback = next(current_callback for current_callback in current_callbacks if current_callback.__name__ == 'refresh_generation_readiness' and len(inspect.signature(current_callback).parameters) == 6)
        current_button_callback = next(current_callback for current_callback in current_callbacks if current_callback.__name__ == 'refresh_generation_readiness' and len(inspect.signature(current_callback).parameters) == 2)
        current_cancel_callback = next(current_callback for current_callback in current_callbacks if current_callback.__name__ == 'cancel_generation_confirmation')
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'ready':True,'message':'준비 완료'}), patch('tools.review.ui.gradio.hy_motion_app.validate_generation_request'):
            self.assertTrue(current_model_callback('walk', 2, 42, ['front'], '', 5)[1])
        self.assertTrue(current_button_callback(None, True)['interactive'])
        current_pending_record = {'inputs': (), 'consumed':False}
        self.assertFalse(current_button_callback(current_pending_record, True)['interactive'])
        self.assertFalse(current_cancel_callback(current_pending_record, False)[2]['interactive'])
        self.assertTrue(current_cancel_callback(None, True)[2]['interactive'])

    def test_latest_history_restores_progress(self):
        for current_job_status in ('running', 'completed', 'failed'):
            with self.subTest(status=current_job_status):
                current_history_reader = Mock(return_value=list(range(8)))
                current_progress_reader = Mock(return_value=(current_job_status, '예상 시간', {'__type__':'update'}))
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

    def test_job_removed_during_restore_clears_identifier(self):
        current_history_reader=Mock(return_value=[])
        current_progress_reader=Mock(return_value=('삭제됨','다른 작업 선택',''))
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command',return_value={'records':[{'id':'removed'}]}):
            self.assertEqual(load_latest_generation(current_history_reader,current_progress_reader),['','삭제됨','다른 작업 선택'])
