"""타일 종류·고정 프롬프트 및 CLI 계약 검증."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.tile.tile_generation import prepare_tile_request, TileGenerationManager
from tools.review.common import management_gateway

class TileGenerationTests(unittest.TestCase):
    def make_tile_request(self):return {'action':'generate','tile_type':'wall','user_prompt':'Red brick house.','steps':4,'seed':1,'width':512,'height':512}
    def test_all_kinds_keep_base_and_style(self):
        for tile_kind_name in ('rooftop','wall','ground'):
            output_request_value=prepare_tile_request(self.make_tile_request()|{'tile_type':tile_kind_name})
            self.assertIn(output_request_value['base_prompt'],output_request_value['prompt'])
            self.assertIn(output_request_value['style_prompt'],output_request_value['prompt'])
            self.assertIn('Red brick house.',output_request_value['prompt'])
            self.assertEqual(output_request_value['prompt_words'],len(output_request_value['prompt'].split()))
            self.assertLess(output_request_value['prompt_words'],100)
    def test_default_seed_is_10107_and_explicit_seed_is_preserved(self):
        request=self.make_tile_request()
        request.pop('seed')
        self.assertEqual(prepare_tile_request(request)['seed'],10107)
        self.assertEqual(prepare_tile_request(request|{'seed':0})['seed'],0)

    def test_user_prompt_is_last_for_every_toggle_combination(self):
        from itertools import product
        for base_enabled,style_enabled,reference_enabled in product((False,True),repeat=3):
            request=self.make_tile_request()|{'use_base_prompt':base_enabled,'use_style_prompt':style_enabled,'use_reference_style_prompt':reference_enabled}
            record=prepare_tile_request(request)
            expected=[record['reference_style_prompt'] if reference_enabled else '',record['base_prompt'] if base_enabled else '',record['style_prompt'] if style_enabled else '',record['user_prompt']]
            self.assertEqual(record['prompt'],'\n\n'.join(part for part in expected if part))
            self.assertTrue(record['prompt'].endswith(record['user_prompt']))

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
        for invalid_request_value in ({'base_prompt':'override'},{'style_prompt':''},{'prompt':'override'},{'tile_type':'other'},{'width':768},{'seed':True},{'user_prompt':'word '*100}):
            with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|invalid_request_value)
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
                expected_prompt_parts=([result_request_value['base_prompt']] if use_base_prompt else [])+([result_request_value['style_prompt']] if use_style_prompt else [])+['Red brick house.']
                self.assertEqual(result_request_value['prompt'],'\n\n'.join(expected_prompt_parts))
                self.assertEqual(result_request_value['use_base_prompt'],use_base_prompt)
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':'false'})
        with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|{'use_base_prompt':False,'use_style_prompt':False,'user_prompt':''})

    def test_cli_passes_only_user_prompt(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'test'}) as execute_command_mock:
            management_gateway.execute_gateway_arguments('tile-map',['generate','--tile-type','wall','--prompt','Oak wood.','--detach'])
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['tile_type'],'wall')
            self.assertEqual(current_payload_value['user_prompt'],'Oak wood.')
            self.assertNotIn('prompt',current_payload_value)
