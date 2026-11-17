import unittest
import gradio as gr
import tempfile
from unittest.mock import patch

from tools.review.ui.gradio import hermes_agent_app
from tools.review.ui.gradio.management_menu_app import load_manager_page_records
from tools.review.common.management_asgi import build_management_blocks
from pathlib import Path


class HermesGradioTests(unittest.TestCase):
    def test_management_page_composes_with_menu(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_source_path = Path(hermes_temporary_root) / 'manager.json'
            hermes_source_path.write_text('{"pages":[]}')
            hermes_page_records = load_manager_page_records(hermes_source_path)
            self.assertIn('hermes-agent', [hermes_page_record['id'] for hermes_page_record in hermes_page_records])
            self.assertEqual(next(current_page_record['label'] for current_page_record in hermes_page_records if current_page_record['id'] == 'hermes-agent'), 'Hermes 관리 에이전트')
            with patch.dict('os.environ', {'SLIME_MANAGEMENT_MENU_SOURCE': str(Path(hermes_temporary_root) / 'missing.json')}):
                hermes_interface_blocks, hermes_mount_options = build_management_blocks('hermes-agent', 8770, hermes_source_path)
            hermes_component_labels = [getattr(hermes_component_value, 'label', None) for hermes_component_value in hermes_interface_blocks.blocks.values()]
            self.assertIn('작업 지시', hermes_component_labels)
            self.assertIn('세션 메시지', hermes_component_labels)
            self.assertIn('대화', hermes_component_labels)
            self.assertIn('검토용 변경 diff', hermes_component_labels)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_proposal_loading_clears_previous_review_without_submitting(self, current_gateway_mock):
        current_gateway_mock.return_value = {'proposal': {'prompt':'walk', 'frames':90, 'steps':100, 'seed':42}}
        current_input_values = hermes_agent_app.load_hermes_kimodo_proposal('2026-11-18_00-00-00-12345678')
        self.assertEqual(current_input_values[:4], ('walk', 90, 100, 42))
        self.assertIsNone(current_input_values[5])
        self.assertFalse(current_input_values[8]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-kimodo-proposal', {'id':'2026-11-18_00-00-00-12345678'})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_receipt_lookup_does_not_resubmit(self, current_gateway_mock):
        current_gateway_mock.return_value = {'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertEqual(hermes_agent_app.read_hermes_delegation_receipt('request_123456')[0], '2026-11-18_00-00-00-12345678')
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-delegation-status', {'request_id':'request_123456'})
        current_gateway_mock.return_value = {'state':'unknown'}
        self.assertIn('확인 필요', hermes_agent_app.read_hermes_delegation_receipt('request_123456')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancel_review_pins_receipt_before_request(self, current_gateway_mock):
        current_job_id = '2026-11-18_00-00-00-12345678'
        current_gateway_mock.return_value = {'state':'accepted', 'job_id':current_job_id}
        current_cancel_record, current_group_update, current_summary_text = hermes_agent_app.review_hermes_kimodo_cancellation('request_123456', current_job_id)
        self.assertTrue(current_group_update['visible'])
        self.assertIn(current_job_id, current_summary_text)
        self.assertEqual(current_gateway_mock.call_count, 1)
        with self.assertRaises(gr.Error):
            hermes_agent_app.review_hermes_kimodo_cancellation('request_123456', 'other')
        current_gateway_mock.return_value = {'job_id':current_job_id, 'cancel_requested':True, 'status':'running'}
        self.assertIn('실제 종료', hermes_agent_app.submit_hermes_kimodo_cancellation(current_cancel_record)[2])
        current_gateway_mock.assert_called_with('hermes-agent', 'hermes-delegation-cancel', current_cancel_record)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_delegation_history_selection_clears_stale_confirmation(self, current_gateway_mock):
        current_gateway_mock.side_effect = [{'records':[{'request_id':'request_123456', 'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}], 'truncated':False}, {'state':'accepted','job_id':'2026-11-18_00-00-00-12345678'}]
        current_choices_value, current_message_text = hermes_agent_app.list_hermes_delegation_choices()
        self.assertEqual(current_choices_value['choices'][0][1], 'request_123456')
        self.assertIn('1개', current_message_text)
        current_selection_value = hermes_agent_app.select_hermes_delegation_receipt('request_123456')
        self.assertEqual(current_selection_value[:2], ('request_123456','2026-11-18_00-00-00-12345678'))
        self.assertIsNone(current_selection_value[3])
        self.assertIsNone(current_selection_value[5])
        self.assertFalse(current_selection_value[6]['visible'])
        self.assertFalse(current_selection_value[7]['interactive'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_status_is_concise_and_reports_failure(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'failed','error':'메모리 보호','progress':{'percent':20},'quality_warnings':['확인 필요'],'log':'private large log'}
        current_status_text = hermes_agent_app.read_hermes_kimodo_job('2026-11-18_00-00-00-12345678')
        self.assertIn('실패', current_status_text)
        self.assertIn('메모리 보호', current_status_text)
        self.assertIn('20%', current_status_text)
        self.assertIn('확인 필요', current_status_text)
        self.assertNotIn('private large log', current_status_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_status_surfaces_pose_shape_warning_without_dumping_logs(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'completed', 'log':'onnxruntime VerifyOutputSizes output simcc_x', 'video':'/kimodo/job/video'}
        current_status_text = hermes_agent_app.read_hermes_kimodo_job('2026-11-18_00-00-00-12345678')
        self.assertIn('DWPose 출력 형상 경고', current_status_text)
        self.assertIn('품질을 확인', current_status_text)
        self.assertNotIn('onnxruntime VerifyOutputSizes', current_status_text)

    def test_kimodo_input_change_invalidates_review(self):
        current_review_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        for current_inputs_value in [('walk backward',90,100,42,'request_123456'), ('walk forward',91,100,42,'request_123456'), ('walk forward',90,100,42,'different_123456')]:
            with self.subTest(inputs=current_inputs_value):
                current_invalidated_value = hermes_agent_app.invalidate_hermes_kimodo_review(current_review_value, *current_inputs_value)
                self.assertIsNone(current_invalidated_value[0])
                self.assertIn('다시 검토', current_invalidated_value[2])
                self.assertFalse(current_invalidated_value[3]['interactive'])
        current_same_value = hermes_agent_app.invalidate_hermes_kimodo_review(current_review_value, 'walk forward',90,100,42,'request_123456')
        self.assertEqual(current_same_value, (gr.skip(),gr.skip(),gr.skip(),gr.skip()))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_submit_rejects_stale_review_even_if_change_event_is_delayed(self, current_gateway_mock):
        current_review_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_kimodo_reviewed_request(current_review_value, 'walk backward', 90, 100, 42, 'request_123456')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value = {'state':'accepted','duplicate':False,'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertEqual(hermes_agent_app.submit_hermes_kimodo_reviewed_request(current_review_value, 'walk forward', 90, 100, 42, 'request_123456')[0], '2026-11-18_00-00-00-12345678')
        current_gateway_mock.assert_called_once()

    def test_kimodo_review_freezes_request_and_rejects_invalid_input(self):
        current_snapshot_value, current_preview_value, current_message_text = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        self.assertIn('walk forward', current_preview_value)
        self.assertIn('request_123456', current_preview_value)
        self.assertEqual(current_snapshot_value['request']['prompt'], 'walk forward')
        self.assertIn('공용 GPU 대기열', current_message_text)
        current_invalid_snapshot, _, current_invalid_message = hermes_agent_app.review_hermes_kimodo_request('walk forward', 1, 100, 42, 'request_123456')
        self.assertIsNone(current_invalid_snapshot)
        self.assertIn('실패', current_invalid_message)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_confirmation_preserves_unknown_and_existing_id(self, current_gateway_mock):
        current_snapshot_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        current_gateway_mock.return_value = {'state':'unknown'}
        self.assertIn('확인 필요', hermes_agent_app.submit_hermes_kimodo_request(current_snapshot_value)[1])
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-delegate-kimodo', current_snapshot_value)
        current_gateway_mock.return_value = {'state':'accepted', 'duplicate':True, 'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertIn('기존 접수', hermes_agent_app.submit_hermes_kimodo_request(current_snapshot_value)[1])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_kimodo_request(None)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_management_summary_distinguishes_unavailable(self, current_gateway_mock):
        from tools.review.ui.gradio.hermes_agent_app import read_hermes_management_summary
        current_gateway_mock.return_value = {'model': {'status':'unavailable'}, 'gpu': {'status':'unavailable'}, 'queue': {'status':'unavailable'}, 'queried_at':'now'}
        current_summary_text = read_hermes_management_summary()
        self.assertIn('Hermes 모델: 조회 불가', current_summary_text)
        self.assertIn('Kimodo: 조회 불가 · 조회 불가', current_summary_text)
        self.assertIn('메모리: 조회 불가', current_summary_text)
        self.assertIn('최근 Hermes 작업: 조회 불가', current_summary_text)
        self.assertIn('GPU 예약 기록: 조회 불가', current_summary_text)
        self.assertIn('GPU: unavailable', current_summary_text)
        self.assertIn('대기: 조회 불가', current_summary_text)
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-management-status', {})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_diff_pages_preserve_utf8_at_chunk_boundary(self, current_gateway_mock):
        import base64
        current_diff_bytes = b'a' * 65535 + '가나다'.encode('utf-8')
        def current_chunk_response(current_service_name, current_command_name, current_payload_value):
            self.assertEqual((current_service_name, current_command_name), ('hermes-agent', 'hermes-diff'))
            current_offset_value = current_payload_value['offset']
            current_chunk_value = current_diff_bytes[current_offset_value:current_offset_value + current_payload_value['limit']]
            current_next_value = current_offset_value + len(current_chunk_value)
            return {'id':current_payload_value['id'],'offset':current_offset_value,'size_bytes':len(current_diff_bytes),'data_base64':base64.b64encode(current_chunk_value).decode(),'next_offset':current_next_value if current_next_value < len(current_diff_bytes) else None}
        current_gateway_mock.side_effect = current_chunk_response
        current_first_text, current_first_message, current_cursor_value = hermes_agent_app.start_hermes_diff_pages('job-1')
        self.assertEqual(current_cursor_value['next_offset'], 65535)
        current_second_text, current_second_message, current_cursor_value = hermes_agent_app.read_hermes_diff_page('job-1', current_cursor_value)
        self.assertEqual(current_first_text + current_second_text, current_diff_bytes.decode('utf-8'))
        self.assertIn('마지막 부분', current_second_message)
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('job-1', current_cursor_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('other-job', current_cursor_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_diff_pages_reject_changed_size_and_invalid_offsets(self, current_gateway_mock):
        current_gateway_mock.return_value = {'id':'job-1','offset':0,'size_bytes':4,'data_base64':'YQ==','next_offset':3}
        with self.assertRaises(gr.Error):
            hermes_agent_app.start_hermes_diff_pages('job-1')
        current_gateway_mock.return_value = {'id':'job-1','offset':2,'size_bytes':5,'data_base64':'YQ==','next_offset':3}
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('job-1', {'job_id':'job-1','next_offset':2,'size_bytes':4})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_capability_rows_explain_side_effects(self, current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'label':'Kimodo 작업 상태','effect':'recovery_possible','gpu':'none','note':'중단 작업 복구 가능'}]}
        current_rows_value, current_status_value = hermes_agent_app.read_hermes_capability_rows()
        self.assertEqual(current_rows_value[0][1], '상태 복구 가능')
        self.assertIn('1개', current_status_value)
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-capabilities', {})

    def test_valid_proposal_is_presented_without_exposing_format(self):
        current_answer_value = '사람이 걷는 모션입니다.\nHERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
        current_display_value = hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('사람이 걷는 모션입니다.', current_display_value)
        self.assertIn('제안을 불러와 검토', current_display_value)
        self.assertNotIn('HERMES_KIMODO_PROPOSAL', current_display_value)
        self.assertEqual(hermes_agent_app.format_hermes_conversation_answer(current_answer_value, True), current_answer_value)
        current_invalid_value = current_answer_value.replace('"seed":42', '"seed":42,"url":"bad"')
        self.assertEqual(hermes_agent_app.format_hermes_conversation_answer(current_invalid_value), current_invalid_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_displays_tool_activity_before_final_answer(self, current_gateway_mock):
        current_gateway_mock.return_value = {'message_count':1, 'queried_at':'now', 'messages':[{'text':'질문','job_id':'job-1','job':{'status':{'status':'completed'},'final_response':'최종 답변','tool_activity':{'events':[{'type':'tool_use','name':'terminal','target':'상태 조회','timestamp':'now'},{'type':'tool_result','name':'terminal','result':'success'}],'truncated':False}}}]}
        current_conversation_values = hermes_agent_app.read_hermes_session_conversation('a' * 32)[0]
        self.assertIn('호출 terminal · 상태 조회', current_conversation_values[1]['content'])
        self.assertIn('결과 terminal · 성공', current_conversation_values[1]['content'])
        self.assertIn('최종 답변', current_conversation_values[2]['content'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_conversation_reads_existing_job_and_reports_truncation(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'message_count': 1, 'queried_at':'2026-11-17T14:00:00+00:00', 'messages': [{'text': '첫 질문', 'job_id': 'job-1', 'context_truncated': True, 'job': {'status': {'status':'completed'}, 'final_response':'첫 답변', 'final_response_truncated':False}}]}
        hermes_conversation_values, hermes_session_message, hermes_timer_update, hermes_job_update = hermes_agent_app.read_hermes_session_conversation('a' * 32)
        self.assertEqual(hermes_conversation_values[0], {'role': 'user', 'content': '첫 질문'})
        self.assertIn('첫 답변', hermes_conversation_values[1]['content'])
        self.assertIn('이전 문맥 일부', hermes_conversation_values[1]['content'])
        self.assertIn('메시지 1개', hermes_session_message)
        self.assertFalse(hermes_timer_update['active'])
        self.assertEqual(hermes_job_update['value'], 'job-1')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-view', {'session_id':'a' * 32})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_job_opens_existing_details(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'status': {'status': 'completed'}, 'diff': 'diff', 'diff_truncated': False, 'log': 'log', 'result': None, 'final_response':'답변'}
        hermes_detail_values = hermes_agent_app.open_hermes_session_job('job-1')
        self.assertEqual(hermes_detail_values[:4], ('job-1', 'completed', '답변', 'diff'))
        self.assertIn('확인할 수 없습니다', hermes_detail_values[-2])
        self.assertTrue(hermes_detail_values[-1]['open'])
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-detail', {'id':'job-1'})
        with self.assertRaises(gr.Error):
            hermes_agent_app.open_hermes_session_job(None)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_pending_session_request_restores_original_id_and_inputs(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'messages': [{'request_id':'original-request-1234', 'text':'원래 질문', 'verification_modules':['tools.review.tests.test_hermes_service'], 'job_id':None}]}
        hermes_restored_values = hermes_agent_app.recover_hermes_session_request('a' * 32)
        self.assertEqual(hermes_restored_values[:3], ('original-request-1234', '원래 질문', 'tools.review.tests.test_hermes_service'))
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-read', {'session_id':'a' * 32})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_submission_uses_request_identifier_and_rotates_after_acknowledgement(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'job_id': 'job-1', 'duplicate': False, 'context_truncated': True}
        hermes_job_identifier, hermes_status_message, hermes_next_request, hermes_timer_update = hermes_agent_app.submit_hermes_session_request('a' * 32, 'same-request-1234', '질문')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-submit', {'session_id':'a' * 32, 'request_id':'same-request-1234', 'prompt':'질문'})
        self.assertEqual(hermes_job_identifier, 'job-1')
        self.assertIn('일부만', hermes_status_message)
        self.assertNotEqual(hermes_next_request, 'same-request-1234')
        self.assertTrue(hermes_timer_update['active'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_selecting_history_loads_selected_job_details(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'status': {'status': 'completed'}, 'diff': '변경', 'diff_truncated': False, 'log': '기록', 'result': {'verification': {'status': 'passed'}}, 'final_response': '완료했습니다.', 'request': {'prompt':'전체 지시문'}}
        hermes_history_rows = [['first-job', 'failed', '첫 작업'], ['second-job', 'completed', '둘째 작업']]
        hermes_selected_event = gr.SelectData(None, {'index': (1, 2), 'value': '둘째 작업'})
        hermes_selected_values = hermes_agent_app.select_hermes_history_record(hermes_history_rows, hermes_selected_event)
        self.assertEqual(hermes_selected_values, ('second-job', 'completed · 독립 검증 통과', '완료했습니다.', '변경', '기록', {'verification': {'status': 'passed'}}, '전체 지시문'))
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-detail', {'id': 'second-job'})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_selecting_stale_history_does_not_request_another_job(self, hermes_gateway_mock):
        for hermes_selected_index in ((5, 0), (-1, 0), (True, 0), ()):
            with self.subTest(index=hermes_selected_index), self.assertRaises(gr.Error):
                hermes_agent_app.select_hermes_history_record([['first-job', 'completed', '작업']], gr.SelectData(None, {'index': hermes_selected_index, 'value': None}))
        hermes_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_passes_stable_request_identifier(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_job_identifier, hermes_status_text = hermes_agent_app.submit_hermes_work_request('작업', 'same-request-1234')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'same-request-1234'})
        self.assertEqual(hermes_job_identifier, '2026-11-17_10-00-00-12345678')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command', side_effect=ValueError('지원하지 않는 관리 명령'))
    def test_history_explains_gateway_version_error(self, hermes_gateway_mock):
        hermes_history_rows, hermes_history_message = hermes_agent_app.refresh_hermes_work_history()
        self.assertEqual(hermes_history_rows, [])
        self.assertIn('게이트웨이 실행 상태와 버전', hermes_history_message)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_includes_selected_verification_modules(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_agent_app.submit_hermes_work_request('작업', 'request-1234', 'tools.review.tests.test_hermes_service\n')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'request-1234', 'verification_modules':['tools.review.tests.test_hermes_service']})


if __name__ == '__main__':
    unittest.main()
