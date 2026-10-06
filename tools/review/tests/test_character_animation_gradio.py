"""캐릭터 애니메이션 Gradio 클라이언트 계약을 검증한다."""
import unittest
from unittest.mock import patch

from tools.review.ui.gradio import character_animation_app


class CharacterAnimationGradioTests(unittest.TestCase):
    def test_reference_gallery_supports_registered_direction_counts(self):
        from pathlib import Path
        for current_character_identifier,current_expected_count in (('character-default',4),('character-female-a',4),('character-default-light-armor-v1',1)):
            current_preview_records=character_animation_app.build_character_baseline_preview(current_character_identifier,'http://127.0.0.1:8770')
            self.assertEqual(len(current_preview_records),current_expected_count)
            self.assertTrue(all(Path(current_image_path).is_file() for current_image_path,_ in current_preview_records))
        with patch('tools.review.domains.character_animation.character_animation_assets.hash_asset_file',return_value='invalid'):
            with self.assertRaisesRegex(ValueError,'무결성'):
                character_animation_app.build_character_baseline_preview('character-default','http://127.0.0.1:8770')

    def test_selected_motion_prompt_display_matches_generation(self):
        from tools.review.domains.character_animation.character_animation_assets import build_animation_catalog, prepare_animation_request
        catalog_record_value=build_animation_catalog()
        for selected_motion_name in ('walking-v13',):
            request_record_value=prepare_animation_request({'motion':selected_motion_name,'character':'character-default','source':'anny','directions':['down_left'],'start_frame':1,'end_frame':1,'direction_auxiliary_prompts':{'down_left':'Keep pose.'}})
            self.assertEqual(character_animation_app.select_motion_prompt_values(catalog_record_value,selected_motion_name),request_record_value['prompts'])
            summary_text_value=character_animation_app.describe_motion_prompt_words(catalog_record_value,selected_motion_name,'Keep pose.','','','')
            self.assertIn(f"전방 좌측: 추가 보조 2단어 · 최종 {request_record_value['direction_prompts']['down_left']['words']}단어",summary_text_value)

    def test_generate_uses_shared_gateway(self):
        with patch.object(character_animation_app,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(character_animation_app.execute_animation_gateway('generate',{'motion':'standing-v7'}),{'id':'sample'})
            gateway_call_value.assert_called_once_with('character-animation','generate',{'motion':'standing-v7'})

    def test_result_player_uses_browser_only_standard_controls(self):
        import json
        from tools.review.common.gradio_frame_player import build_browser_frame_player
        import gradio as gr
        current_result_payload=json.loads(character_animation_app.create_animation_player('sample',{'result':{'frames':{'down_left':['down_left/frame-0001/result.png']},'fps':8}},'http://127.0.0.1:8770'))
        self.assertEqual(current_result_payload['frames']['down_left'],['down_left/frame-0001/result.png'])
        with gr.Blocks() as current_test_interface:
            build_browser_frame_player()
        current_configuration_record=current_test_interface.get_config_file()
        current_player_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'generationFramePlayerCommand' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_player_events),7)
        self.assertTrue(all(not current_event_record['backend_fn'] for current_event_record in current_player_events))
        self.assertNotIn('<iframe',str(current_configuration_record))

    def test_motion_preview_payload_preserves_sampling_and_explicit_loading(self):
        import json
        current_preview_payload=json.loads(character_animation_app.create_motion_preview_player('walking-v13','anny','down_left',10,20,4,8,2,'http://127.0.0.1:8770'))
        self.assertEqual(current_preview_payload['sourceFrames']['down_left'],[10,12,14,16,18,20])
        self.assertEqual(len(current_preview_payload['frames']['down_left']),6)
        self.assertTrue(current_preview_payload['frames']['down_left'][0].endswith('/anny/down_left/10'))
        self.assertTrue(current_preview_payload['deferLoading'])
        self.assertTrue(current_preview_payload['directUrls'])

    def test_two_players_have_independent_browser_commands(self):
        from tools.review.common.gradio_frame_player import build_browser_frame_player
        import gradio as gr
        with gr.Blocks() as current_test_interface:
            build_browser_frame_player()
            build_browser_frame_player('motion-preview-player',defer_image_loading=True)
        current_configuration_record=current_test_interface.get_config_file()
        current_player_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'generationFramePlayerCommands' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_player_events),14)
        self.assertEqual(sum('motion-preview-player' in current_event_record['js'] for current_event_record in current_player_events),7)
        self.assertTrue(all(not current_event_record['backend_fn'] for current_event_record in current_player_events))

    def test_motion_preview_uses_generation_sampling(self):
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(10,20,4,8,2),[10,12,14,16,18,20])
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(10,20,4,8,2),[10,12,14,16,18,20])

    def test_restored_frame_range_is_preserved_or_clamped_for_motion(self):
        self.assertEqual(character_animation_app.clamp_selected_frame_range(10,20,120),(10,20))
        self.assertEqual(character_animation_app.clamp_selected_frame_range(10,120,60),(10,60))
        self.assertEqual(character_animation_app.clamp_selected_frame_range(None,None,60),(1,60))

    def test_direction_auxiliary_prompts_round_trip(self):
        request=character_animation_app.build_animation_request('walking-v13','character-default','anny',['down_left'],1,2,512,4,4,1,'','left detail','','rear detail','')
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
        self.assertEqual(restored_input_values[:10],('standing-v7','anny-v1','anny',['down_left'],10,20,768,30,8,2))
        self.assertEqual(restored_input_values[10],'돌온재 걷기')

    def test_animation_request_includes_trimmed_history_tag(self):
        request_payload_value=character_animation_app.build_animation_request('standing-v7','anny-v1','anny',['down_left'],10,20,512,4,4,1,' 돌온재 걷기 ')
        self.assertEqual(request_payload_value['tag'],'돌온재 걷기')

    def test_fixed_eight_fps_and_default_double_speed(self):
        from tools.review.domains.character_animation.character_animation_assets import select_target_fps_frames
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(1,120,4,8,2),select_target_fps_frames(120,4,8,2))
        self.assertEqual(character_animation_app.calculate_preview_frame_numbers(1,28,4,8,2),list(range(1,29,2)))
