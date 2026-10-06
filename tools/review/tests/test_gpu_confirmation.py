"""확인 취소는 생성 명령을 보내지 않으며 승인 시 한 번만 전달한다."""
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_gpu_confirmation import GPU_CONFIRMATION_SCRIPT, bind_gpu_generation_confirmation

class GpuConfirmationTests(unittest.TestCase):
    def test_cancel_does_not_invoke_generation(self):
        callback_value=Mock(return_value='accepted')
        with gr.Blocks() as blocks_value:
            input_value=gr.Textbox()
            output_value=gr.Textbox()
            bind_gpu_generation_confirmation(gr.Button('생성'),callback_value,input_value,output_value)
        callback_registry_values=blocks_value.fns.values() if isinstance(blocks_value.fns,dict) else blocks_value.fns
        callback_function=next(value.fn for value in callback_registry_values if value.fn and value.fn.__name__=='execute_confirmed_generation')
        list(callback_function('input',False))
        callback_value.assert_not_called()
        self.assertEqual(list(callback_function('input',True)),['accepted'])
        callback_value.assert_called_once_with('input')

    def test_confirmation_script_requires_explicit_queue_approval(self):
        self.assertIn("fetch('/management/gpu-queue'", GPU_CONFIRMATION_SCRIPT)
        self.assertIn("status === 'busy'", GPU_CONFIRMATION_SCRIPT)
        self.assertIn('대기열에 추가', GPU_CONFIRMATION_SCRIPT)
        self.assertIn('window.confirm(', GPU_CONFIRMATION_SCRIPT)
        self.assertNotIn('cssText', GPU_CONFIRMATION_SCRIPT)
