"""작가 UI의 기본 컴포넌트 및 조회한 제안 적용 계약."""
import unittest
from unittest.mock import patch
import gradio as gr
from gui.ui.gradio.writer_agent_app import build_writer_agent_interface,format_writer_detail


class WriterAgentGradioTest(unittest.TestCase):
    def test_linked_writer_search_clears_other_selection(self):
        from gui.ui.gradio.writer_agent_app import prepare_writer_history_link
        current_job_identifier='20261118-120000-12345678'
        current_interface_value=build_writer_agent_interface(8770)
        current_config_value=current_interface_value.get_config_file()
        self.assertTrue(any(current_component.get('props',{}).get('value')=='전달된 작업을 이력에서 찾기' for current_component in current_config_value['components']))
        self.assertTrue(any("searchParams.get('job')" in str(current_dependency.get('js','')) for current_dependency in current_config_value['dependencies']))
        current_search_callbacks=[current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='search_writer_history_records']
        self.assertEqual(len(current_search_callbacks),2)
        current_link_values=prepare_writer_history_link(current_job_identifier)
        self.assertTrue(current_link_values[1]['visible'])
        current_response_value={'jobs':[{'id':current_job_identifier,'mode':'write','stage':'review','summary':'검토'}],'count':1}
        current_linked_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='search_linked_writer_history')
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value=current_response_value) as current_service_mock:
            current_rows,current_selection,current_count=current_linked_callback(current_link_values[0])
        current_service_mock.assert_called_once_with(8770,'history',{'query':current_job_identifier})
        self.assertEqual(current_rows[0][0],current_job_identifier)
        self.assertEqual(current_selection,current_job_identifier)
        self.assertIn('선택했습니다',current_count)
        for current_jobs_value in ([],[current_response_value['jobs'][0],current_response_value['jobs'][0]],[{'id':'other','mode':'write','stage':'review'}]):
            with self.subTest(jobs=current_jobs_value),patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value={'jobs':current_jobs_value,'count':len(current_jobs_value)}):
                self.assertIsNone(current_linked_callback(current_job_identifier)[1])
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value={'jobs':current_response_value['jobs'],'count':2}):
            current_partial_value=current_linked_callback(current_job_identifier)
            self.assertIsNone(current_partial_value[1])
            self.assertIn('검색에 실패',current_partial_value[2])
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
            self.assertIsNone(current_linked_callback('../invalid')[1])
            current_service_mock.assert_not_called()

    def test_linked_writer_job_uses_real_temporary_history_and_detail(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from urllib.parse import parse_qs
        from generators.writer_agent.documents import save_yaml_document,load_workspace_config
        from generators.writer_agent.jobs import create_writer_job,resolve_job_directory,update_job_status
        from generators.writer_agent.management import WriterAgentManager
        with TemporaryDirectory() as current_temporary_directory:
            current_root_path=Path(current_temporary_directory)
            (current_root_path/'docs'/'ideas').mkdir(parents=True)
            current_workspace_path=current_root_path/'workspace.yaml'
            save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_root_path/'docs'),'state_root':str(current_root_path/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            current_workspace_config=load_workspace_config(current_workspace_path)
            current_job_identifier=create_writer_job(current_workspace_config,{'mode':'write','prompt':'임시 조회 검증'})
            current_job_path=resolve_job_directory(current_workspace_config,current_job_identifier)
            update_job_status(current_job_path,'failed',error='임시 실패')
            current_before_status=(current_job_path/'status.yaml').read_bytes()
            current_manager_value=WriterAgentManager(current_workspace_path)
            current_interface_value=build_writer_agent_interface(8770)
            current_linked_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='search_linked_writer_history')
            current_detail_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='read_writer_selection')
            def execute_temporary_writer_request(current_port_value,current_route_path,current_payload_record=None):
                if current_route_path=='history':return current_manager_value.search_writer_history(current_payload_record['query'])
                if current_route_path.startswith('job?'):return current_manager_value.read_writer_detail(parse_qs(current_route_path.split('?',1)[1])['id'][0])
                raise AssertionError(current_route_path)
            with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=execute_temporary_writer_request):
                current_rows_value,current_selected_identifier,_=current_linked_callback(current_job_identifier)
                current_detail_values=current_detail_callback(current_selected_identifier)
            self.assertEqual(current_rows_value[0][0],current_job_identifier)
            self.assertEqual(current_detail_values[1],current_job_identifier)
            self.assertIn('실패',current_detail_values[3])
            self.assertEqual((current_job_path/'status.yaml').read_bytes(),current_before_status)

    def test_writer_detail_rejects_other_job_and_clears_old_result(self):
        current_interface_value=build_writer_agent_interface(8770)
        current_detail_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='read_writer_selection')
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value={'id':'another-job'}):
            current_result_values=current_detail_callback('20261118-120000-12345678')
        self.assertEqual(current_result_values[0],{})
        self.assertIn('일치하지 않습니다',current_result_values[3])
        self.assertEqual(current_result_values[8],'')
        self.assertFalse(current_result_values[13])

    def test_writer_history_search_failure_clears_selection(self):
        current_interface_value=build_writer_agent_interface(8770)
        current_search_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='search_writer_history_records')
        for current_response_value in (OSError('lost'),{'jobs':[],'count':'bad'},{'jobs':[{}],'count':1},{'jobs':[{'id':'job-a','mode':'write','stage':'review'}],'count':2}):
            with self.subTest(response=current_response_value),patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
                if isinstance(current_response_value,Exception):current_service_mock.side_effect=current_response_value
                else:current_service_mock.return_value=current_response_value
                current_rows,current_selection,current_notice=current_search_callback('job-a','old-job')
                self.assertEqual(current_rows,[])
                self.assertIsNone(current_selection)
                self.assertIn('검색에 실패',current_notice)

    def test_model_readiness_links_to_management_when_not_ready(self):
        current_interface_blocks = build_writer_agent_interface(8770)
        current_links = [current_component for current_component in current_interface_blocks.config['components']
                         if current_component.get('props', {}).get('value') == '모델 관리로 이동']
        self.assertEqual(len(current_links), 1)
        self.assertEqual(current_links[0]['props']['link'], '/management/?tool=model-management&category=model-management')
        current_refresh_callback = next(current_binding.fn for current_binding in current_interface_blocks.fns.values()
                                        if current_binding.fn and current_binding.fn.__name__ == 'refresh_model_readiness_status')
        with patch('gui.ui.gradio.writer_agent_app.execute_remote_management_command', return_value={'ready': False, 'message': '모델 파일 준비 필요'}) as current_gateway_mock:
            current_result_values = current_refresh_callback()
        current_gateway_mock.assert_called_once_with('writer-agent', 'model-status', {})
        self.assertFalse(current_result_values[1])
        self.assertTrue(current_result_values[2]['visible'])
        with patch('gui.ui.gradio.writer_agent_app.execute_remote_management_command', return_value={'ready': True, 'message': '파일 준비 완료'}):
            self.assertFalse(current_refresh_callback()[2]['visible'])

    def test_failed_detail_clears_previous_proposal_and_confirmation(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_read_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='read_writer_selection')
        for current_error_value in (ValueError('조회 거절'), RuntimeError('서비스 오류'), OSError('연결 종료')):
            with self.subTest(error=str(current_error_value)),patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_error_value):
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
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value=current_workspace_record):
            current_empty_values=current_refresh_callback(None,'  ')
            self.assertFalse(current_empty_values[6]['interactive'])
            self.assertTrue(current_empty_values[7]['interactive'])
            self.assertIn('작성 지시를 입력',current_empty_values[8])
            self.assertFalse(current_empty_values[9]['interactive'])
            current_ready_values=current_refresh_callback('job-a','작성 지시')
            self.assertTrue(current_ready_values[6]['interactive'])
            self.assertTrue(current_ready_values[9]['interactive'])
            self.assertEqual(current_refresh_callback('older-job','작성 지시')[3],'older-job')
            current_workspace_record['active_job']='job-running'
            current_busy_values=current_refresh_callback('job-a','작성 지시')
            self.assertFalse(current_busy_values[6]['interactive'])
            self.assertFalse(current_busy_values[7]['interactive'])
            self.assertIn('완료 후',current_busy_values[8])
            current_workspace_record['jobs'].append({'id':'job-running','mode':'learn','stage':'indexing'})
            self.assertIn('문서 학습 · 학습',current_refresh_callback(None)[1])
            current_workspace_record.pop('active_job')
            current_workspace_record['trained']=False
            current_first_values=current_refresh_callback(None)
            self.assertTrue(current_first_values[5]['interactive'])
            self.assertFalse(current_first_values[6]['interactive'])
            self.assertIn('학습 · 색인 갱신',current_first_values[1])

    def test_uses_native_components_without_html(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        self.assertFalse(any(isinstance(current_component_value,gr.HTML) for current_component_value in current_interface_blocks.blocks.values()))
        self.assertTrue(any(isinstance(current_component_value,gr.Dataframe) for current_component_value in current_interface_blocks.blocks.values()))
        self.assertFalse(any(isinstance(current_component_value,gr.Dropdown) for current_component_value in current_interface_blocks.blocks.values()))

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
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
            with self.assertRaises(gr.Error):current_apply_callback({'id':'job-a'},False,'job-a')
            current_service_mock.assert_not_called()

    def test_apply_error_clears_confirmation_without_retry(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_detail_record={'id':'job-a','status':{'stage':'review','proposal_hash':'hash-a'},'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}}
        for current_error_value in (ValueError('원문 변경'),OSError('응답 연결 끊김')):
            with self.subTest(error=str(current_error_value)),patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_error_value) as current_service_mock:
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
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[{},current_detail_record]) as current_service_mock:
            current_output_values=current_apply_callback({**current_detail_record,'status':{'stage':'review','proposal_hash':'hash-a'},'application':None,'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}},True,'job-a')
            self.assertEqual(current_service_mock.call_args_list[0].args,(8770,'apply',{'id':'job-a','proposal_hash':'hash-a'}))
            self.assertFalse(current_output_values[12]['interactive'])

    def test_changed_selection_and_applied_proposal_never_call_service(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        for current_detail_record,current_selection_value in [({'id':'job-a','status':{'stage':'review'}},'job-b'),({'id':'job-a','status':{'stage':'applied'}},'job-a'),({'id':'job-a','status':{'stage':'review'},'application':{'status':'applied'}},'job-a')]:
            with self.subTest(record=current_detail_record),patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
                with self.assertRaises(gr.Error):current_apply_callback(current_detail_record,True,current_selection_value)
                current_service_mock.assert_not_called()

    def test_gui_dispatches_gateway_commands(self):
        from gui.ui.gradio.writer_agent_app import request_writer_service
        with patch('gui.ui.gradio.writer_agent_app.execute_remote_management_command',return_value={}) as current_command_mock:
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
        from workflow.common.management_gateway import execute_gateway_cli,execute_management_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_payload_path=Path(current_directory_name)/'request.json'
            current_payload_path.write_text('{"mode":"learn","prompt":""}')
            with patch('workflow.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock,contextlib.redirect_stdout(io.StringIO()):
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
        self.assertTrue(current_clear_function.outputs)
        current_output_values=current_clear_callback()
        self.assertEqual(len(current_output_values),16)
        for current_output_index in (1,2,5,8,9,11):self.assertEqual(current_output_values[current_output_index],'')
        self.assertEqual(current_output_values[0],{})
        self.assertFalse(current_output_values[12]['interactive'])
        self.assertFalse(current_output_values[13])

    def test_history_row_selects_job_and_selection_loads_detail(self):
        from types import SimpleNamespace
        current_interface_blocks=build_writer_agent_interface(8770)
        current_select_callback=next(current_binding.fn for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='select_writer_history')
        current_load_callback=next(current_binding.fn for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='load_selected_writer_detail')
        current_rows=[['job-a','작성 제안','검토',''],['job-b','문서 학습','완료','']]
        current_selection_update=current_select_callback(current_rows,SimpleNamespace(index=(1,2)))
        self.assertEqual(current_selection_update,'job-b')
        current_detail_record={'id':'job-b','job_path':'/records/job-b','status':{'stage':'completed'},'request':{'mode':'learn'}}
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value=current_detail_record):
            self.assertEqual(current_load_callback('job-b')[1],'job-b')
        self.assertEqual(current_load_callback(None)[0],{})

    def test_search_and_delete_require_current_selection_confirmation(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_search_callback=next(current_binding.fn for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='search_writer_history_records')
        current_delete_callback=next(current_binding.fn for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='delete_selected_writer_history')
        current_readiness_callback=next(current_binding.fn for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='update_writer_delete_readiness')
        current_readiness_values=current_readiness_callback({'id':'job-a','status':{'stage':'completed'}},'job-a',True)
        self.assertTrue(current_readiness_values[0]['interactive'])
        self.assertIn('job-a',current_readiness_values[1])
        current_history_response={'jobs':[{'id':'job-a','mode':'write','stage':'review'}],'count':1}
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value=current_history_response):
            self.assertEqual(current_search_callback('주제','job-a')[1],'job-a')
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
            for current_detail_record,current_selected_identifier,current_confirm_value in (({'id':'job-a'},'job-b',True),({'id':'job-a'},'job-a',False)):
                with self.assertRaises(gr.Error):current_delete_callback(current_detail_record,current_selected_identifier,current_confirm_value,'')
            current_service_mock.assert_not_called()
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[{'id':'job-a','status':'deleted','recoverable':True},{'jobs':[],'count':0}]) as current_service_mock:
            current_result_values=current_delete_callback({'id':'job-a'},'job-a',True,'')
            current_service_mock.assert_any_call(8770,'delete',{'id':'job-a'})
            self.assertEqual(current_result_values[0],[])
            self.assertFalse(current_result_values[3])

    def test_writer_delete_uncertain_response_clears_confirmation(self):
        current_interface_value=build_writer_agent_interface(8770)
        current_delete_callback=next(current_dependency.fn for current_dependency in current_interface_value.fns.values() if current_dependency.fn and current_dependency.fn.__name__=='delete_selected_writer_history')
        for current_response_value in (OSError('lost'),{'id':'other','status':'deleted','recoverable':True},{'id':'job-a','status':'deleted'}):
            with self.subTest(response=current_response_value),patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
                if isinstance(current_response_value,Exception):current_service_mock.side_effect=current_response_value
                else:current_service_mock.return_value=current_response_value
                current_result_values=current_delete_callback({'id':'job-a'},'job-a',True,'')
                self.assertIsNone(current_result_values[1])
                self.assertFalse(current_result_values[3])
                self.assertFalse(current_result_values[4]['interactive'])
                self.assertIn('삭제 결과 확인 필요',current_result_values[5])
                current_service_mock.assert_called_once()

    def test_missing_changes_or_hash_never_dispatches_apply(self):
        current_interface_blocks=build_writer_agent_interface(8770)
        current_apply_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='apply_writer_proposal')
        current_readiness_callback=next(current_function_value.fn for current_function_value in current_interface_blocks.fns.values() if current_function_value.fn and current_function_value.fn.__name__=='update_writer_apply_readiness')
        for current_detail_record in (
            {'id':'job-a','status':{'stage':'review','proposal_hash':'hash-a'},'proposal':{'changes':[]}},
            {'id':'job-a','status':{'stage':'review'},'proposal':{'changes':[{'path':'a.md','diff':'+문장'}]}},
        ):
            with self.subTest(record=current_detail_record),patch('gui.ui.gradio.writer_agent_app.request_writer_service') as current_service_mock:
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
            self.assertFalse(any(isinstance(current_component_value,gr.Dropdown) for current_component_value in current_function_value.outputs))
            self.assertFalse(any(isinstance(current_component_value,gr.Dataframe) for current_component_value in current_function_value.outputs))
        current_workspace_record={'configured':True,'ready':True,'trained':True,'jobs':[{'id':'job-a','mode':'write','stage':'review'}]}
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',return_value=current_workspace_record):
            current_progress_values=current_progress_functions[0].fn(None,'')
        self.assertEqual(len(current_progress_values),len(current_progress_functions[0].outputs))
        current_detail_record={'id':'job-a','status':{'stage':'review','summary':'검토 대기'},'log':'실행 기록'}
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,current_detail_record]):
            current_progress_values=current_progress_functions[0].fn('job-a','')
        self.assertEqual(current_progress_values[-2:],['변경 검토 대기 · 검토 대기','실행 기록'])
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,current_detail_record]):
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
            with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=current_response_values):
                current_output_values=current_callback_record.fn('job-a','검증',True)
            self.assertEqual(current_output_values[-1],gr.skip())
            self.assertIn('상태 조회 실패',current_output_values[-2])
            for current_component_value,current_output_value in zip(current_callback_record.outputs,current_output_values):
                if isinstance(current_component_value,gr.Button):self.assertFalse(current_output_value['interactive'])
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,{'id':'other-job','status':{'stage':'completed'},'log':'다른 작업 로그'}]):
            current_output_values=current_callback_record.fn('job-a','검증',True)
        self.assertEqual(current_output_values[-1],gr.skip())
        self.assertIn('일치하지 않습니다',current_output_values[-2])
        with patch('gui.ui.gradio.writer_agent_app.request_writer_service',side_effect=[current_workspace_record,{'id':'job-a','status':{'stage':'completed'},'log':'완료 로그'}]):
            current_output_values=current_callback_record.fn('job-a','검증',True)
        self.assertEqual(current_output_values[-1],'완료 로그')
        self.assertTrue(current_output_values[4]['interactive'])
