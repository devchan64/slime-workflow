"""캐릭터 애니메이션 Gradio 클라이언트 계약을 검증한다."""
import unittest
from unittest.mock import patch

from tools.review.ui.gradio import character_animation_app


class CharacterAnimationGradioTests(unittest.TestCase):
    def test_generate_uses_shared_gateway(self):
        with patch.object(character_animation_app,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(character_animation_app.execute_animation_gateway('generate',{'motion':'standing-v7'}),{'id':'sample'})
            gateway_call_value.assert_called_once_with('character-animation','generate',{'motion':'standing-v7'})

    def test_result_player_has_frame_controls(self):
        player_html_text=character_animation_app.create_animation_player('sample',{'result':{'frames':{'down_left':['down_left/frame-0001/result.png']},'fps':4}},'http://127.0.0.1:8770')
        self.assertIn('이전',player_html_text)
        self.assertIn('character-animation/files',player_html_text)

    def test_motion_preview_player_has_pose_asset_and_controls(self):
        preview_html_text=character_animation_app.create_motion_preview_player('standing-v8','anny','down_left',10,20,'http://127.0.0.1:8770')
        self.assertIn('character-animation/asset/standing-v8/anny/down_left/10',preview_html_text)
        self.assertIn('재생',preview_html_text)

    def test_restore_animation_inputs_uses_historical_request(self):
        restored_input_values=character_animation_app.restore_animation_inputs({'request':{'motion':'standing-v7','character':'anny-v1','source':'anny','directions':['down_left'],'start_frame':10,'end_frame':20,'resolution':768,'steps':30,'target_fps':2,'speed':1.5}})
        self.assertEqual(restored_input_values[:10],('standing-v7','anny-v1','anny',['down_left'],10,20,768,30,2,1.5))
