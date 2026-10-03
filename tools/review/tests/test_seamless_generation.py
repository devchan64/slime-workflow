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
