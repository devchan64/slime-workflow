"""메뉴 오류 원인 기록과 필터 전환 회귀 검증."""
import unittest
from unittest.mock import patch
import gradio as gr
from tools.review.common.gradio_error_trace import trace_management_callback
from tools.review.ui.gradio.management_menu_app import build_management_menu_interface


class ManagementErrorTraceTests(unittest.TestCase):
    def test_error_exposes_trace_without_sensitive_details(self):
        @trace_management_callback('도구 선택')
        def fail_menu_callback():
            raise ValueError('private-input-content')
        with patch('tools.review.common.gradio_error_trace.MANAGEMENT_ERROR_LOGGER.exception') as current_log_mock:
            with self.assertRaises(gr.Error) as current_error_context:
                fail_menu_callback()
        self.assertIn('추적 ID:', str(current_error_context.exception))
        self.assertIn('ValueError', str(current_error_context.exception))
        self.assertNotIn('private-input-content', str(current_error_context.exception))
        current_log_mock.assert_called_once()
        self.assertIn(current_log_mock.call_args.args[-1], str(current_error_context.exception))

    def test_filter_accepts_previous_selection_and_reconciles(self):
        current_page_records = [dict(id='f2v',label='F2V',description='',category='animation-tool',path='/f2v'),dict(id='map',label='맵',description='',category='map-review',path='/map')]
        current_interface_blocks, _ = build_management_menu_interface(current_page_records, 8770)
        current_filter_callbacks = [current_callback for current_callback in current_interface_blocks.fns.values() if current_callback.fn and current_callback.fn.__name__ == 'update_menu_choices']
        self.assertTrue(current_filter_callbacks)
        for current_filter_callback in current_filter_callbacks:
            self.assertFalse(current_filter_callback.preprocess)
            current_filter_result = current_filter_callback.fn('', 'map-review', 'f2v')
            self.assertEqual(current_filter_result[0]['value'], 'map')
