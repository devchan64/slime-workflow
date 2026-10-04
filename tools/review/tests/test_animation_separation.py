"""분리 서비스의 샘플 검수·원본 저장·중단 재개 계약을 검증한다."""
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
    def setUp(self):
        self.current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_root_path = Path(self.current_temp_directory.name)
        self.current_source_path = self.current_root_path / 'sheet.png'
        Image.new('RGBA', (32, 16), (20, 40, 60, 200)).save(self.current_source_path)
        self.current_source_record = {'id': 'asset:test', 'label': '테스트', 'fps': 8, 'frames': [{'frameId': f'down_left.{current_frame_index}', 'rect': {'x': current_frame_index*16, 'y': 0, 'width': 16, 'height': 16}, 'anchor': {'x': 8, 'y': 15}, 'source_path': str(self.current_source_path)} for current_frame_index in range(2)]}
        self.current_service_instance = separation_service_module.AnimationSeparationManager()
        self.current_service_instance.job_storage_root = self.current_root_path
        self.current_patch_context = patch.object(separation_service_module, 'load_sprite_editor_source', return_value=self.current_source_record)
        self.current_patch_context.start()
        self.addCleanup(self.current_patch_context.stop)
        self.current_request_record = {'action': 'generate', 'source_id': 'asset:test', 'start_frame': 1, 'end_frame': 1, 'width': 512, 'height': 512, 'steps': 40, 'seed': 1, 'prompt': 'Separate head and clothed body.'}

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
        Image.new('RGB', (512, 512), 'white').save(current_frame_directory / 'result.png')

    def test_invalid_input_and_sample_gate(self):
        for current_overrides in ({'end_frame': 2}, {'seed': True}, {'width': 1024}, {'extra': 1}, {'start_frame': 0}, {'prompt': 'word '*100}, {'source_id': '../file'}):
            with self.subTest(current_overrides=current_overrides), self.assertRaises(ValueError):
                self.current_service_instance.validate_generation_request({**self.current_request_record, **current_overrides})

    def test_completed_sample_same_settings_required(self):
        current_sample_directory, current_saved_record = self.prepare_saved_sample()
        render_separation_outputs(current_sample_directory, current_saved_record, self.generate_test_frame)
        (current_sample_directory / 'status.json').write_text('{"status":"completed"}')
        current_batch_request = {**self.current_request_record, 'end_frame': 2, 'sample_id': current_sample_directory.name}
        self.assertEqual(len(self.current_service_instance.validate_generation_request(current_batch_request)['images']), 2)
        with self.assertRaises(ValueError):
            self.current_service_instance.validate_generation_request({**current_batch_request, 'seed': 2})
        Image.new('RGBA', (32,16), 'red').save(self.current_source_path)
        with self.assertRaises(ValueError):
            self.current_service_instance.validate_generation_request(current_batch_request)

    def test_export_resume_and_tamper_detection(self):
        current_sample_directory, current_saved_record = self.prepare_saved_sample()
        current_generation_calls = []
        def generate_recorded_frame(*current_arguments):
            current_generation_calls.append(1)
            self.generate_test_frame(*current_arguments)
        render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)
        render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)
        self.assertEqual(len(current_generation_calls), 1)
        self.assertTrue((current_sample_directory / 'separation.zip').is_file())
        current_manifest_record = json.loads((current_sample_directory / 'manifest.json').read_text())
        self.assertEqual(current_manifest_record['frames'][0]['source']['anchor'], {'x': 8, 'y': 15})
        with Image.open(current_sample_directory / 'head-sheet.png') as current_head_image:
            self.assertEqual(current_head_image.size, (256, 512))
        (current_sample_directory / 'frame-001/result.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            render_separation_outputs(current_sample_directory, current_saved_record, generate_recorded_frame)

    def test_gateway_cli_payload(self):
        with patch('tools.review.common.management_gateway.call_management_api', return_value={'id': 'sample'}) as current_api_call, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('animation-separation', ['generate', '--source-id', 'asset:test', '--detach'])
        self.assertEqual(current_api_call.call_args.args[1], '/animation-separation/jobs')
        current_api_payload = current_api_call.call_args.args[2]
        self.assertEqual(current_api_payload['steps'], 40)
        self.assertEqual(current_api_payload['width'], 768)
        self.assertEqual(current_api_payload['start_frame'], current_api_payload['end_frame'])

    def test_interrupted_batch_resumes_unfinished_frame(self):
        current_job_directory, current_saved_record = self.prepare_saved_sample()
        current_saved_record['frames'] = current_saved_record['frames'] * 2
        current_saved_record['references'] = current_saved_record['references'] * 2
        current_generation_calls = []
        def generate_interrupted_frame(current_frame_directory, current_request_record, current_reference_paths):
            current_generation_calls.append(current_frame_directory.name)
            if current_frame_directory.name == 'frame-002':
                raise RuntimeError('테스트용 중단')
            self.generate_test_frame(current_frame_directory, current_request_record, current_reference_paths)
        with self.assertRaises(RuntimeError):
            render_separation_outputs(current_job_directory, current_saved_record, generate_interrupted_frame)
        self.assertFalse((current_job_directory / 'separation.zip').exists())
        def generate_remaining_frame(current_frame_directory, current_request_record, current_reference_paths):
            current_generation_calls.append(current_frame_directory.name)
            self.generate_test_frame(current_frame_directory, current_request_record, current_reference_paths)
        render_separation_outputs(current_job_directory, current_saved_record, generate_remaining_frame)
        self.assertEqual(current_generation_calls, ['frame-001', 'frame-002', 'frame-002'])
        self.assertEqual(json.loads((current_job_directory / 'separation-progress.json').read_text())['completed'], 2)
