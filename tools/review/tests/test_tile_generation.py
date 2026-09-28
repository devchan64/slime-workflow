"""타일 종류·고정 프롬프트 및 CLI 계약 검증."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.tile.tile_generation import load_tile_configuration, prepare_tile_request, TileGenerationManager
from tools.review.common import management_gateway

class TileGenerationTests(unittest.TestCase):
    def make_tile_request(self):return {'action':'generate','tile_type':'wall','user_prompt':'Red brick house.','steps':4,'seed':1,'width':512,'height':512}
    def test_ground_tile_uses_floor_tile_label(self):
        self.assertEqual(load_tile_configuration()['types']['ground']['label'],'바닥 타일')

    def test_ground_prompt_defines_square_area(self):
        ground_prompt_text=load_tile_configuration()['types']['ground']['base_prompt']
        self.assertIn('Top-down view of a flat square area',ground_prompt_text)
        self.assertIn('aligned with the image borders, surrounded by black background',ground_prompt_text)
        self.assertIn('All details stay inside',ground_prompt_text)
        self.assertNotRegex(ground_prompt_text,r'\b(?:plate|frame|soil|grass)\b')

    def test_all_kinds_keep_base_and_style(self):
        for tile_kind_name in ('rooftop','wall','ground'):
            output_request_value=prepare_tile_request(self.make_tile_request()|{'tile_type':tile_kind_name})
            self.assertIn(output_request_value['base_prompt'],output_request_value['prompt'])
            self.assertIn(output_request_value['style_prompt'],output_request_value['prompt'])
            self.assertNotRegex(output_request_value['base_prompt'],r'\btile\b')
            self.assertIn('No text or symbols.',output_request_value['base_prompt'])
            self.assertNotIn('no decorative border or frame',output_request_value['base_prompt'])
            self.assertNotIn('visible outer boundary lines',output_request_value['base_prompt'])
            self.assertIn('Red brick house.',output_request_value['prompt'])
            self.assertEqual(output_request_value['prompt_words'],len(output_request_value['prompt'].split()))
            self.assertLess(output_request_value['prompt_words'],100)

    def test_rooftop_prompt_keeps_layout_user_defined(self):
        rooftop_prompt_text=load_tile_configuration()['types']['rooftop']['base_prompt']
        self.assertIn('Orthographic top view',rooftop_prompt_text)
        self.assertIn('flat square panel on a black background',rooftop_prompt_text)
        self.assertNotIn('plate',rooftop_prompt_text)
        self.assertNotIn('frame',rooftop_prompt_text)
        self.assertIn('straight edges and equal side lengths',rooftop_prompt_text)
        self.assertNotRegex(rooftop_prompt_text,r'\d|\b(?:rows?|columns?|five|three)\b')
        self.assertLessEqual(len(rooftop_prompt_text.split()),32)

    def test_base_prompts_do_not_prescribe_material(self):
        for tile_type_record in load_tile_configuration()['types'].values():
            self.assertNotRegex(tile_type_record['base_prompt'],r'\b(?:wooden|wood|marble|stone|metal|material)\b')

    def test_wall_prompt_uses_columns_and_top_beam_without_prescribing_material(self):
        wall_prompt_text=load_tile_configuration()['types']['wall']['base_prompt']
        self.assertIn('half-visible columns at both edges',wall_prompt_text)
        self.assertIn('a top beam',wall_prompt_text)
        self.assertNotRegex(wall_prompt_text,r'\b(?:wooden|wood|marble|stone|metal|material)\b')
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

    def test_prompt_order_follows_base_user_style(self):
        from itertools import product
        for base_enabled,style_enabled,reference_enabled in product((False,True),repeat=3):
            request=self.make_tile_request()|{'use_base_prompt':base_enabled,'use_style_prompt':style_enabled,'use_reference_style_prompt':reference_enabled}
            record=prepare_tile_request(request)
            expected=[record['reference_style_prompt'] if reference_enabled else '',record['base_prompt'] if base_enabled else '',record['user_prompt'],record['style_prompt'] if style_enabled else '']
            self.assertEqual(record['prompt'],'\n\n'.join(part for part in expected if part))
            self.assertTrue(record['prompt'].endswith(record['style_prompt'] if style_enabled else record['user_prompt']))

    def test_reference_style_toggle_defaults_off(self):
        default_record=prepare_tile_request(self.make_tile_request())
        self.assertFalse(default_record['use_reference_style_prompt'])
        self.assertNotIn(default_record['reference_style_prompt'],default_record['prompt'])
        enabled_record=prepare_tile_request(self.make_tile_request()|{'use_reference_style_prompt':True})
        self.assertTrue(enabled_record['prompt'].startswith(enabled_record['reference_style_prompt']))
        self.assertEqual(enabled_record['prompt_words'],len(enabled_record['prompt'].split()))
        with self.assertRaises(ValueError):
            prepare_tile_request(self.make_tile_request()|{'use_reference_style_prompt':'on'})

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
                expected_prompt_parts=([result_request_value['base_prompt']] if use_base_prompt else [])+['Red brick house.']+([result_request_value['style_prompt']] if use_style_prompt else [])
                self.assertEqual(result_request_value['prompt'],'\n\n'.join(expected_prompt_parts))
                self.assertEqual(result_request_value['use_base_prompt'],use_base_prompt)
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':'false'})
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':False,'use_style_prompt':False,'user_prompt':''})

    def test_cli_passes_user_prompt_and_history_tag(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'test'}) as execute_command_mock:
            management_gateway.execute_gateway_arguments('tile-map',['generate','--tile-type','wall','--prompt','Oak wood.','--tag','돌온재 외벽 후보','--detach'])
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['tile_type'],'wall')
            self.assertEqual(current_payload_value['user_prompt'],'Oak wood.')
            self.assertEqual(current_payload_value['tag'],'돌온재 외벽 후보')
            self.assertNotIn('prompt',current_payload_value)

    def test_cli_queue_adds_tile_request_without_waiting(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'queued'}) as execute_command_mock:
            self.assertEqual(management_gateway.execute_gateway_arguments('tile-map',['queue','--tile-type','ground','--prompt','Packed riverbank dirt.','--tag','갈대나루 강변 흙길 후보']),0)
            self.assertEqual(execute_command_mock.call_args.args[1],'queue')
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['action'],'generate')
            self.assertEqual(current_payload_value['tile_type'],'ground')
            self.assertEqual(current_payload_value['tag'],'갈대나루 강변 흙길 후보')
