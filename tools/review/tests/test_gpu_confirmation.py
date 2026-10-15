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
        self.assertIsNone(callback_function_values['cancel_generation_confirmation'](pending_input_values)[0])
        generation_callback_mock.assert_not_called()
        with self.assertRaises(gr.Error):
            list(callback_function_values['execute_confirmed_generation'](pending_input_values))
        pending_input_values = callback_function_values['prepare_generation_confirmation']('original')[0]
        self.assertEqual(list(callback_function_values['execute_confirmed_generation'](pending_input_values)), ['accepted'])
        with self.assertRaises(gr.Error):
            list(callback_function_values['execute_confirmed_generation'](pending_input_values))
        generation_callback_mock.assert_called_once_with('original')

    def test_missing_confirmation_rejected(self):
        with gr.Blocks() as interface_blocks_value:
            bind_gpu_generation_confirmation(gr.Button('생성'), Mock(), gr.Textbox(), gr.Textbox())
        callback_function_value = next(record.fn for record in interface_blocks_value.fns.values() if record.fn and record.fn.__name__ == 'execute_confirmed_generation')
        with self.assertRaises(gr.Error):
            list(callback_function_value(None))

    def test_reference_readiness_preserves_pending_lock_and_current_inputs(self):
        current_generation_callback = Mock(return_value='accepted')
        with gr.Blocks() as current_interface_blocks:
            current_reference_controls = [gr.Textbox(), gr.Textbox()]
            bind_gpu_generation_confirmation(gr.Button('생성', interactive=False), current_generation_callback,
                current_reference_controls, gr.Textbox(),
                generation_readiness_callback=lambda *current_reference_values: all(current_reference_values),
                generation_readiness_inputs=current_reference_controls)
        current_callback_functions = {current_function_record.fn.__name__: current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn}
        current_readiness_callback = current_callback_functions['refresh_generation_readiness']
        self.assertFalse(current_readiness_callback(None, '', '')['interactive'])
        self.assertFalse(current_readiness_callback(None, 'identity', '')['interactive'])
        self.assertTrue(current_readiness_callback(None, 'identity', 'pose')['interactive'])
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('identity', 'pose')[0]
        self.assertFalse(current_readiness_callback(current_pending_inputs, 'changed', 'pose')['interactive'])
        self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs)), ['accepted'])
        current_generation_callback.assert_called_once_with('identity', 'pose')
        self.assertFalse(current_readiness_callback(current_pending_inputs, 'changed', 'pose')['interactive'])
        current_cancel_result = current_callback_functions['cancel_generation_confirmation'](current_pending_inputs, 'identity', '')
        self.assertFalse(current_cancel_result[2]['interactive'])
        self.assertTrue(current_callback_functions['cancel_generation_confirmation'](None, 'identity', 'pose')[2]['interactive'])
