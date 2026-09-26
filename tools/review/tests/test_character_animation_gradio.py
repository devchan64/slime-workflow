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
