"""작가 UI의 기본 컴포넌트 및 조회한 제안 적용 계약."""
import unittest
from unittest.mock import patch
import gradio as gr
from tools.review.ui.gradio.writer_agent_app import build_writer_agent_interface,format_writer_detail


class WriterAgentGradioTest(unittest.TestCase):
    def test_uses_native_components_without_html(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        self.assertFalse(any(isinstance(current_component_value,gr.HTML) for current_component_value in current_interface_blocks.blocks.values()))
        self.assertTrue(any(isinstance(current_component_value,gr.Dropdown) for current_component_value in current_interface_blocks.blocks.values()))

    def test_detail_retains_diff_evidence_and_apply_hash(self):
        current_detail_record={'id':'job-a','job_path':'/records/job-a','status':{'stage':'review','proposal_hash':'hash-a'},'request':{'mode':'write'},'proposal':{'reason':'근거','changes':[{'path':'a.md','diff':'+문장'}],'evidence':[{'text':'자료'}]}}
        current_output_values=format_writer_detail(current_detail_record)
        self.assertEqual(current_output_values[0]['status']['proposal_hash'],'hash-a')
        self.assertEqual(current_output_values[8],'a.md\n+문장')
        self.assertTrue(current_output_values[12]['interactive'])
        self.assertFalse(current_output_values[13])

    def test_unconfirmed_apply_never_calls_service(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
            with self.assertRaises(gr.Error):current_apply_callback({'id':'job-a'},False)
            current_service_mock.assert_not_called()

    def test_apply_uses_loaded_identifier_and_hash(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_detail_record={'id':'job-a','status':{'stage':'applied','proposal_hash':'hash-a'},'job_path':'/records/job-a','request':{},'application':{'status':'applied'}}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[{},current_detail_record]) as current_service_mock:
            current_output_values=current_apply_callback(current_detail_record,True)
            self.assertEqual(current_service_mock.call_args_list[0].args,(8770,'apply',{'id':'job-a','proposal_hash':'hash-a'}))
            self.assertFalse(current_output_values[12]['interactive'])
