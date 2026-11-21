"""1.3B 모델과 참조 인코더의 준비 검증."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generators.wan_fun import wan13_model_assets


class Wan13ModelAssetsTests(unittest.TestCase):
    def test_prepare_dispatches_profile_and_progress_is_separate(self):
        from gui.ui.gradio import model_management_app
        from workflow.common.model_download_progress import format_model_download_status
        with patch.object(model_management_app, 'execute_remote_management_command', return_value={'id': 'job'}) as current_gateway_mock:
            model_management_app.execute_wan13_model_command('prepare', {'action': 'prepare'})
            current_gateway_mock.assert_called_once_with('wan22-fun-control', 'prepare', {'action': 'prepare', 'model_profile': 'wan21-1.3b'})
        current_progress_records = [{'model': wan13_model_assets.WAN13_REPOSITORY_NAME + '/diffusion_pytorch_model.safetensors', 'status': 'running', 'bytes': 50, 'total_bytes': 100}]
        self.assertIn('50.0%', format_model_download_status(current_progress_records, 'wan21-fun-1.3b'))
        self.assertNotIn('50.0%', format_model_download_status(current_progress_records, 'wan22-fun-control'))

    def test_manager_accepts_only_explicit_wan13_prepare_profile(self):
        from workflow.domains.wan_fun.generation import FunControlGenerationManager
        from workflow.common.management_gateway import resolve_management_command
        current_manager_instance = FunControlGenerationManager()
        self.assertEqual(current_manager_instance.validate_generation_request({'action': 'prepare', 'model_profile': 'wan21-1.3b'})['model_profile'], 'wan21-1.3b')
        resolve_management_command('wan22-fun-control', 'prepare', {'action': 'prepare', 'model_profile': 'wan21-1.3b'})
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-fun-control', 'prepare', {'action': 'prepare', 'model_profile': 'unknown'})
        with self.assertRaises(ValueError):
            current_manager_instance.validate_generation_request({'action': 'prepare', 'model_profile': 'unknown'})

    def test_existing_inputs_can_select_wan13_and_unknown_profile_fails(self):
        import base64
        import io
        from PIL import Image
        from generators.wan_fun.contracts import validate_fun_request
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (832, 480)).save(current_image_buffer, 'PNG')
        current_encoded_image = base64.b64encode(current_image_buffer.getvalue()).decode()
        current_request_record = {'action': 'generate', 'prompt': 'stand', 'negative_prompt': '', 'images': [current_encoded_image] * 6,
                                  'width': 832, 'height': 480, 'frames': 5, 'steps': 2, 'seed': 42, 'flow_shift': 5,
                                  'guidance_scale': 6, 'switch_ratio': .5, 'control_type': 'pose', 'model_profile': 'wan21-1.3b'}
        current_validated_record = validate_fun_request(current_request_record)
        self.assertEqual(current_validated_record['model_profile'], 'wan21-1.3b')
        self.assertEqual(current_validated_record['tag'], 'wan21-fun-1.3b')
        from generators.wan_fun.page.interface import describe_fun_model_steps
        self.assertIn('단일 모델', describe_fun_model_steps('wan21-1.3b', 20, .5))
        self.assertIn('고노이즈', describe_fun_model_steps('wan22-14b', 20, .5))
        with self.assertRaises(ValueError):
            validate_fun_request({**current_request_record, 'model_profile': 'unknown'})

    def test_only_verified_finished_legacy_generation_is_ignored_by_prepare_check(self):
        from workflow.domains.wan_fun.generation import FunControlGenerationManager
        from workflow.domains.image.image_generation import WORKFLOW_ROOT_PATH
        import json
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manager_instance = FunControlGenerationManager()
            current_manager_instance.job_storage_root = Path(current_directory_name)
            current_job_path = current_manager_instance.job_storage_root / '2026-11-14_19-57-00-a9b8c7d6'
            current_job_path.mkdir()
            current_request_record = {'references': ['reference-1.png'], 'frames': 5}
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            (current_job_path/'status.json').write_text(json.dumps({'status': 'completed'}))
            current_command_values = [str(current_manager_instance.select_generation_python(current_request_record)), str(WORKFLOW_ROOT_PATH/current_manager_instance.select_generation_runner(current_request_record)), '--job-dir', str(current_job_path)]
            (current_job_path/'gpu-command.json').write_text(json.dumps({'command': current_command_values, 'service': 'wan-fun'}))
            self.assertEqual(current_manager_instance.inspect_video_resume_availability(), 'available')
            (current_job_path/'status.json').write_text(json.dumps({'status': 'running'}))
            self.assertEqual(current_manager_instance.inspect_video_resume_availability(), 'unknown')

    def test_inspection_requires_exact_size_and_hash_for_both_files(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_fixture_files = {'model.safetensors': b'model', 'clip.pth': b'clip'}
            current_expected_files = {current_name: (len(current_bytes), hashlib.sha256(current_bytes).hexdigest())
                                      for current_name, current_bytes in current_fixture_files.items()}
            with patch.object(wan13_model_assets, 'WAN13_MODEL_DIRECTORY', current_root_path), patch.object(wan13_model_assets, 'WAN13_MODEL_FILES', current_expected_files):
                self.assertFalse(wan13_model_assets.inspect_wan13_model_files()['ready'])
                for current_file_name, current_file_bytes in current_fixture_files.items():
                    (current_root_path / current_file_name).write_bytes(current_file_bytes)
                self.assertTrue(wan13_model_assets.inspect_wan13_model_files()['ready'])
                (current_root_path / 'clip.pth').write_bytes(b'xxxx')
                self.assertEqual(wan13_model_assets.inspect_wan13_model_files()['missing'], ['clip.pth'])
