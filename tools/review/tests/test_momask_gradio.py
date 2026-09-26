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
    def test_generate_uses_shared_gateway(self):
        with patch.object(MODULE_SOURCE_VALUE,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(MODULE_SOURCE_VALUE.start_motion_generation('walking',['down_left'],True),'sample')
            gateway_call_value.assert_called_once_with('momask','generate',{'action':'walking','directions':['down_left'],'face':True})

    def test_settings_read_shared_configuration(self):
        prompt_text_value,summary_text_value,_=MODULE_SOURCE_VALUE.read_motion_settings('walking')
        self.assertIn('centerline',prompt_text_value)
        self.assertIn('25°',summary_text_value)

    def test_player_keeps_frame_count_and_directions(self):
        player_html_value=MODULE_SOURCE_VALUE.create_motion_player('sample',{'frames':32,'directions':['up_left']},'http://127.0.0.1:8770')
        self.assertIn('allow-scripts',player_html_value)
        self.assertIn('up_left',player_html_value)
        self.assertIn('HumanML3D',player_html_value)

    def test_interface_builds(self):
        self.assertGreater(len(MODULE_SOURCE_VALUE.build_momask_interface('http://127.0.0.1:8770').blocks),30)
