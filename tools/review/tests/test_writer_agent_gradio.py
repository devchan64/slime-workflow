"""작가 UI의 기본 컴포넌트 및 조회한 제안 적용 계약."""
import unittest
from unittest.mock import patch
import gradio as gr
from tools.review.ui.gradio.writer_agent_app import build_writer_agent_interface,format_writer_detail


class WriterAgentGradioTest(unittest.TestCase):
    def test_failed_detail_clears_previous_proposal_and_confirmation(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_read_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='read_writer_selection')
        for current_error_value in (ValueError('조회 거절'), RuntimeError('서비스 오류'), OSError('연결 종료')):
            with self.subTest(error=str(current_error_value)),patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_error_value):
                current_output_values=current_read_callback('job-a')
                self.assertEqual(current_output_values[0],{})
                self.assertEqual(current_output_values[1],'job-a')
                for current_output_index in (2,5,8,9,11):self.assertEqual(current_output_values[current_output_index],'')
                self.assertFalse(current_output_values[12]['interactive'])
                self.assertFalse(current_output_values[13])
                self.assertIn(str(current_error_value),current_output_values[3])
                self.assertIn('다시 조회',current_output_values[14])

    def test_readiness_requires_prompt_and_existing_selection(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_refresh_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='refresh_writer_workspace')
        current_workspace_record={'configured':True,'ready':True,'trained':True,'jobs':[{'id':'job-a','mode':'write','stage':'completed'}]}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',return_value=current_workspace_record):
            current_empty_values=current_refresh_callback(None,'  ')
            self.assertFalse(current_empty_values[6]['interactive'])
            self.assertTrue(current_empty_values[7]['interactive'])
            self.assertIn('작성 지시를 입력',current_empty_values[8])
            self.assertFalse(current_empty_values[9]['interactive'])
            current_ready_values=current_refresh_callback('job-a','작성 지시')
            self.assertTrue(current_ready_values[6]['interactive'])
            self.assertTrue(current_ready_values[9]['interactive'])
            self.assertFalse(current_refresh_callback('missing','작성 지시')[9]['interactive'])
            current_workspace_record['active_job']='job-running'
            current_busy_values=current_refresh_callback('job-a','작성 지시')
            self.assertFalse(current_busy_values[6]['interactive'])
            self.assertFalse(current_busy_values[7]['interactive'])
            self.assertIn('완료 후',current_busy_values[8])

    def test_uses_native_components_without_html(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        self.assertFalse(any(isinstance(current_component_value,gr.HTML) for current_component_value in current_interface_blocks.blocks.values()))
        self.assertTrue(any(isinstance(current_component_value,gr.Dropdown) for current_component_value in current_interface_blocks.blocks.values()))

    def test_detail_retains_diff_evidence_and_apply_hash(self):
        current_detail_record={'id':'job-a','job_path':'/records/job-a','status':{'stage':'review','proposal_hash':'hash-a'},'request':{'mode':'write'},'proposal':{'reason':'근거','changes':[{'path':'a.md','diff':'+문장'}],'evidence':[{'text':'자료'}]}}
        current_output_values=format_writer_detail(current_detail_record)
        self.assertEqual(current_output_values[0]['status']['proposal_hash'],'hash-a')
        self.assertEqual(current_output_values[8],'a.md\n+문장')
        self.assertFalse(current_output_values[12]['interactive'])
        self.assertFalse(current_output_values[13])

    def test_unconfirmed_apply_never_calls_service(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
            with self.assertRaises(gr.Error):current_apply_callback({'id':'job-a'},False,'job-a')
            current_service_mock.assert_not_called()

    def test_apply_error_clears_confirmation_without_retry(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_detail_record={'id':'job-a','status':{'stage':'review','proposal_hash':'hash-a'},'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}}
        for current_error_value in (ValueError('원문 변경'),OSError('응답 연결 끊김')):
            with self.subTest(error=str(current_error_value)),patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_error_value) as current_service_mock:
                current_output_values=current_apply_callback(current_detail_record,True,'job-a')
                self.assertEqual(current_output_values[0],{})
                self.assertEqual(current_output_values[1],'job-a')
                self.assertIn(str(current_error_value),current_output_values[3])
                self.assertFalse(current_output_values[12]['interactive'])
                self.assertFalse(current_output_values[13])
                self.assertIn('적용 여부',current_output_values[14])
                current_service_mock.assert_called_once()

    def test_apply_readiness_requires_confirmation_and_current_review(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_readiness_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='update_writer_apply_readiness')
        current_detail_record={'id':'job-a','status':{'stage':'review','proposal_hash':'hash-a'},'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}}
        self.assertFalse(current_readiness_callback(current_detail_record,False,'job-a')[0]['interactive'])
        self.assertTrue(current_readiness_callback(current_detail_record,True,'job-a')[0]['interactive'])
        self.assertFalse(current_readiness_callback(current_detail_record,True,'job-b')[0]['interactive'])
        for current_invalid_detail in ({}, {**current_detail_record,'application':{'status':'applied'}}, {**current_detail_record,'status':{'stage':'completed'}}, {**current_detail_record,'proposal':{'changes':[]}}):
            with self.subTest(record=current_invalid_detail):
                self.assertFalse(current_readiness_callback(current_invalid_detail,True,'job-a')[0]['interactive'])

    def test_apply_uses_loaded_identifier_and_hash(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_detail_record={'id':'job-a','status':{'stage':'applied','proposal_hash':'hash-a'},'job_path':'/records/job-a','request':{},'application':{'status':'applied'}}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[{},current_detail_record]) as current_service_mock:
            current_output_values=current_apply_callback({**current_detail_record,'status':{'stage':'review','proposal_hash':'hash-a'},'application':None,'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}},True,'job-a')
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
        current_clear_function=next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn is current_clear_callback)
        self.assertEqual([current_target_value[1] for current_target_value in current_clear_function.targets],['change'])
        current_output_values=current_clear_callback()
        self.assertEqual(len(current_output_values),16)
        for current_output_index in (1,2,5,8,9,11):self.assertEqual(current_output_values[current_output_index],'')
        self.assertEqual(current_output_values[0],{})
        self.assertFalse(current_output_values[12]['interactive'])
        self.assertFalse(current_output_values[13])

    def test_missing_changes_or_hash_never_dispatches_apply(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_readiness_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='update_writer_apply_readiness')
        for current_detail_record in (
            {'id':'job-a','status':{'stage':'review','proposal_hash':'hash-a'},'proposal':{'changes':[]}},
            {'id':'job-a','status':{'stage':'review'},'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}},
        ):
            with self.subTest(record=current_detail_record),patch('tools.review.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
                self.assertFalse(current_readiness_callback(current_detail_record,True,'job-a')[0]['interactive'])
                if not current_detail_record['status'].get('proposal_hash'):
                    self.assertIn('제안 해시가 없어',current_readiness_callback(current_detail_record,True,'job-a')[1])
                with self.assertRaisesRegex(gr.Error,'변경이나 제안 해시'):
                    current_apply_callback(current_detail_record,True,'job-a')
                current_service_mock.assert_not_called()

    def test_progress_refresh_excludes_history_selection_outputs(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_progress_functions=[current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='refresh_writer_progress']
        self.assertEqual(len(current_progress_functions),3)
        for current_function_value in current_progress_functions:
            self.assertFalse(any(isinstance(current_component_value,(gr.Dropdown,gr.Dataframe)) for current_component_value in current_function_value.outputs))
        current_workspace_record={'configured':True,'ready':True,'trained':True,'jobs':[{'id':'job-a','mode':'write','stage':'review'}]}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',return_value=current_workspace_record):
            current_progress_values=current_progress_functions[0].fn(None,'')
        self.assertEqual(len(current_progress_values),len(current_progress_functions[0].outputs))
        current_detail_record={'status':{'stage':'review','summary':'검토 대기'},'log':'실행 기록'}
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,current_detail_record]):
            current_progress_values=current_progress_functions[0].fn('job-a','')
        self.assertEqual(current_progress_values[-2:],['변경 검토 대기 · 검토 대기','실행 기록'])
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,current_detail_record]):
            current_progress_values=current_progress_functions[0].fn('job-a','',False)
        self.assertEqual(current_progress_values[-2],'변경 검토 대기 · 검토 대기')
        self.assertEqual(current_progress_values[-1],gr.skip())
        for current_function_value in current_progress_functions:
            self.assertIsInstance(current_function_value.inputs[-1],gr.Checkbox)

    def test_progress_lookup_failure_preserves_log_and_recovers(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_callback_record=next(current_function_value for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='refresh_writer_progress')
        current_workspace_record={'configured':True,'ready':True,'trained':True,'jobs':[{'id':'job-a','mode':'write','stage':'completed'}]}
        for current_response_values in (OSError('연결 종료'),[current_workspace_record,RuntimeError('상세 조회 실패')]):
            with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_response_values):
                current_output_values=current_callback_record.fn('job-a','검증',True)
            self.assertEqual(current_output_values[-1],gr.skip())
            self.assertIn('상태 조회 실패',current_output_values[-2])
            for current_component_value,current_output_value in zip(current_callback_record.outputs,current_output_values):
                if isinstance(current_component_value,gr.Button):self.assertFalse(current_output_value['interactive'])
        with patch('tools.review.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,{'status':{'stage':'completed'},'log':'완료 로그'}]):
            current_output_values=current_callback_record.fn('job-a','검증',True)
        self.assertEqual(current_output_values[-1],'완료 로그')
        self.assertTrue(current_output_values[4]['interactive'])
