"""확인 취소는 생성 명령을 보내지 않으며 승인 시 한 번만 전달한다."""
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation

class GpuConfirmationTests(unittest.TestCase):
    def test_cancel_does_not_invoke_generation(self):
        callback_value=Mock(return_value='accepted')
        with gr.Blocks() as blocks_value:
            input_value=gr.Textbox()
            output_value=gr.Textbox()
            bind_gpu_generation_confirmation(gr.Button('생성'),callback_value,input_value,output_value)
        callback_function=next(value.fn for value in blocks_value.fns.values() if value.fn and value.fn.__name__=='execute_confirmed_generation')
        list(callback_function('input',False))
        callback_value.assert_not_called()
        self.assertEqual(list(callback_function('input',True)),['accepted'])
        callback_value.assert_called_once_with('input')
