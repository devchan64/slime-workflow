"""Gradio 확인 단계는 승인 시에만 생성 명령을 전달한다."""
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation

class GpuConfirmationTests(unittest.TestCase):
    def test_confirmation_and_cancel_preserve_generation_boundary(self):
        generation_callback_mock = Mock(return_value='accepted')
        with gr.Blocks() as interface_blocks_value:
            bind_gpu_generation_confirmation(gr.Button('생성'), generation_callback_mock, gr.Textbox(), gr.Textbox())
        callback_function_values = {record.fn.__name__: record.fn for record in interface_blocks_value.fns.values() if record.fn}
        pending_input_values = callback_function_values['prepare_generation_confirmation']('original')[0]
        generation_callback_mock.assert_not_called()
        self.assertIsNone(callback_function_values['cancel_generation_confirmation']()[0])
        generation_callback_mock.assert_not_called()
        self.assertEqual(list(callback_function_values['execute_confirmed_generation'](pending_input_values)), ['accepted'])
        generation_callback_mock.assert_called_once_with('original')

    def test_missing_confirmation_rejected(self):
        with gr.Blocks() as interface_blocks_value:
            bind_gpu_generation_confirmation(gr.Button('생성'), Mock(), gr.Textbox(), gr.Textbox())
        callback_function_value = next(record.fn for record in interface_blocks_value.fns.values() if record.fn and record.fn.__name__ == 'execute_confirmed_generation')
        with self.assertRaises(gr.Error):
            list(callback_function_value(None))
