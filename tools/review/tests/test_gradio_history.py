import inspect
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_history import bind_history_reset_action

from tools.review.common.gradio_history import build_generation_history_view, collect_image_history_thumbnails, format_history_choice_label, format_history_selection_summary, build_history_table_rows


class GradioHistoryTest(unittest.TestCase):
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
        service_command_mock = Mock()
        refresh_history_mock = Mock(return_value=['목록'])
        reset_button_mock = Mock()
        reset_callback_value = bind_history_reset_action((Mock(),reset_button_mock,Mock()),service_command_mock,refresh_history_mock,[Mock()])
        with self.assertRaises(gr.Error):
            reset_callback_value(False)
        service_command_mock.assert_not_called()
        refresh_history_mock.assert_not_called()
        reset_result_values = reset_callback_value(True)
        service_command_mock.assert_called_once_with('history-reset',{'action':'reset'})
        refresh_history_mock.assert_called_once_with()
        self.assertEqual(reset_result_values[0],'목록')
        self.assertFalse(reset_result_values[1])

    def test_reset_failure_does_not_clear_history_view(self):
        service_command_mock = Mock(side_effect=ValueError('실행 중에는 초기화할 수 없습니다.'))
        refresh_history_mock = Mock()
        reset_callback_value = bind_history_reset_action((Mock(),Mock(),Mock()),service_command_mock,refresh_history_mock,[])
        with self.assertRaisesRegex(gr.Error,'실행 중'):
            reset_callback_value(True)
        refresh_history_mock.assert_not_called()

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
        self.assertFalse(current_refresh_result['data'][7]['visible'])

    def test_refresh_explicitly_preserves_existing_selection(self):
        with gr.Blocks():
            read_history_callback, history_output_components = build_generation_history_view(
                lambda command_name, request_payload: {'records': [{'id': 'current-job', 'status': 'completed'}]},
                'http://localhost', '테스트 기록')
        current_refresh_values = read_history_callback(1, 'current-job')
        self.assertEqual(current_refresh_values[0]['value'], 'current-job')
        self.assertTrue(current_refresh_values[7]['visible'])

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
