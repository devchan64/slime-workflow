"""다운로드와 작업 상태는 필요한 동안에만 빠르게 조회한다."""
import unittest
from unittest.mock import patch
import gradio as gr

from tools.management.common.gradio_model_download import build_model_progress_display


class PollingEfficiencyTests(unittest.TestCase):
    def test_download_polling_adapts_to_activity(self):
        with patch('tools.management.common.management_client.execute_remote_management_command') as current_gateway_mock:
            with gr.Blocks() as current_interface_blocks:
                build_model_progress_display(current_interface_blocks, 'expression-lora')
            current_refresh_callback = next(current_binding.fn for current_binding in current_interface_blocks.fns.values()
                                            if current_binding.fn and current_binding.fn.__name__ == 'refresh_model_progress_status')
            current_gateway_mock.return_value = {'records': []}
            self.assertEqual(current_refresh_callback()[1].value, 30)
            current_gateway_mock.return_value = {'records': [{'model': 'WarmBloodAban/Qwen-Image-2.1-LoRAs/adapter', 'status': 'running'}]}
            self.assertEqual(current_refresh_callback()[1].value, 5)
            current_gateway_mock.side_effect = RuntimeError('offline')
            self.assertEqual(current_refresh_callback()[1].value, 30)

    def test_music_poll_stops_when_no_job_or_completed(self):
        from tools.management.ui.gradio.music_app import build_music_interface
        current_interface_blocks = build_music_interface('music-heartmula', 'http://127.0.0.1:9988')
        current_refresh_callback = next(current_binding.fn for current_binding in current_interface_blocks.fns.values()
                                        if current_binding.fn and current_binding.fn.__name__ == 'refresh_music_result')
        with patch('tools.management.ui.gradio.music_app.execute_remote_management_command') as current_command_mock:
            self.assertFalse(current_refresh_callback('', False, '')[-1].active)
            current_command_mock.assert_not_called()
        with patch('tools.management.ui.gradio.music_app.read_existing_generation_status', return_value={'status': 'completed'}):
            self.assertFalse(current_refresh_callback('job', False, '')[-1].active)
        with patch('tools.management.ui.gradio.music_app.read_existing_generation_status', return_value={'status': 'running'}):
            current_running_timer = current_refresh_callback('job', False, '')[-1]
            self.assertTrue(current_running_timer.active)
            self.assertEqual(current_running_timer.value, 5)
