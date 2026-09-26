"""타일 종류·고정 프롬프트 및 CLI 계약 검증."""
import unittest
from unittest.mock import patch
from tools.review.domains.tile.tile_generation import prepare_tile_request, TileGenerationManager
from tools.review.common import management_gateway

class TileGenerationTests(unittest.TestCase):
    def make_tile_request(self):return {'action':'generate','tile_type':'wall','user_prompt':'Red brick house.','steps':4,'seed':1,'width':512,'height':512}
    def test_all_kinds_keep_base_and_style(self):
        for tile_kind_name in ('rooftop','wall','door','ground'):
            output_request_value=prepare_tile_request(self.make_tile_request()|{'tile_type':tile_kind_name})
            self.assertIn(output_request_value['base_prompt'],output_request_value['prompt'])
            self.assertIn(output_request_value['style_prompt'],output_request_value['prompt'])
            self.assertIn('Red brick house.',output_request_value['prompt'])
            self.assertEqual(output_request_value['prompt_words'],len(output_request_value['prompt'].split()))
            self.assertLess(output_request_value['prompt_words'],100)
    def test_fixed_prompt_override_and_invalid_input_rejected(self):
        for invalid_request_value in ({'base_prompt':'override'},{'style_prompt':''},{'prompt':'override'},{'tile_type':'other'},{'width':768},{'seed':True},{'user_prompt':'word '*100}):
            with self.assertRaises(ValueError):prepare_tile_request(self.make_tile_request()|invalid_request_value)
    def test_tile_storage_and_shared_page(self):
        image_manager_value=TileGenerationManager()
        self.assertEqual(image_manager_value.job_storage_root.name,'tile-map')
        self.assertEqual(image_manager_value.history_storage_path().name,'tile-map')
        rendered_page_value=image_manager_value.render_generation_page().decode()
        self.assertIn('tile-map-generator/tile-ui.js',rendered_page_value)
        self.assertNotIn('id="use-style-prompt"',rendered_page_value)
    def test_cli_passes_only_user_prompt(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'test'}) as execute_command_mock:
            management_gateway.execute_gateway_arguments('tile-map',['generate','--tile-type','door','--prompt','Oak wood.','--detach'])
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['tile_type'],'door')
            self.assertEqual(current_payload_value['user_prompt'],'Oak wood.')
            self.assertNotIn('prompt',current_payload_value)
