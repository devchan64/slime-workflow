"""타일 공통·고정 프롬프트 및 CLI 계약 검증."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.tile.tile_generation import load_tile_configuration, prepare_tile_request, TileGenerationManager
from tools.review.common import management_gateway

class TileGenerationTests(unittest.TestCase):
    def make_tile_request(self):return {'action':'generate','user_prompt':'Red brick house.','steps':4,'seed':1,'width':512,'height':512}
    def test_common_prompt_configuration(self):
        configuration_record_value=load_tile_configuration()
        self.assertEqual(set(configuration_record_value),{'schema_version','base_prompt','style_prompt'})
        self.assertEqual(configuration_record_value['base_prompt'],'게임용 텍스처. 정사각형. 얇은 검은 테두리.')
        output_request_value=prepare_tile_request(self.make_tile_request())
        self.assertNotIn('tile_type',output_request_value)
        self.assertEqual(output_request_value['prompt'],configuration_record_value['style_prompt']+' '+configuration_record_value['base_prompt']+' 표면 재질: Red brick house.')

    def test_gui_request_and_legacy_history_restore_without_type(self):
        from tools.review.ui.gradio.tile_map_app import build_tile_request, restore_tile_inputs
        gui_request_value=build_tile_request('Red brick house.','',512,4,1,True,True)
        self.assertNotIn('tile_type',gui_request_value)
        self.assertEqual(prepare_tile_request(gui_request_value),prepare_tile_request(self.make_tile_request()))
        current_history_record={'request':gui_request_value}
        legacy_history_record={'request':gui_request_value|{'tile_type':'wall'}}
        self.assertEqual(restore_tile_inputs(current_history_record,''),restore_tile_inputs(legacy_history_record,''))

    def test_gui_build_has_no_type_selector(self):
        from tools.review.ui.gradio.tile_map_app import build_tile_interface
        with patch('tools.review.ui.gradio.tile_map_app.execute_tile_gateway',return_value=load_tile_configuration()):
            interface_record_value=build_tile_interface('http://127.0.0.1:8770')
        self.assertNotIn('타일 종류',[component_record_value.get('props',{}).get('label') for component_record_value in interface_record_value.config['components']])
        interface_record_value.close()

    def test_default_seed_is_10107_and_explicit_seed_is_preserved(self):
        request=self.make_tile_request()
        request.pop('seed')
        self.assertEqual(prepare_tile_request(request)['seed'],10107)
        self.assertEqual(prepare_tile_request(request|{'seed':0})['seed'],0)

    def test_random_seed_value_stays_within_gateway_range(self):
        from tools.review.ui.gradio.tile_map_app import generate_random_seed_value
        for generation_attempt_index in range(8):
            random_seed_value=generate_random_seed_value()
            self.assertIsInstance(random_seed_value,int)
            self.assertGreaterEqual(random_seed_value,0)
            self.assertLessEqual(random_seed_value,4294967295)

    def test_wall_tile_korean_example_is_inserted_without_overwriting_or_duplication(self):
        from tools.review.ui.gradio.tile_map_app import WALL_TILE_KOREAN_EXAMPLE, append_wall_tile_example
        self.assertEqual(append_wall_tile_example(''),WALL_TILE_KOREAN_EXAMPLE)
        self.assertEqual(append_wall_tile_example('낮은 성벽'), '낮은 성벽\n'+WALL_TILE_KOREAN_EXAMPLE)
        self.assertEqual(append_wall_tile_example(WALL_TILE_KOREAN_EXAMPLE),WALL_TILE_KOREAN_EXAMPLE)

    def test_small_window_wall_example_is_inserted_without_overwriting_or_duplication(self):
        from tools.review.ui.gradio.tile_map_app import SMALL_WINDOW_WALL_KOREAN_EXAMPLE, append_small_window_wall_example
        self.assertEqual(append_small_window_wall_example(''),SMALL_WINDOW_WALL_KOREAN_EXAMPLE)
        self.assertEqual(append_small_window_wall_example('낮은 성벽'), '낮은 성벽\n'+SMALL_WINDOW_WALL_KOREAN_EXAMPLE)
        self.assertEqual(append_small_window_wall_example(SMALL_WINDOW_WALL_KOREAN_EXAMPLE),SMALL_WINDOW_WALL_KOREAN_EXAMPLE)

    def test_closed_gate_wall_example_is_inserted_without_overwriting_or_duplication(self):
        from tools.review.ui.gradio.tile_map_app import CLOSED_GATE_WALL_KOREAN_EXAMPLE, append_closed_gate_wall_example
        self.assertEqual(append_closed_gate_wall_example(''),CLOSED_GATE_WALL_KOREAN_EXAMPLE)
        self.assertEqual(append_closed_gate_wall_example('낮은 성벽'), '낮은 성벽\n'+CLOSED_GATE_WALL_KOREAN_EXAMPLE)
        self.assertEqual(append_closed_gate_wall_example(CLOSED_GATE_WALL_KOREAN_EXAMPLE),CLOSED_GATE_WALL_KOREAN_EXAMPLE)

    def test_ground_tile_korean_example_is_inserted_without_overwriting_or_duplication(self):
        from tools.review.ui.gradio.tile_map_app import GROUND_TILE_KOREAN_EXAMPLE, append_ground_tile_example
        self.assertEqual(append_ground_tile_example(''),GROUND_TILE_KOREAN_EXAMPLE)
        self.assertEqual(append_ground_tile_example('광장 바닥'), '광장 바닥\n'+GROUND_TILE_KOREAN_EXAMPLE)
        self.assertEqual(append_ground_tile_example(GROUND_TILE_KOREAN_EXAMPLE),GROUND_TILE_KOREAN_EXAMPLE)

    def test_user_prompt_clear_action_returns_empty_value(self):
        from tools.review.ui.gradio.tile_map_app import clear_user_prompt_value
        self.assertEqual(clear_user_prompt_value(),'')

    def test_prompt_order_follows_style_base_surface(self):
        from itertools import product
        for base_enabled,style_enabled in product((False,True),repeat=2):
            request=self.make_tile_request()|{'use_base_prompt':base_enabled,'use_style_prompt':style_enabled}
            record=prepare_tile_request(request)
            expected=[record['style_prompt'] if style_enabled else '',record['base_prompt'] if base_enabled else '','표면 재질: '+record['user_prompt']]
            self.assertEqual(record['prompt'],' '.join(section_text_value for section_text_value in expected if section_text_value))

    def test_surface_material_sentence_and_prompt_metadata(self):
        import hashlib
        prepared_request_value=prepare_tile_request(self.make_tile_request()|{'user_prompt':'잔디와 진흙'})
        self.assertIn('표면 재질: 잔디와 진흙.',prepared_request_value['prompt'])
        self.assertFalse(prepared_request_value['prompt'].startswith('{'))
        self.assertEqual(prepared_request_value['prompt_sha256'],hashlib.sha256(prepared_request_value['prompt'].encode()).hexdigest())
        self.assertEqual(prepared_request_value['prompt_words'],len(prepared_request_value['prompt'].split()))

    def test_reference_style_feature_is_removed(self):
        prepared_request_value=prepare_tile_request(self.make_tile_request())
        self.assertNotIn('reference_style_prompt',prepared_request_value)
        for removed_toggle_value in (True,False):
            with self.assertRaises(ValueError):
                prepare_tile_request(self.make_tile_request()|{'use_reference_style_prompt':removed_toggle_value})

    def test_reference_images_disable_fixed_prompts(self):
        import base64,io
        from PIL import Image
        from tools.review.ui.gradio.tile_map_app import build_tile_request, update_reference_prompt_controls, format_applied_prompt_words
        reference_image_value=Image.new('RGB',(512,512),'white')
        reference_image_buffer=io.BytesIO()
        reference_image_value.save(reference_image_buffer,format='PNG')
        reference_image_payload=base64.b64encode(reference_image_buffer.getvalue()).decode()
        reference_request_value=self.make_tile_request()|{'images':[reference_image_payload]}
        prepared_request_value=prepare_tile_request(reference_request_value)
        self.assertEqual(prepared_request_value['prompt'],'Red brick house.')
        self.assertEqual(prepared_request_value['prompt_words'],3)
        self.assertIn('총 3단어',format_applied_prompt_words(load_tile_configuration(),'Red brick house.',True,True,True,reference_image_value))
        self.assertFalse(prepared_request_value['use_base_prompt'])
        self.assertFalse(prepared_request_value['use_style_prompt'])
        for fixed_prompt_key in ('use_base_prompt','use_style_prompt'):
            with self.assertRaisesRegex(ValueError,'참조 이미지'):
                prepare_tile_request(reference_request_value|{fixed_prompt_key:True})
        gui_request_value=build_tile_request('Red brick house.','',512,4,1,True,True,True,reference_image_value)
        self.assertEqual(prepare_tile_request(gui_request_value)['prompt'],prepared_request_value['prompt'])
        self.assertTrue(all(not update_record['interactive'] and update_record['value'] is False for update_record in update_reference_prompt_controls(True,reference_image_value)))
        self.assertTrue(all(update_record['interactive'] for update_record in update_reference_prompt_controls(True,None)))
        self.assertIn('기본 0',format_applied_prompt_words(load_tile_configuration(),'Red brick house.',True,True,True,reference_image_value))

    def test_reference_switch_excludes_retained_images(self):
        from PIL import Image
        from tools.review.ui.gradio.tile_map_app import build_tile_request, format_applied_prompt_words, update_reference_prompt_controls, update_reference_upload_visibility
        reference_image_value=Image.new('RGB',(512,512),'white')
        disabled_request_value=build_tile_request('벽','',512,4,1,True,True,False,reference_image_value)
        self.assertEqual(disabled_request_value['images'],[])
        self.assertTrue(disabled_request_value['use_base_prompt'])
        self.assertTrue(disabled_request_value['use_style_prompt'])
        self.assertEqual(format_applied_prompt_words(load_tile_configuration(),'벽',True,True,False,reference_image_value),format_applied_prompt_words(load_tile_configuration(),'벽',True,True))
        self.assertTrue(all(control_update_value['interactive'] for control_update_value in update_reference_prompt_controls(False,reference_image_value)))
        self.assertFalse(update_reference_upload_visibility(False)['visible'])
        self.assertTrue(update_reference_upload_visibility(True)['visible'])

    def test_fixed_prompt_override_and_invalid_input_rejected(self):
        for invalid_request_value in ({'base_prompt':'override'},{'style_prompt':''},{'prompt':'override'},{'tile_type':'other'},{'width':768},{'seed':True},{'tag':False},{'tag':'새\n태그'},{'tag':'a'*81},{'user_prompt':'word '*100}):
            with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|invalid_request_value)
    def test_generation_tag_is_saved_for_history_summary(self):
        prepared_request_value=prepare_tile_request(self.make_tile_request()|{'tag':'이슬온 시장 외벽 후보'})
        self.assertEqual(prepared_request_value['tag'],'이슬온 시장 외벽 후보')
    def test_tile_storage_uses_separate_history(self):
        image_manager_value=TileGenerationManager()
        self.assertEqual(image_manager_value.job_storage_root.name,'tile-map')
        self.assertEqual(image_manager_value.history_storage_path().name,'tile-map')
    def test_existing_job_directories_appear_in_history(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path=Path(temporary_directory_name)
            job_root_path=temporary_root_path/'jobs'/'2026-09-26_12-00-00-abcdef12'
            job_root_path.mkdir(parents=True)
            (job_root_path/'request.json').write_text(json.dumps(self.make_tile_request()))
            (job_root_path/'status.json').write_text(json.dumps({'status':'completed'}))
            image_manager_value=TileGenerationManager()
            with patch.object(image_manager_value,'job_storage_root',temporary_root_path/'jobs'),patch.object(image_manager_value,'history_storage_path',return_value=temporary_root_path/'history'):
                history_record_values=image_manager_value.list_generation_history()
            self.assertEqual([record_value['id'] for record_value in history_record_values],['2026-09-26_12-00-00-abcdef12'])
            self.assertEqual(history_record_values[0]['status']['status'],'completed')
            with patch.object(image_manager_value,'job_storage_root',temporary_root_path/'jobs'),patch.object(image_manager_value,'history_storage_path',return_value=temporary_root_path/'history'):
                image_manager_value.reset_generation_history()
                self.assertEqual(image_manager_value.list_generation_history(),[])
                self.assertFalse(job_root_path.exists())
                self.assertEqual(image_manager_value.current_job_identifier,None)

    def test_individual_history_delete_hides_tile_job_and_preserves_result(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path=Path(temporary_directory_name)
            generation_job_identifier='2026-09-26_12-00-00-abcdef12'
            job_root_path=temporary_root_path/'jobs'/generation_job_identifier
            job_root_path.mkdir(parents=True)
            (job_root_path/'request.json').write_text(json.dumps(self.make_tile_request()))
            (job_root_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (job_root_path/'result.png').write_bytes(b'image')
            image_manager_value=TileGenerationManager()
            with patch.object(image_manager_value,'job_storage_root',temporary_root_path/'jobs'),patch.object(image_manager_value,'history_storage_path',return_value=temporary_root_path/'history'):
                self.assertEqual(image_manager_value.delete_generation_history(generation_job_identifier),{'deleted':generation_job_identifier,'files_preserved':True})
                self.assertEqual(image_manager_value.list_generation_history(),[])
                self.assertTrue((job_root_path/'result.png').exists())
            restarted_manager_value=TileGenerationManager()
            with patch.object(restarted_manager_value,'job_storage_root',temporary_root_path/'jobs'),patch.object(restarted_manager_value,'history_storage_path',return_value=temporary_root_path/'new-history'):
                self.assertEqual(restarted_manager_value.list_generation_history(),[])

    def test_three_references_are_validated(self):
        import base64,io
        from PIL import Image
        image_output_buffer=io.BytesIO()
        Image.new('RGB',(512,512),'white').save(image_output_buffer,format='PNG')
        image_payload_value=base64.b64encode(image_output_buffer.getvalue()).decode()
        result_request_value=prepare_tile_request(self.make_tile_request()|{'images':[image_payload_value]*3})
        self.assertEqual(len(result_request_value['images']),3)
        for invalid_image_values in ([image_payload_value]*4,['invalid']):
            with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'images':invalid_image_values})

    def test_prompt_toggle_combinations(self):
        for use_base_prompt in (True,False):
            for use_style_prompt in (True,False):
                result_request_value=prepare_tile_request(self.make_tile_request()|{'use_base_prompt':use_base_prompt,'use_style_prompt':use_style_prompt})
                expected_prompt_parts=([result_request_value['style_prompt']] if use_style_prompt else [])+([result_request_value['base_prompt']] if use_base_prompt else [])+['표면 재질: Red brick house.']
                self.assertEqual(result_request_value['prompt'],' '.join(expected_prompt_parts))
                self.assertEqual(result_request_value['use_base_prompt'],use_base_prompt)
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':'false'})
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':False,'use_style_prompt':False,'user_prompt':''})

    def test_cli_passes_user_prompt_and_history_tag(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'test'}) as execute_command_mock:
            management_gateway.execute_gateway_arguments('tile-map',['generate','--prompt','Oak wood.','--tag','돌온재 외벽 후보','--detach'])
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertNotIn('tile_type',current_payload_value)
            self.assertEqual(current_payload_value['user_prompt'],'Oak wood.')
            self.assertEqual(current_payload_value['tag'],'돌온재 외벽 후보')
            self.assertNotIn('prompt',current_payload_value)
            self.assertNotIn('use_base_prompt',current_payload_value)
            self.assertNotIn('use_style_prompt',current_payload_value)

    def test_cli_queue_adds_tile_request_without_waiting(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'queued'}) as execute_command_mock:
            self.assertEqual(management_gateway.execute_gateway_arguments('tile-map',['queue','--prompt','Packed riverbank dirt.','--tag','갈대나루 강변 흙길 후보']),0)
            self.assertEqual(execute_command_mock.call_args.args[1],'queue')
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['action'],'generate')
            self.assertNotIn('tile_type',current_payload_value)
            self.assertEqual(current_payload_value['tag'],'갈대나루 강변 흙길 후보')

    def test_removed_reference_style_cli_flag_rejected(self):
        with self.assertRaises(SystemExit):
            management_gateway.execute_gateway_arguments('tile-map',['queue','--prompt','벽','--use-reference-style-prompt'])
