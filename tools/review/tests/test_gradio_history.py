import inspect
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_history import bind_history_reset_action, build_history_reset_controls

from tools.review.common.gradio_history import build_generation_history_view, collect_image_history_thumbnails, format_history_choice_label, format_history_selection_summary, build_history_table_rows


class GradioHistoryTest(unittest.TestCase):
    def test_delete_readiness_tracks_completion_missing_and_recovery(self):
        current_fixture_state={'status':'running','failure':False,'exists':True}
        current_command_calls=[]
        def execute_fixture_command(current_command_name,current_payload_record):
            current_command_calls.append(current_command_name)
            if current_command_name=='history':
                return {'records':[{'id':'existing-job'}] if current_fixture_state['exists'] else []}
            if current_fixture_state['failure'] or not current_fixture_state['exists']:
                raise RuntimeError('상태 조회 연결 오류')
            return {'status':current_fixture_state['status']}
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(execute_fixture_command,'http://localhost','격리 검증',allow_individual_delete=True)
        current_delete_functions=[current_function for current_function in current_interface_blocks.fns.values() if current_function.name=='update_history_delete_button']
        self.assertEqual(len(current_delete_functions),1)
        current_delete_callback=current_delete_functions[0].fn
        self.assertFalse(current_delete_callback('')['interactive'])
        self.assertEqual(current_command_calls,[])
        self.assertFalse(current_delete_callback('existing-job')['interactive'])
        current_fixture_state['status']='completed'
        self.assertTrue(current_delete_callback('existing-job')['interactive'])
        current_fixture_state['failure']=True
        current_failure_update=current_delete_callback('existing-job')
        self.assertFalse(current_failure_update['interactive'])
        self.assertIn('자동 재확인',current_failure_update['value'])
        current_fixture_state['failure']=False
        self.assertTrue(current_delete_callback('existing-job')['interactive'])
        current_fixture_state['exists']=False
        current_missing_update=current_delete_callback('existing-job')
        self.assertFalse(current_missing_update['interactive'])
        self.assertIn('목록 새로고침',current_missing_update['value'])
        self.assertNotIn('history-delete',current_command_calls)

    def test_reset_preview_explains_executor_finalization(self):
        current_preview_record = {'job_count':1,'jobs':[{'path':'job','status':'completed'}],'blocked_jobs':[{'path':'job','status':'completed','reason':'실행 또는 최종 기록 저장 중'}],'can_reset':False,'scope':'복구 불가','notice':'상태 재확인'}
        with gr.Blocks() as current_interface_blocks:
            current_control_values = build_history_reset_controls('삭제 범위')
            bind_history_reset_action(current_control_values, Mock(return_value=current_preview_record), lambda: [], [])
        current_preview_callback = next(value.fn for value in current_interface_blocks.fns.values() if value.fn and value.fn.__name__ == 'preview_history_reset')
        current_preview_values = current_preview_callback()
        self.assertIn('최종 기록 저장 중', current_preview_values[1])
        self.assertFalse(current_preview_values[2]['interactive'])
        self.assertFalse(current_preview_values[3]['interactive'])

    def test_service_lookup_errors_keep_actionable_message(self):
        current_service_mock=Mock()
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(current_service_mock,'','기록 정책')
        current_result_callback=next(value.fn for value in current_interface_blocks.fns.values() if value.fn and value.fn.__name__=='read_selected_result')
        for current_error_class in (ValueError,RuntimeError,OSError):
            current_service_mock.side_effect=current_error_class('완료 기록의 영상 결과 파일이 없습니다: preview.mp4')
            current_result_values=current_result_callback('job-one')
            self.assertIn('결과 조회 실패:',current_result_values[2])
            self.assertIn('preview.mp4',current_result_values[2])
            self.assertFalse(current_result_values[3]['visible'])
            self.assertEqual(current_result_values[4],{})
            self.assertEqual(current_result_values[5]['value'],current_result_values[2])

    def test_missing_image_result_uses_terminal_guidance(self):
        current_service_mock=Mock()
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(current_service_mock,'','기록 정책')
        current_result_callback=next(value.fn for value in current_interface_blocks.fns.values() if value.fn and value.fn.__name__=='read_selected_result')
        for current_status_name in ('completed','failed','cancelled','queued'):
            with self.subTest(status=current_status_name):
                current_service_mock.side_effect=[{'status':current_status_name},{'records':[]}]
                current_result_values=current_result_callback('job-one')
                self.assertFalse(current_result_values[3]['visible'])
                if current_status_name=='queued':
                    self.assertIn('생성 완료 후',current_result_values[2])
                else:
                    self.assertIn('실행 로그를 확인',current_result_values[2])
                    self.assertNotIn('생성 완료 후',current_result_values[2])

    def test_delete_confirmation_pins_identifier_and_cancel_does_not_delete(self):
        current_service_mock=Mock(return_value={'records':[]})
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(current_service_mock,'','기록 정책',allow_individual_delete=True)
        current_callback_values={value.fn.__name__:value.fn for value in current_interface_blocks.fns.values() if value.fn is not None}
        current_open_values=current_callback_values['open_delete_confirmation']('job-one')
        self.assertEqual(current_open_values[1:],('job-one','job-one'))
        self.assertEqual(current_callback_values['close_delete_confirmation']()[1:],('',''))
        current_service_mock.assert_not_called()
        with self.assertRaises(gr.Error):
            current_callback_values['delete_selected_history']('job-two','job-one')
        current_service_mock.assert_not_called()
        current_callback_values['delete_selected_history']('job-one','job-one')
        current_service_mock.assert_any_call('history-delete',{'id':'job-one'})

    def test_reset_requires_confirmation_and_sends_cli_contract(self):
        current_preview_record={'job_count':1,'jobs':[{'path':'job','status':'completed'}],'blocked_jobs':[],'can_reset':True,'scope':'복구 불가','notice':'숨긴 작업 포함'}
        service_command_mock = Mock(side_effect=[dict(current_preview_record),{'deleted_jobs':1,'deleted_bytes':12}])
        refresh_history_mock = Mock(return_value=['목록'])
        with gr.Blocks():
            reset_callback_value = bind_history_reset_action(build_history_reset_controls('테스트'),service_command_mock,refresh_history_mock,[])
        with self.assertRaises(gr.Error):
            reset_callback_value(False,None)
        service_command_mock.assert_not_called()
        reset_result_values = reset_callback_value(True,current_preview_record)
        self.assertEqual(service_command_mock.call_args_list[0].args,('history-reset-preview',{}))
        self.assertEqual(service_command_mock.call_args_list[1].args,('history-reset',{'action':'reset','expected_jobs':current_preview_record['jobs']}))
        self.assertEqual(reset_result_values[0],'목록')
        self.assertFalse(reset_result_values[1]['value'])
        with self.assertRaises(gr.Error):reset_callback_value(True,current_preview_record)
        self.assertEqual(service_command_mock.call_count,2)

    def test_reset_failure_does_not_clear_history_view(self):
        service_command_mock = Mock(side_effect=ValueError('실행 중에는 초기화할 수 없습니다.'))
        refresh_history_mock = Mock()
        with gr.Blocks():
            reset_callback_value = bind_history_reset_action(build_history_reset_controls('테스트'),service_command_mock,refresh_history_mock,[])
        with self.assertRaisesRegex(gr.Error,'실행 중'):
            reset_callback_value(True,{'can_reset':True,'jobs':[]})
        refresh_history_mock.assert_not_called()

    def test_reset_preview_cancel_and_changed_target_preserve_files(self):
        current_preview_record={'job_count':0,'jobs':[],'blocked_jobs':[],'can_reset':True,'scope':'복구 불가','notice':'숨긴 작업 포함'}
        current_service_mock=Mock(return_value=current_preview_record)
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(current_service_mock,'','테스트')
        current_callbacks={value.fn.__name__:value.fn for value in current_interface_blocks.fns.values() if value.fn}
        current_result_values=current_callbacks['preview_history_reset']()
        self.assertIn('0개 작업',current_result_values[1])
        current_callbacks['cancel_history_reset'](current_preview_record)
        with self.assertRaises(gr.Error):current_callbacks['execute_confirmed_reset'](True,current_preview_record)
        current_service_mock.assert_called_once_with('history-reset-preview',{})
        current_service_mock.return_value={**current_preview_record,'can_reset':True,'jobs':[{'path':'new','status':'completed'}]}
        with self.assertRaisesRegex(gr.Error,'변경'):
            current_callbacks['execute_confirmed_reset'](True,{'can_reset':True,'jobs':[]})
        self.assertTrue(all(current_call.args[0]!='history-reset' for current_call in current_service_mock.call_args_list))

    def test_history_view_uses_selected_card_as_the_only_result_lookup_entry(self):
        history_view_parameter_names=inspect.signature(build_generation_history_view).parameters

        self.assertNotIn('direct_result_identifier_component',history_view_parameter_names)
        self.assertNotIn('direct_result_button_component',history_view_parameter_names)

    def test_history_choice_includes_status_time_identifier_and_request_summary(self):
        history_choice_label = format_history_choice_label({'id':'tile-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'tile_type':'wall','width':512,'height':512,'steps':30,'seed':10107}})

        self.assertEqual(history_choice_label,'완료 · 2026-09-27 09:15:00\n타일 wall · 너비 512 · 높이 512 · 스텝 30 · 시드 10107\nID · tile-123')

    def test_history_choice_handles_legacy_minimal_record(self):
        self.assertEqual(format_history_choice_label({'id':'legacy-1','status':'failed','request':{}}),'실패 · 시각 없음\n설정 요약 없음\nID · legacy-1')

    def test_history_selection_summary_makes_status_and_identifier_scannable(self):
        summary_text=format_history_selection_summary({'id':'animation-123','created_at':'2026-09-27T09:15:00.123456+09:00','status':{'status':'completed'},'request':{'motion':'standing-v8','action':'generate','start_frame':1,'end_frame':12}})
        self.assertIn('**완료**',summary_text)
        self.assertNotIn('ID: `animation-123`',summary_text)  # ID는 별도 복사 입력란에서 표시한다.
        self.assertIn('모션 standing-v8',summary_text)
        self.assertNotIn('동작 generate',summary_text)
        self.assertNotIn('.123456',summary_text)

    def test_collects_only_image_history_thumbnails(self):
        thumbnail_item_values,thumbnail_identifier_values=collect_image_history_thumbnails([
            {'id':'completed-image','status':{'status':'completed'},'image':'/image-generation/jobs/completed-image/result.png'},
            {'id':'running-image','status':{'status':'running'},'image':None},
        ],'http://127.0.0.1:8770')
        self.assertEqual(thumbnail_item_values,[('http://127.0.0.1:8770/image-generation/jobs/completed-image/result.png','completed · completed-image')])
        self.assertEqual(thumbnail_identifier_values,['completed-image'])

    def test_history_card_uses_tag_and_image_type_as_heading(self):
        rendered_history_html=build_history_table_rows([{'id':'image-123','created_at':'2026-09-27T09:15:00+09:00','status':{'status':'completed'},'request':{'action':'generate','tag':'돌온재 자갈 지면','prompt':'gravel ground','width':512,'steps':4}}])
        self.assertIn('돌온재 자갈 지면',rendered_history_html[0][2])
        self.assertEqual(rendered_history_html[0][3],'')

    def test_result_view_displays_original_and_crop_with_labels(self):
        from tools.review.common.gradio_history import render_generation_images
        rendered_result_html=render_generation_images({'image':'/jobs/sample/result.png','cropped_image':'/jobs/sample/border-crop.png'},'http://127.0.0.1:8770')
        self.assertIn('생성 원본',rendered_result_html)
        self.assertIn('보더 크롭 결과',rendered_result_html)
        self.assertEqual(rendered_result_html.count('<img '),2)
        self.assertIn('http://127.0.0.1:8770/jobs/sample/border-crop.png',rendered_result_html)

    def test_legacy_result_view_does_not_show_missing_crop(self):
        from tools.review.common.gradio_history import render_generation_images
        rendered_result_html=render_generation_images({'image':'/jobs/sample/result.png'},'http://127.0.0.1:8770')
        self.assertEqual(rendered_result_html.count('<img '),1)
        self.assertNotIn('보더 크롭 결과',rendered_result_html)

    def test_refresh_accepts_stale_radio_value_and_clears_removed_selection(self):
        import asyncio
        current_history_records = [{'id': 'current-job', 'status': 'completed'}]
        with gr.Blocks() as current_history_blocks:
            read_history_callback, history_output_components = build_generation_history_view(
                lambda command_name, request_payload: {'records': current_history_records},
                'http://localhost', '테스트 기록')
        history_refresh_function = next(
            current_block_function for current_block_function in current_history_blocks.fns.values()
            if current_block_function.fn is read_history_callback
            and not current_block_function.preprocess)
        # 서버 Radio의 choices가 비어 있어도 오래된 브라우저 ID로 목록 복구가 가능해야 한다.
        current_refresh_result = asyncio.run(current_history_blocks.process_api(
            history_refresh_function, [1, 'removed-job']))
        self.assertIsNone(current_refresh_result['data'][0]['value'])
        self.assertEqual(current_refresh_result['data'][0]['choices'][0][1], 'current-job')
        self.assertFalse(current_refresh_result['data'][6]['visible'])

    def test_refresh_explicitly_preserves_existing_selection(self):
        with gr.Blocks():
            read_history_callback, history_output_components = build_generation_history_view(
                lambda command_name, request_payload: {'records': [{'id': 'current-job', 'status': 'completed'}]},
                'http://localhost', '테스트 기록')
        current_refresh_values = read_history_callback(1, 'current-job')
        self.assertEqual(current_refresh_values[0]['value'], 'current-job')
        self.assertTrue(current_refresh_values[6]['visible'])

    def test_radio_selection_updates_shared_action_handlers(self):
        with gr.Blocks() as current_history_blocks:
            build_generation_history_view(
                lambda command_name, request_payload: {'records': []},
                'http://localhost', '테스트 기록')
        current_blocks_config = current_history_blocks.get_config_file()
        selection_component_identifier = next(
            component_record_value['id'] for component_record_value in current_blocks_config['components']
            if component_record_value.get('props', {}).get('elem_id') == 'generation-history-selection')
        selection_event_names = [
            target_event_name for dependency_record_value in current_blocks_config['dependencies']
            for target_component_identifier, target_event_name in dependency_record_value['targets']
            if target_component_identifier == selection_component_identifier]
        self.assertIn('change', selection_event_names)
        self.assertNotIn('input', selection_event_names)


    def test_history_list_has_no_periodic_full_render(self):
        with gr.Blocks() as current_history_blocks:
            read_history_callback, history_output_components = build_generation_history_view(
                lambda command_name, request_payload: {'records': []},
                'http://localhost', '테스트 기록')
        current_timer_identifiers = {current_component_id for current_component_id, current_component_value in current_history_blocks.blocks.items() if isinstance(current_component_value, gr.Timer)}
        for current_function_value in current_history_blocks.fns.values():
            if current_function_value.fn is read_history_callback:
                self.assertFalse(any(current_target_value[0] in current_timer_identifiers for current_target_value in current_function_value.targets))


class HistoryRadioTableTest(unittest.TestCase):
    def test_identifier_clipboard_enabled_by_default(self):
        from tools.review.common.gradio_history import render_history_selection_table
        current_history_records=[{'id':'sample-id','status':'completed','request':{}}]
        current_table_markup=render_history_selection_table(current_history_records)
        self.assertIn('data-history-copy-id="sample-id"',current_table_markup)
        self.assertIn('aria-live="polite"',current_table_markup)
        current_disabled_markup=render_history_selection_table(current_history_records,enable_identifier_clipboard=False)
        self.assertNotIn('data-history-copy-id',current_disabled_markup)
        self.assertIn('sample-id',current_disabled_markup)

    def test_single_selection_and_escaped_content(self):
        from tools.review.common.gradio_history import render_history_selection_table
        current_table_markup=render_history_selection_table([
            {'id':'first','status':'completed','request':{'tag':'<script>alert(1)</script>'}},
            {'id':'second','status':'cancelled','request':{}}], 'second')
        self.assertEqual(current_table_markup.count('type="radio"'),2)
        self.assertEqual(current_table_markup.count(' checked'),1)
        self.assertIn('value="second" aria-label="second 선택" checked',current_table_markup)
        self.assertNotIn('<script>',current_table_markup)
        self.assertIn('<th scope="col">선택</th>',current_table_markup)
        self.assertIn('<th scope="col">썸네일</th>',current_table_markup)

    def test_thumbnail_column_can_be_omitted(self):
        from tools.review.common.gradio_history import render_history_selection_table
        current_history_records=[{'id':'sound-job','status':{'status':'completed','audio':'/sound.wav'},'request':{},'image':'/image.png'}]
        current_table_markup=render_history_selection_table(current_history_records,'sound-job',show_thumbnail_column=False)
        self.assertNotIn('썸네일',current_table_markup)
        self.assertNotIn('<img',current_table_markup)
        self.assertEqual(current_table_markup.count('<th scope='),6)
        self.assertEqual(current_table_markup.count('<td>'),6)
        self.assertIn(' checked',current_table_markup)
        self.assertIn('data-history-copy-id="sound-job"',current_table_markup)
        with gr.Blocks():
            current_read_history,current_output_components=build_generation_history_view(lambda *_:{'records':current_history_records},'http://localhost','검증',show_thumbnail_column=False)
            current_page_updates=current_read_history(1,'sound-job')
        self.assertNotIn('썸네일',current_page_updates[3])
        self.assertIn(' checked',current_page_updates[3])

    def test_completed_history_row_includes_result_thumbnail(self):
        from tools.review.common.gradio_history import render_history_selection_table
        current_table_markup=render_history_selection_table([
            {'id':'completed-image','status':{'status':'completed'},'request':{},'image':'/image-generation/jobs/completed-image/result.png'}],
            server_base_address='http://127.0.0.1:8770')
        self.assertIn('generation-history-table-thumbnail',current_table_markup)
        self.assertIn('http://127.0.0.1:8770/image-generation/jobs/completed-image/result.png',current_table_markup)


class HistoryRestoreFailureTests(unittest.TestCase):
    def test_state_restore_delivers_change_events_through_queue(self):
        for current_state_enabled in (False, True):
            with self.subTest(state=current_state_enabled), gr.Blocks() as current_interface_blocks:
                current_output_control = gr.State([]) if current_state_enabled else gr.Textbox()
                build_generation_history_view(lambda *_: {'records': []}, 'http://localhost', '격리 검증', restore_input_callback=lambda _: ([],), restore_output_components=[current_output_control])
            current_restore_function = next(current_function for current_function in current_interface_blocks.fns.values() if current_function.name == 'restore_selected_inputs')
            self.assertEqual(current_restore_function.queue, current_state_enabled)

    def test_expected_restore_failure_preserves_inputs_and_reports_reason(self):
        with gr.Blocks() as current_interface_blocks:
            current_prompt_control = gr.Textbox(value='보존할 입력')
            build_generation_history_view(lambda *_:{'records':[{'id':'saved-job','request':{},'status':{'status':'completed'}}]}, 'http://localhost', '격리 검증', restore_input_callback=lambda _: (_ for _ in ()).throw(ValueError('참조 이미지 해시 불일치')), restore_output_components=[current_prompt_control])
        current_restore_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values() if current_function.fn and current_function.fn.__name__=='restore_selected_inputs')
        current_restore_result = current_restore_callback('saved-job')
        self.assertEqual(current_restore_result[0], gr.skip())
        self.assertIn('해시 불일치', current_restore_result[1])
        self.assertEqual(current_prompt_control.value, '보존할 입력')


class HistoryProgressDetailTests(unittest.TestCase):
    def test_selected_result_displays_worker_observation_and_unknown_estimate(self):
        current_status_record = {'status':'running', 'metrics':{'stage':'denoise', 'worker_progress':{'stage':'denoise','step':12,'total':40,'updated_at':'2026-10-15T14:00:00Z'}}}
        def execute_fixture_command(current_command_name, current_payload_record):
            if current_command_name == 'status':
                return current_status_record
            return {'records':[{'id':'sample-job','status':current_status_record,'request':{}}]}
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(execute_fixture_command, 'http://localhost', '격리 검증')
        current_result_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values() if current_function.name == 'read_selected_result')
        current_result_text = current_result_callback('sample-job')[2]
        for current_expected_text in ('작업자 마지막 관측: denoise', '12/40', '전체 예상 진행률과 별개', '2026-10-15T14:00:00Z', '계산 중', 'VRAM: 측정 자료 없음'):
            self.assertIn(current_expected_text, current_result_text)
        self.assertNotIn('30%', current_result_text)

    def test_result_observation_refresh_preserves_media_and_clears_missing_history(self):
        current_status_record = {'status':'running','progress':{'stage':'inference','step':7,'total':40}}
        current_command_calls = []
        current_history_records = [{'id':'sample-job'}]
        def execute_fixture_command(current_command_name, current_payload_record):
            current_command_calls.append(current_command_name)
            if current_command_name == 'history':
                return {'records':current_history_records}
            if not current_history_records:
                raise ValueError('작업 없음')
            return current_status_record
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(execute_fixture_command, 'http://localhost', '격리 검증')
        current_refresh_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values() if current_function.name == 'refresh_combined_history')
        current_combined_callback = current_refresh_callback
        current_refresh_callback = lambda current_job_identifier: tuple(current_combined_callback('', current_job_identifier, False)[3:7])
        current_command_calls.clear()
        self.assertEqual(current_refresh_callback(''), (gr.skip(),)*4)
        self.assertEqual(current_command_calls, [])
        current_refresh_values = current_refresh_callback('sample-job')
        self.assertIn('7/40', current_refresh_values[0])
        self.assertEqual(current_refresh_values[1:], (gr.skip(),)*3)
        current_status_record.update(status='completed')
        self.assertIn('최신 결과는 결과 조회', current_refresh_callback('sample-job')[0])
        current_history_records.clear()
        current_refresh_values = current_refresh_callback('sample-job')
        self.assertIn('삭제되었습니다', current_refresh_values[0])
        self.assertEqual(current_refresh_values[1], '')
        self.assertFalse(current_refresh_values[2]['visible'])
        self.assertEqual(current_refresh_values[3], {})

    def test_deleted_selection_disables_priority_resume_and_cancel_without_exception(self):
        def execute_fixture_command(current_command_name, current_payload_record):
            if current_command_name == 'history':
                return {'records':[]}
            raise ValueError('삭제된 작업')
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(execute_fixture_command, 'http://localhost', '격리 검증')
        current_callbacks = {current_function.name:current_function.fn for current_function in current_interface_blocks.fns.values()}
        self.assertIn('삭제되었습니다',current_callbacks['refresh_combined_history']('deleted-job','deleted-job',True)[3])
        self.assertEqual(current_callbacks['refresh_combined_history']('deleted-job','deleted-job',False)[-2],gr.skip())
        self.assertFalse(current_callbacks['refresh_priority_control']('deleted-job')['interactive'])
        current_button_updates = current_callbacks['refresh_history_controls']('deleted-job')
        self.assertTrue(all(not current_update['interactive'] for current_update in current_button_updates))

    def test_transient_lookup_failure_preserves_result_and_recovers_controls(self):
        current_fixture_state = {'failure':True}
        current_command_calls = []
        def execute_fixture_command(current_command_name, current_payload_record):
            current_command_calls.append(current_command_name)
            if current_command_name == 'history':
                return {'records':[{'id':'existing-job'}]}
            if current_fixture_state['failure']:
                raise RuntimeError('연결 재시도 필요')
            return {'status':'queued','log':'복구된 로그'}
        with gr.Blocks() as current_interface_blocks:
            build_generation_history_view(execute_fixture_command, 'http://localhost', '격리 검증')
        current_callbacks = {current_function.name:current_function.fn for current_function in current_interface_blocks.fns.values()}
        current_result_values=tuple(current_callbacks['refresh_combined_history']('existing-job','existing-job',True)[3:7])
        self.assertIn('연결 재시도 필요',current_result_values[0])
        self.assertEqual(current_result_values[1:],(gr.skip(),)*3)
        self.assertTrue(current_callbacks['refresh_combined_history']('existing-job','existing-job',True)[-1].active)
        self.assertFalse(current_callbacks['refresh_priority_control']('existing-job')['interactive'])
        self.assertTrue(all(not current_update['interactive'] for current_update in current_callbacks['refresh_history_controls']('existing-job')))
        current_command_calls.clear()
        self.assertEqual(current_callbacks['refresh_combined_history']('', '', False)[-2],gr.skip())
        self.assertEqual(current_command_calls,[])
        current_fixture_state['failure']=False
        self.assertTrue(current_callbacks['refresh_priority_control']('existing-job')['interactive'])
        current_cancel_update,current_resume_update=current_callbacks['refresh_history_controls']('existing-job')
        self.assertTrue(current_cancel_update['interactive'])
        self.assertEqual(current_cancel_update['value'],'작업 중지')
        self.assertEqual(current_callbacks['refresh_combined_history']('existing-job','existing-job',True)[-2],'복구된 로그')


class CombinedHistoryPollingTest(unittest.TestCase):
    def test_poll_reads_same_job_once_and_stops_when_completed(self):
        current_command_calls = []
        current_status_record = {'status': 'running', 'log': '진행 중'}

        def execute_test_command(current_command_name, current_request_payload):
            if current_command_name == 'history':
                return {'records': []}
            current_command_calls.append(current_request_payload['id'])
            return current_status_record

        with gr.Blocks() as current_history_blocks:
            build_generation_history_view(execute_test_command, 'http://localhost', '테스트', allow_individual_delete=True)
        current_poll_callback = next(current_function.fn for current_function in current_history_blocks.fns.values() if current_function.name == 'refresh_combined_history')
        current_command_calls.clear()
        current_poll_result = current_poll_callback('job-1', 'job-1', True)
        self.assertEqual(current_command_calls, ['job-1'])
        self.assertTrue(current_poll_result[-1].active)
        current_status_record['status'] = 'completed'
        self.assertFalse(current_poll_callback('job-1', 'job-1', True)[-1].active)
        current_command_calls.clear()
        self.assertFalse(current_poll_callback('', '', True)[-1].active)
        self.assertEqual(current_command_calls, [])
        current_timers = [current_component for current_component in current_history_blocks.blocks.values() if isinstance(current_component, gr.Timer)]
        self.assertEqual(len(current_timers), 1)
        self.assertFalse(current_timers[0].active)
