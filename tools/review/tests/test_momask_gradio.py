"""Gradio 클라이언트의 공용 명령·프롬프트·재생 계약 검증."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[3]
MODULE_SOURCE_SPEC=importlib.util.spec_from_file_location('momask_gradio',WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio/momask_app.py')
MODULE_SOURCE_VALUE=importlib.util.module_from_spec(MODULE_SOURCE_SPEC)
MODULE_SOURCE_SPEC.loader.exec_module(MODULE_SOURCE_VALUE)

class GradioMoMaskTests(unittest.TestCase):
    def test_saved_inputs_use_record_not_current_configuration(self):
        saved_status_record = {'request': {'action': 'walking', 'directions': ['up_left'], 'face': False}, 'prompt': 'Historical prompt.', 'prompt_word_count': 2}
        with patch.object(MODULE_SOURCE_VALUE, 'execute_motion_command', return_value=saved_status_record) as gateway_call_value:
            saved_input_record = MODULE_SOURCE_VALUE.read_saved_motion_inputs('saved-id')
            self.assertEqual(saved_input_record['prompt'], 'Historical prompt.')
            restored_input_values = MODULE_SOURCE_VALUE.restore_saved_motion_inputs('saved-id')
            self.assertEqual(restored_input_values[:3], ('walking', ['up_left'], False))
            self.assertIn('동일 결과 재생성을 보장하지 않습니다', restored_input_values[-1])
            self.assertTrue(all(current_call.args[0] == 'status' for current_call in gateway_call_value.call_args_list))

    def test_restore_rejects_unsupported_saved_input(self):
        saved_status_record = {'request': {'action': 'unknown', 'directions': ['up_left'], 'face': False}, 'prompt': None, 'prompt_word_count': None}
        with patch.object(MODULE_SOURCE_VALUE, 'execute_motion_command', return_value=saved_status_record):
            with self.assertRaises(Exception):
                MODULE_SOURCE_VALUE.restore_saved_motion_inputs('saved-id')

    def test_generate_uses_shared_gateway(self):
        with patch.object(MODULE_SOURCE_VALUE,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(MODULE_SOURCE_VALUE.start_motion_generation('walking',['down_left'],True),'sample')
            gateway_call_value.assert_called_once_with('momask','generate',{'action':'walking','directions':['down_left'],'face':True})

    def test_settings_read_shared_configuration(self):
        prompt_text_value,summary_text_value=MODULE_SOURCE_VALUE.read_motion_settings('walking')
        self.assertIn('centerline',prompt_text_value)
        self.assertIn('25°',summary_text_value)

    def test_action_choices_do_not_include_deep_breath(self):
        self.assertNotIn(('심호흡','deep_breath'),MODULE_SOURCE_VALUE.MOTION_ACTION_LABELS)

    def test_player_keeps_frame_count_and_directions(self):
        player_html_value=MODULE_SOURCE_VALUE.create_motion_player('sample',{'frames':32,'directions':['up_left']},'http://127.0.0.1:8770')
        self.assertIn('allow-scripts',player_html_value)
        self.assertIn('up_left',player_html_value)
        self.assertIn('HumanML3D',player_html_value)

    def test_interface_builds(self):
        self.assertGreater(len(MODULE_SOURCE_VALUE.build_momask_interface('http://127.0.0.1:8770').blocks),30)
