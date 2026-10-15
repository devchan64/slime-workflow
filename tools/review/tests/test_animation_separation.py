"""분리 서비스의 샘플 검수·원본 저장·중단 재개 계약을 검증한다."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import contextlib
from PIL import Image
from tools.review.domains.image import animation_separation as separation_service_module
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
from generators.image.run_animation_separation import render_separation_outputs
from tools.review.common.management_gateway import execute_gateway_arguments


class AnimationSeparationTest(unittest.TestCase):
    def test_native_alpha_preserved_exactly(self):
        from generators.image.separation_alpha import preserve_generated_alpha
        current_test_image = Image.new('RGBA', (4, 1))
        current_test_image.putdata([(255,255,255,255),(255,255,255,0),(30,60,90,127),(0,0,0,245)])
        current_output_image = preserve_generated_alpha(current_test_image)
        self.assertEqual(current_output_image.tobytes(), current_test_image.tobytes())
        with self.assertRaisesRegex(ValueError, 'RGBA'):
            preserve_generated_alpha(current_test_image.convert('RGB'))

    def test_retired_source_routes_explain_upload_without_reading_assets(self):
        from types import SimpleNamespace
        for current_route_suffix in ('/catalog', '/source-preview?source_id=workflow:character-default&frame=1'):
            for current_host_value, current_expected_status in (('127.0.0.1:8771', 410), ('invalid.example', 400)):
                with self.subTest(route=current_route_suffix, host=current_host_value):
                    current_response_codes = []
                    current_handler_value = SimpleNamespace(path='/animation-separation'+current_route_suffix, command='GET', headers={'Host':current_host_value}, server=SimpleNamespace(server_port=8771), wfile=io.BytesIO(), send_response=current_response_codes.append, send_header=lambda *current_header_values:None, end_headers=lambda:None)
                    with patch.object(Path, 'read_bytes', side_effect=AssertionError('폐기 경로에서 파일 읽기 금지')), patch.object(Path, 'read_text', side_effect=AssertionError('폐기 경로에서 설정 읽기 금지')):
                        self.assertTrue(self.current_service_instance.handle_image_request(current_handler_value))
                    self.assertEqual(current_response_codes, [current_expected_status])
                    current_response_record = json.loads(current_handler_value.wfile.getvalue())
                    if current_expected_status == 410:
                        self.assertEqual(current_response_record['code'], 'source_selection_retired')
                        self.assertIn('참조 PNG 1장', current_response_record['error'])

    def setUp(self):
        self.current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_root_path = Path(self.current_temp_directory.name)
        self.current_source_path = self.current_root_path / 'sheet.png'
        Image.new('RGBA', (32, 16), (20, 40, 60, 200)).save(self.current_source_path)
        self.current_service_instance = separation_service_module.AnimationSeparationManager()
        self.current_service_instance.job_storage_root = self.current_root_path
        self.current_request_record = {'action': 'generate', 'images': [base64.b64encode(self.current_source_path.read_bytes()).decode()], 'width': 512, 'height': 512, 'steps': 40, 'seed': 1, 'prompt': 'Create opaque fitted base clothing.', 'outfit_prompt': 'Remove person and keep garments.'}

    def test_gateway_catalog_preserves_retirement_response(self):
        from tools.review.tests.test_management_gateway import GatewayContractTest
        from tools.review.common.management_gateway import ManagementCommandGateway
        current_handler_value = GatewayContractTest().create_request_handler('/management/command', {'service':'animation-separation', 'command':'catalog', 'payload':{}})
        current_gateway_value = ManagementCommandGateway({'animation-separation':self.current_service_instance.handle_image_request})
        self.assertTrue(current_gateway_value.handle(current_handler_value))
        self.assertEqual(current_handler_value.responses, [410])
        self.assertEqual(json.loads(current_handler_value.wfile.getvalue())['code'], 'source_selection_retired')

    def prepare_saved_sample(self):
        current_validated_record = self.current_service_instance.validate_generation_request(self.current_request_record)
        current_sample_directory = self.current_root_path / '2026-10-04_00-00-00-12345678'
        current_sample_directory.mkdir()
        saved_input_record = save_three_reference_inputs(current_sample_directory, current_validated_record)
        current_saved_record = {**{current_key_name: current_value_record for current_key_name, current_value_record in current_validated_record.items() if current_key_name != 'images'}, **saved_input_record}
        (current_sample_directory / 'request.json').write_text(json.dumps(current_saved_record))
        return current_sample_directory, current_saved_record

    @staticmethod
    def generate_test_frame(current_frame_directory, current_request_record, current_reference_paths):
        Image.new('RGBA', (512, 512), 'blue' if current_frame_directory.name == 'base' else 'red').save(current_frame_directory / 'result.png')

    def test_invalid_input_and_sample_gate(self):
        for current_overrides in ({'end_frame': 2}, {'seed': True}, {'width': 1024}, {'extra': 1}, {'start_frame': 0}, {'prompt': 'word '*100}, {'source_id': '../file'}, {'outfit_prompt': ''}):
            with self.subTest(current_overrides=current_overrides), self.assertRaises(ValueError):
                self.current_service_instance.validate_generation_request({**self.current_request_record, **current_overrides})

    def test_gui_upload_matches_service_contract(self):
        from tools.review.ui.gradio.animation_separation_app import build_separation_request
        with Image.open(self.current_source_path) as current_reference_image:
            current_gui_request = build_separation_request(current_reference_image, 768, 10107, 'Create base.', 'Keep outfit.')
        current_saved_record = self.current_service_instance.validate_generation_request(current_gui_request)
        self.assertEqual(len(current_saved_record['images']), 1)
        self.assertEqual(current_saved_record['width'], 768)
        self.assertTrue(current_saved_record['source_id'].startswith('upload:'))
        with self.assertRaises(ValueError):
            build_separation_request(None, 768, 10107, 'Create base.', 'Keep outfit.')

    def test_single_upload_required(self):
        for current_images_value in ([], self.current_request_record['images'] * 2, ['invalid']):
            with self.assertRaises(ValueError):
                self.current_service_instance.validate_generation_request({**self.current_request_record, 'images': current_images_value})
        current_saved_record = self.current_service_instance.validate_generation_request(self.current_request_record)
        self.assertEqual(len(current_saved_record['frames']), 1)
        self.assertEqual(current_saved_record['frames'][0]['rect'], {'x': 0, 'y': 0, 'width': 32, 'height': 16})

    def test_export_resume_and_tamper_detection(self):
        current_sample_directory, current_saved_record = self.prepare_saved_sample()
        current_generation_calls = []
        def generate_recorded_frame(*current_arguments):
            current_generation_calls.append((current_arguments[0].name, current_arguments[1]['prompt'], current_arguments[2][0].read_bytes()))
            self.generate_test_frame(*current_arguments)
        render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)
        render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)
        self.assertEqual(len(current_generation_calls), 2)
        self.assertEqual([current_call_record[1] for current_call_record in current_generation_calls], [current_saved_record['prompt'], current_saved_record['outfit_prompt']])
        self.assertEqual(current_generation_calls[0][2], current_generation_calls[1][2])
        self.assertTrue((current_sample_directory / 'separation.zip').is_file())
        with Image.open(current_sample_directory / 'base-sheet.png') as current_base_image, Image.open(current_sample_directory / 'outfit-sheet.png') as current_outfit_image:
            self.assertEqual(current_base_image.getpixel((0, 0)), (0, 0, 255, 255))
            self.assertEqual(current_outfit_image.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertFalse((current_sample_directory / 'head-sheet.png').exists())
        current_manifest_record = json.loads((current_sample_directory / 'manifest.json').read_text())
        self.assertEqual(current_manifest_record['frames'][0]['source']['rect'], {'x': 0, 'y': 0, 'width': 32, 'height': 16})
        with Image.open(current_sample_directory / 'base-sheet.png') as current_head_image:
            self.assertEqual(current_head_image.size, (512, 512))
        (current_sample_directory / 'frame-001/base/result.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)

    def test_gateway_cli_payload(self):
        with patch('tools.review.common.management_gateway.call_management_api', return_value={'id': 'sample'}) as current_api_call, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('animation-separation', ['generate', '--reference', str(self.current_source_path), '--detach'])
        self.assertEqual(current_api_call.call_args.args[1], '/animation-separation/jobs')
        current_api_payload = current_api_call.call_args.args[2]
        self.assertEqual(current_api_payload['steps'], 40)
        self.assertEqual(current_api_payload['width'], 768)
        self.assertEqual(current_api_payload['images'], self.current_request_record['images'])

    def test_interrupted_batch_resumes_unfinished_frame(self):
        current_job_directory, current_saved_record = self.prepare_saved_sample()
        current_saved_record['frames'] = current_saved_record['frames'] * 2
        current_saved_record['references'] = current_saved_record['references'] * 2
        current_generation_calls = []
        def generate_interrupted_frame(current_frame_directory, current_request_record, current_reference_paths):
            current_generation_calls.append(current_frame_directory.parent.name + '/' + current_frame_directory.name)
            if current_frame_directory.name == 'outfit':
                raise RuntimeError('테스트용 중단')
            self.generate_test_frame(current_frame_directory, current_request_record, current_reference_paths)
        with self.assertRaises(RuntimeError):
            render_separation_outputs(current_job_directory, current_saved_record, generate_interrupted_frame)
        self.assertFalse((current_job_directory / 'separation.zip').exists())
        def generate_remaining_frame(current_frame_directory, current_request_record, current_reference_paths):
            current_generation_calls.append(current_frame_directory.parent.name + '/' + current_frame_directory.name)
            self.generate_test_frame(current_frame_directory, current_request_record, current_reference_paths)
        render_separation_outputs(current_job_directory, current_saved_record, generate_remaining_frame)
        self.assertEqual(current_generation_calls, ['frame-001/base', 'frame-001/outfit', 'frame-001/outfit', 'frame-002/base', 'frame-002/outfit'])
        self.assertEqual(json.loads((current_job_directory / 'separation-progress.json').read_text())['completed'], 2)

    def test_legacy_resume_rejected(self):
        current_job_directory, current_saved_record = self.prepare_saved_sample()
        current_saved_record.pop('schema_version')
        (current_job_directory / 'request.json').write_text(json.dumps(current_saved_record))
        with self.assertRaisesRegex(ValueError, '이전'):
            self.current_service_instance.validate_generation_resume(current_job_directory)
