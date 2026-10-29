"""Gradio 확인 단계는 승인 시에만 생성 명령을 전달한다."""
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation

class GpuConfirmationTests(unittest.TestCase):
    def test_external_readiness_success_respects_pending_confirmation(self):
        current_generation_mock = Mock()
        with gr.Blocks() as current_interface_blocks:
            current_ready_state = gr.State(False)
            current_refresh_event = gr.Button('조회').click(lambda: True, outputs=current_ready_state)
            current_generate_button = gr.Button('생성', interactive=False)
            bind_gpu_generation_confirmation(current_generate_button, current_generation_mock, gr.Textbox(), gr.Textbox(),
                generation_readiness_callback=lambda current_ready_value: current_ready_value,
                generation_readiness_inputs=[current_ready_state], generation_readiness_events=[current_refresh_event])
        current_dependencies = current_interface_blocks.get_config_file()['dependencies']
        current_success_events = [current_dependency for current_dependency in current_dependencies if current_dependency.get('trigger_after') == current_refresh_event['id']]
        self.assertEqual(len(current_success_events), 1)
        self.assertTrue(current_success_events[0]['trigger_only_on_success'])
        current_readiness_callback = current_interface_blocks.fns[current_success_events[0]['id']].fn
        self.assertTrue(current_readiness_callback(None, True)['interactive'])
        self.assertFalse(current_readiness_callback(None, False)['interactive'])
        self.assertFalse(current_readiness_callback({'inputs': ('saved',), 'consumed': False}, True)['interactive'])
        current_generation_mock.assert_not_called()

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

    def test_failed_submission_releases_confirmation_for_new_inputs(self):
        current_generation_callback = Mock(side_effect=[ValueError('입력 검증 실패'), 'accepted'])
        with gr.Blocks() as current_interface_blocks:
            bind_gpu_generation_confirmation(gr.Button('생성'), current_generation_callback, gr.Textbox(), gr.Textbox())
        current_callback_functions = {current_function_record.fn.__name__: current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn}
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('invalid')[0]
        with self.assertRaisesRegex(ValueError, '입력 검증 실패'):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))
        with self.assertRaises(gr.Error):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))
        current_failure_events = [current_event_record for current_event_record in current_interface_blocks.get_config_file()['dependencies'] if current_event_record.get('trigger_only_on_failure')]
        self.assertEqual(len(current_failure_events), 1)
        current_failure_callback = current_interface_blocks.fns[current_failure_events[0]['id']].fn
        current_cleanup_result = current_failure_callback(current_pending_inputs)
        self.assertIsNone(current_cleanup_result[0])
        self.assertFalse(current_cleanup_result[1]['visible'])
        self.assertTrue(current_cleanup_result[2]['interactive'])
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('corrected')[0]
        self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs)), ['accepted'])
        self.assertEqual(current_generation_callback.call_count, 2)
        current_generation_callback.assert_called_with('corrected')

    def test_required_reference_consumers_gate_missing_inputs(self):
        from tools.review.ui.gradio.animation_separation_app import build_separation_interface
        for current_interface_builder, current_button_label, current_missing_inputs, current_ready_inputs in (
            (build_separation_interface, '대기열에 추가', [(None, 'base', 'outfit'), (object(), '', 'outfit'), (object(), 'base', ' '), (object(), 'word ' * 100, 'outfit'), (object(), 'base', 'word ' * 100)], (object(), 'word ' * 99, 'outfit')),
        ):
            with self.subTest(builder=current_interface_builder.__name__):
                current_interface_blocks = current_interface_builder('http://127.0.0.1:8798')
                current_start_button = next(current_component for current_component in current_interface_blocks.blocks.values() if isinstance(current_component, gr.Button) and current_component.value == current_button_label)
                self.assertFalse(current_start_button.interactive)
                current_readiness_callback = next(current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn and current_function_record.fn.__name__ == 'refresh_generation_readiness')
                for current_input_values in current_missing_inputs:
                    self.assertFalse(current_readiness_callback(None, *current_input_values)['interactive'])
                self.assertTrue(current_readiness_callback(None, *current_ready_inputs)['interactive'])
                self.assertFalse(current_readiness_callback({'inputs': current_ready_inputs, 'consumed': False}, *current_ready_inputs)['interactive'])
