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
        self.assertIn('pending.onload',player_html_text)
        self.assertIn('생성 결과 프레임',player_html_text)
        self.assertIn('allow-same-origin',player_html_text)

    def test_motion_preview_player_has_pose_asset_and_controls(self):
        preview_html_text=character_animation_app.create_motion_preview_player('standing-v10','anny','down_left',10,20,4,2,1,'http://127.0.0.1:8770')
        self.assertIn('character-animation/asset/standing-v10/anny/down_left/10',preview_html_text)
        self.assertIn('character-animation/asset/standing-v10/anny/down_left/12',preview_html_text)
        self.assertIn('미리보기 불러오기',preview_html_text)
        self.assertIn('id=&quot;play&quot; disabled',preview_html_text)
        self.assertIn('입력 포즈 프레임',preview_html_text)
        self.assertIn('allow-same-origin',preview_html_text)
        self.assertNotIn('<select id="fps">',preview_html_text)
        self.assertIn('loading&lt;4',preview_html_text)
        self.assertIn('load&#x27;).onclick',preview_html_text)
        self.assertNotIn('};preloadNext()</script>',preview_html_text)

    def test_motion_preview_uses_generation_sampling(self):
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(10,20,4,2,1),[10,12,14,16,18,20])
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(10,20,4,4,2),[10,12,14,16,18,20])

    def test_restored_frame_range_is_preserved_or_clamped_for_motion(self):
        self.assertEqual(character_animation_app.clamp_selected_frame_range(10,20,120),(10,20))
        self.assertEqual(character_animation_app.clamp_selected_frame_range(10,120,60),(10,60))
        self.assertEqual(character_animation_app.clamp_selected_frame_range(None,None,60),(1,60))

    def test_direction_auxiliary_prompts_round_trip(self):
        request=character_animation_app.build_animation_request('standing-v10','character-default','anny',['down_left'],1,2,512,4,4,1,'','left detail','','rear detail','')
        self.assertEqual(request['direction_auxiliary_prompts']['down_left'],'left detail')
        restored=character_animation_app.restore_animation_inputs({'request':request})
        self.assertEqual(restored[11:15],('left detail','','rear detail',''))
        from tools.review.domains.character_animation.character_animation_assets import compose_direction_prompts
        fixed={'base':'Preserve character.','auxiliary':'Face {direction}.','auxiliary_rear':'Back {direction}.'}
        prompts=compose_direction_prompts(fixed,request['direction_auxiliary_prompts'])
        self.assertIn('left detail',prompts['down_left']['text'])
        self.assertNotIn('left detail',prompts['down_right']['text'])
        self.assertEqual(compose_direction_prompts(fixed),compose_direction_prompts(fixed,{direction:'' for direction in request['direction_auxiliary_prompts']}))

    def test_restore_animation_inputs_uses_historical_request(self):
        restored_input_values=character_animation_app.restore_animation_inputs({'request':{'motion':'standing-v7','character':'anny-v1','source':'anny','directions':['down_left'],'start_frame':10,'end_frame':20,'resolution':768,'steps':30,'target_fps':2,'speed':1.5,'tag':'돌온재 걷기'}})
        self.assertEqual(restored_input_values[:10],('standing-v7','anny-v1','anny',['down_left'],10,20,768,30,2,1.5))
        self.assertEqual(restored_input_values[10],'돌온재 걷기')

    def test_animation_request_includes_trimmed_history_tag(self):
        request_payload_value=character_animation_app.build_animation_request('standing-v7','anny-v1','anny',['down_left'],10,20,512,4,4,1,' 돌온재 걷기 ')
        self.assertEqual(request_payload_value['tag'],'돌온재 걷기')
