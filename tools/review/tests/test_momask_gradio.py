"""Gradio 클라이언트의 공용 명령·프롬프트·재생 계약 검증."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[3]
MODULE_SOURCE_SPEC=importlib.util.spec_from_file_location('momask_gradio',WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio/momask_app.py')
MODULE_SOURCE_VALUE=importlib.util.module_from_spec(MODULE_SOURCE_SPEC)
MODULE_SOURCE_SPEC.loader.exec_module(MODULE_SOURCE_VALUE)

class GradioMoMaskTests(unittest.TestCase):
    def test_saved_inputs_use_record_not_current_configuration(self):
        saved_status_record = {'request': {'action': 'walking', 'directions': ['up_left'], 'face': False, 'tag':'돌온재 걷기'}, 'prompt': 'Historical prompt.', 'prompt_word_count': 2}
        with patch.object(MODULE_SOURCE_VALUE, 'execute_motion_command', return_value=saved_status_record) as gateway_call_value:
            saved_input_record = MODULE_SOURCE_VALUE.read_saved_motion_inputs('saved-id')
            self.assertEqual(saved_input_record['prompt'], 'Historical prompt.')
            restored_input_values = MODULE_SOURCE_VALUE.restore_saved_motion_inputs('saved-id')
            self.assertEqual(restored_input_values[:3], ('walking', ['up_left'], False))
            self.assertEqual(restored_input_values[3], '돌온재 걷기')
            self.assertIn('동일 결과 재생성을 보장하지 않습니다', restored_input_values[-1])
            self.assertTrue(all(current_call.args[0] == 'status' for current_call in gateway_call_value.call_args_list))

    def test_restore_rejects_unsupported_saved_input(self):
        saved_status_record = {'request': {'action': 'unknown', 'directions': ['up_left'], 'face': False}, 'prompt': None, 'prompt_word_count': None}
        with patch.object(MODULE_SOURCE_VALUE, 'execute_motion_command', return_value=saved_status_record):
            with self.assertRaises(Exception):
                MODULE_SOURCE_VALUE.restore_saved_motion_inputs('saved-id')

    def test_card_history_restore_adapts_record_to_identifier(self):
        with patch.object(MODULE_SOURCE_VALUE,'restore_saved_motion_inputs',return_value=('walking',)) as restore_input_mock:
            self.assertEqual(MODULE_SOURCE_VALUE.restore_motion_history_record({'id':'saved-id'}),('walking',))
            restore_input_mock.assert_called_once_with('saved-id')

    def test_generate_uses_shared_gateway(self):
        with patch.object(MODULE_SOURCE_VALUE,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(MODULE_SOURCE_VALUE.start_motion_generation('walking',['down_left'],True,' 돌온재 '),'sample')
            gateway_call_value.assert_called_once_with('momask','generate',{'action':'walking','directions':['down_left'],'face':True,'tag':'돌온재'})

    def test_settings_read_shared_configuration(self):
        prompt_text_value,summary_text_value=MODULE_SOURCE_VALUE.read_motion_settings('walking')
        self.assertIn('treadmill',prompt_text_value)
        self.assertIn('gaze slightly lowered',prompt_text_value)
        self.assertIn('30°',summary_text_value)

    def test_action_choices_do_not_include_deep_breath(self):
        self.assertNotIn(('심호흡','deep_breath'),MODULE_SOURCE_VALUE.MOTION_ACTION_LABELS)

    def test_action_choices_include_resting(self):
        self.assertIn(('휴식','resting'),MODULE_SOURCE_VALUE.MOTION_ACTION_LABELS)

    def test_resting_settings_use_fixed_prompt(self):
        prompt_text_value, summary_text_value = MODULE_SOURCE_VALUE.read_motion_settings('resting')
        self.assertEqual(prompt_text_value, 'A person stands fully upright with both feet planted for a few seconds, sits with buttocks on the ground and legs forward for a few seconds, then stands fully upright again.')
        self.assertIn('160프레임', summary_text_value)

    def test_player_keeps_frame_count_and_directions(self):
        player_html_value=MODULE_SOURCE_VALUE.create_motion_player('sample',{'frames':32,'directions':['up_left']},'http://127.0.0.1:8770')
        self.assertIn('allow-scripts',player_html_value)
        self.assertIn('up_left',player_html_value)
        self.assertIn('HumanML3D',player_html_value)

    def test_completed_history_card_uses_first_result_frame_as_thumbnail(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name,patch.object(MODULE_SOURCE_VALUE,'WORKFLOW_ROOT_DIRECTORY',Path(temporary_directory_name)):
            result_frame_path=Path(temporary_directory_name)/'.tmp/momask-generator/jobs/completed-id/result/anny/down_left/frames/anny-0001.png'
            result_frame_path.parent.mkdir(parents=True)
            result_frame_path.write_bytes(b'image')
            with patch.object(MODULE_SOURCE_VALUE,'execute_motion_command',side_effect=lambda operation,payload: [{'id':'completed-id','status':'completed','action':'walking','directions':['down_left'],'tag':'돌온재'}, {'id':'running-id','status':'running','action':'standing','directions':[]}] if operation=='history' else {'progress':{'percent':25}}):
                history_records=MODULE_SOURCE_VALUE.create_motion_history_records('http://127.0.0.1:8770')['records']
        self.assertEqual(history_records[0]['image'],'/momask-generator/jobs/completed-id/result/anny/down_left/frames/anny-0001.png')
        self.assertEqual(history_records[0]['request']['tag'],'돌온재')
        self.assertNotIn('image',history_records[1])
        self.assertEqual(history_records[1]['progress']['percent'],25)

    def test_interface_builds(self):
        self.assertGreater(len(MODULE_SOURCE_VALUE.build_momask_interface('http://127.0.0.1:8770').blocks),30)

    def test_interface_uses_single_workspace_without_tabs(self):
        interface_source_text=(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio/momask_app.py').read_text()
        self.assertNotIn('gr.Tab(',interface_source_text)
        self.assertIn('### 새 모션 생성',interface_source_text)
        self.assertIn("gr.Accordion('위치 채널 기반 공통 리타깃', open=False,elem_id='motion-retarget-policy')",interface_source_text)
        self.assertIn('build_generation_history_view(',interface_source_text)
        self.assertNotIn("gr.Gallery(label='이미지가 있는 생성 이력'",interface_source_text)
        self.assertIn("gr.Button('현재 생성 취소'",interface_source_text)
        self.assertNotIn("gr.Accordion('생성 ID로 직접 결과 조회'",interface_source_text)
