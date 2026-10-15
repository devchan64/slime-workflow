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
            with self.assertRaises(gr.Error):current_apply_callback({'id':'job-a'},False,'job-a')
            current_service_mock.assert_not_called()

    def test_apply_uses_loaded_identifier_and_hash(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_detail_record={'id':'job-a','status':{'stage':'applied','proposal_hash':'hash-a'},'job_path':'/records/job-a','request':{},'application':{'status':'applied'}}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[{},current_detail_record]) as current_service_mock:
            current_output_values=current_apply_callback({**current_detail_record,'status':{'stage':'review','proposal_hash':'hash-a'},'application':None},True,'job-a')
            self.assertEqual(current_service_mock.call_args_list[0].args,(8770,'apply',{'id':'job-a','proposal_hash':'hash-a'}))
            self.assertFalse(current_output_values[12]['interactive'])

    def test_changed_selection_and_applied_proposal_never_call_service(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        for current_detail_record,current_selection_value in [({'id':'job-a','status':{'stage':'review'}},'job-b'),({'id':'job-a','status':{'stage':'applied'}},'job-a'),({'id':'job-a','status':{'stage':'review'},'application':{'status':'applied'}},'job-a')]:
            with self.subTest(record=current_detail_record),patch('tools.review.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
                with self.assertRaises(gr.Error):current_apply_callback(current_detail_record,True,current_selection_value)
                current_service_mock.assert_not_called()

    def test_gui_dispatches_gateway_commands(self):
        from tools.review.ui.gradio.writer_agent_app import request_writer_service
        with patch('tools.review.ui.gradio.writer_agent_app.execute_remote_management_command',return_value={}) as current_command_mock:
            request_writer_service(8770,'job?id=job-a')
            current_command_mock.assert_called_with('writer-agent','writer-detail',{'id':'job-a'})
            request_writer_service(8770,'jobs',{'mode':'learn','prompt':''})
            current_command_mock.assert_called_with('writer-agent','writer-submit',{'mode':'learn','prompt':''})

    def test_cli_uses_same_payload_and_http_client_preserves_token(self):
        import contextlib
        import io
        import json
        import tempfile
        from pathlib import Path
        from tools.review.common.management_gateway import execute_gateway_cli,execute_management_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_payload_path=Path(current_directory_name)/'request.json'
            current_payload_path.write_text('{"mode":"learn","prompt":""}')
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(execute_gateway_cli(['command','writer-agent','writer-submit','--payload-file',str(current_payload_path)]),0)
                self.assertEqual(current_command_mock.call_args.args[:3],('writer-agent','writer-submit',{'mode':'learn','prompt':''}))
        current_http_requests=[]
        def respond_mock_request(current_request_value,**current_request_options):
            current_http_requests.append(current_request_value)
            current_envelope_record=json.loads(current_request_value.data)
            return io.BytesIO(json.dumps({'csrf_token':'mock-token'} if current_envelope_record['command']=='writer-state' else {'id':'mock'}).encode())
        with patch('urllib.request.urlopen',side_effect=respond_mock_request):
            execute_management_command('writer-agent','writer-submit',{'mode':'learn','prompt':''},'http://127.0.0.1:8770')
        self.assertEqual(len(current_http_requests),2)
        self.assertEqual(current_http_requests[-1].get_header('X-writer-token'),'mock-token')

    def test_new_selection_clears_previous_proposal_and_confirmation(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_clear_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='clear_writer_selection_detail')
        current_output_values=current_clear_callback()
        self.assertEqual(len(current_output_values),16)
        for current_output_index in (1,2,5,8,9,11):self.assertEqual(current_output_values[current_output_index],'')
        self.assertEqual(current_output_values[0],{})
        self.assertFalse(current_output_values[12]['interactive'])
        self.assertFalse(current_output_values[13])
