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
        self.assertIn('Ctrl+V / ⌘V',rendered_page_value)
        self.assertIn('data-reference-slot="1"',rendered_page_value)
        self.assertIn('data-select-reference="1"',rendered_page_value)
        self.assertIn('aria-pressed="false"',rendered_page_value)
        self.assertIn('<details><summary>기본 프롬프트 · 고정',rendered_page_value)
        self.assertIn('<details><summary>화풍 프롬프트 · 항상 적용',rendered_page_value)
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
                # 작업 종료로 폴더 시각이 바뀌어도 초기화한 기록을 복원하지 않는다.
                (job_root_path/'later-output.txt').write_text('완료')
                self.assertEqual(image_manager_value.list_generation_history(),[])
                self.assertTrue((job_root_path/'request.json').exists())
                self.assertTrue((job_root_path/'status.json').exists())

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

    def test_cli_passes_only_user_prompt(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'test'}) as execute_command_mock:
            management_gateway.execute_gateway_arguments('tile-map',['generate','--tile-type','wall','--prompt','Oak wood.','--detach'])
            current_payload_value=execute_command_mock.call_args.args[2]
            self.assertEqual(current_payload_value['tile_type'],'wall')
            self.assertEqual(current_payload_value['user_prompt'],'Oak wood.')
            self.assertNotIn('prompt',current_payload_value)
