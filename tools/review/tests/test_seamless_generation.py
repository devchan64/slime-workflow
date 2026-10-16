"""연결 타일 입력·중앙 픽셀 보존·CLI 계약 회귀 검사."""
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.domains.image.seamless_generation import validate_seamless_request, prepare_seamless_reference, finish_seamless_generation
from tools.review.common.management_gateway import execute_gateway_arguments


class SeamlessGenerationTests(unittest.TestCase):
    def test_saved_pattern_restore_validates_before_updates(self):
        from tools.review.ui.gradio import seamless_tile_app
        current_valid_request = {'seamless_tile': {'user_prompt': 'Grass field'}, 'seed': 42, 'tag': '검증'}
        current_history_record = {'id': 'isolated', 'request': current_valid_request}
        with patch.object(seamless_tile_app, 'execute_management_command', return_value={'records': [current_history_record]}) as current_gateway_mock:
            current_interface_blocks = seamless_tile_app.build_seamless_interface('http://localhost')
            current_restore_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values()
                if current_function.fn and current_function.fn.__name__ == 'restore_selected_inputs')
            self.assertEqual(tuple(current_restore_callback('isolated')[:4]), ('Grass field', '검증', 40, 42))
            for current_invalid_fields in ({'seed': -1}, {'seed': True}, {'seamless_tile': None}, {'seamless_tile': {'user_prompt': []}}, {'seamless_tile': {'user_prompt': ''}}):
                current_history_record['request'] = {**current_valid_request, **current_invalid_fields}
                current_restored_values = current_restore_callback('isolated')
                self.assertTrue(all(current_value == {'__type__': 'update'} for current_value in current_restored_values[:4]))
                self.assertIn('입력값을 불러오지 못했습니다', current_restored_values[-1])
            self.assertTrue(all(current_call.args[1] == 'history' for current_call in current_gateway_mock.call_args_list))

    def test_status_failure_preserves_result_and_disables_stage_actions(self):
        import gradio as gr
        from tools.review.ui.gradio import seamless_tile_app
        current_interface_blocks = seamless_tile_app.build_seamless_interface('http://localhost')
        current_refresh_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values()
            if current_function.fn and current_function.fn.__name__ == 'refresh_seamless_status')
        for current_error_type in (ValueError, RuntimeError, OSError):
            with patch.object(seamless_tile_app, 'read_existing_generation_status', side_effect=current_error_type('격리 조회 오류')):
                current_output_values = current_refresh_callback('saved-job', True)
            self.assertIn('상태 조회 실패', current_output_values[0])
            self.assertEqual(current_output_values[1:3], (gr.skip(), gr.skip()))
            self.assertFalse(current_output_values[3])
            self.assertFalse(current_output_values[4]['interactive'])
            self.assertEqual(current_output_values[5], gr.skip())
        with patch.object(seamless_tile_app, 'read_existing_generation_status', return_value={'status': 'paused', 'pipeline': {'stage': '검수'}, 'log': '복구 로그'}):
            current_output_values = current_refresh_callback('saved-job', True)
        self.assertEqual(current_output_values[1], '복구 로그')
        self.assertTrue(current_output_values[3])

    def test_boundary_measurement_detects_wrap_jump(self):
        from tools.review.domains.image.seamless_generation import measure_texture_boundaries
        current_tile_image = Image.new('RGB', (16, 16), 'black')
        self.assertEqual(measure_texture_boundaries(current_tile_image)['left_right_rgb_mae'], 0)
        current_tile_image.paste('white', (15, 0, 16, 16))
        self.assertEqual(measure_texture_boundaries(current_tile_image)['left_right_rgb_mae'], 255)
        self.assertEqual(measure_texture_boundaries(current_tile_image)['top_bottom_rgb_mae'], 0)

    def test_model_routing_preserves_history(self):
        from tools.review.domains.image.seamless_generation import SeamlessGenerationManager
        current_manager_value = SeamlessGenerationManager()
        self.assertTrue(current_manager_value.select_generation_runner().endswith('run_qwen_21_reference.py'))
        self.assertTrue(current_manager_value.select_generation_runner({'seamless_tile': {'schema_version': 1}}).endswith('run_qwen_2511_three_reference.py'))
        for rejected_step_count in (4, 30, True):
            with self.assertRaises(ValueError):
                validate_seamless_request({**self.create_tile_request(), 'steps': rejected_step_count})

    def create_tile_request(self, source_image_size=(256,256)):
        source_image_buffer = io.BytesIO()
        Image.new('RGB', source_image_size, 'green').save(source_image_buffer, format='PNG')
        return {'action':'generate','prompt':'잔디밭','images':[base64.b64encode(source_image_buffer.getvalue()).decode()], 'width':768,'height':768,'steps':40,'seed':10107}

    def test_reject_invalid_inputs(self):
        for request_record_value in (self.create_tile_request((256,128)), {**self.create_tile_request(),'images':['bad']}, {**self.create_tile_request(),'width':512}, {**self.create_tile_request(),'prompt':'grass '*100}):
            with self.assertRaises(ValueError):
                validate_seamless_request(request_record_value)

    def test_center_pixels_and_repeated_preview(self):
        current_request_record = validate_seamless_request(self.create_tile_request())
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root = Path(temporary_directory_name)
            (current_job_root/'reference-1.png').write_bytes(base64.b64decode(current_request_record['images'][0]))
            grid_reference_path = prepare_seamless_reference(current_job_root,current_request_record)
            with Image.open(grid_reference_path) as grid_input_image:
                self.assertEqual(grid_input_image.size,(768,768))
                self.assertEqual(grid_input_image.getpixel((767,767)),(0,128,0))
            generated_grid_image = Image.new('RGB',(768,768),'red')
            generated_grid_image.paste('blue',(256,256,512,512))
            generated_grid_image.putpixel((256,256),(1,2,3))
            generated_grid_image.save(current_job_root/'result.png')
            (current_job_root/'result.json').write_text(json.dumps({'size':[768,768],'quality_warnings':[]}))
            finish_seamless_generation(current_job_root,current_request_record)
            with Image.open(current_job_root/'result.png') as center_tile_image:
                self.assertEqual(center_tile_image.size,(256,256))
                self.assertEqual(center_tile_image.tobytes(),generated_grid_image.crop((256,256,512,512)).tobytes())
            with Image.open(current_job_root/'tiled-preview.png') as repeated_tile_image:
                self.assertEqual(repeated_tile_image.getpixel((512,512)),(1,2,3))
            self.assertEqual(json.loads((current_job_root/'result.json').read_text())['size'],[256,256])

    def test_cli_uses_same_request_contract(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            reference_image_path = Path(temporary_directory_name)/'tile.png'
            reference_image_path.write_bytes(base64.b64decode(self.create_tile_request()['images'][0]))
            with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'test'}) as gateway_call_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments('seamless-tile',['generate','--prompt','잔디밭','--reference',str(reference_image_path),'--detach'])
            current_request_record = gateway_call_mock.call_args.args[2]
            self.assertEqual(current_request_record['width'],768)
            self.assertIn('seamless_tile',validate_seamless_request(current_request_record))
