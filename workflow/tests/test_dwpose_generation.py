"""단일 DWPose 입력과 공용 UI·CLI 계약 검증."""
import base64
import io
import unittest
from unittest.mock import patch
from PIL import Image
from generators.dwpose.contracts import validate_dwpose_request
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES
from gui.ui.gradio.dwpose_app import build_dwpose_interface


class DwposeGenerationTests(unittest.TestCase):
    def make_image_request(self, current_image_size=(832,480)):
        current_image_buffer = io.BytesIO()
        Image.new('RGB',current_image_size,'white').save(current_image_buffer,format='PNG')
        return {'action':'generate','images':[base64.b64encode(current_image_buffer.getvalue()).decode()]}

    def test_request_validation_contract(self):
        self.assertEqual(validate_dwpose_request(self.make_image_request())['frames'],1)
        for current_invalid_request in (self.make_image_request((480,480)), {**self.make_image_request(),'images':[]}, {**self.make_image_request(),'pose_include_face':1}, {**self.make_image_request(),'unknown':True}):
            with self.assertRaises(ValueError):
                validate_dwpose_request(current_invalid_request)

    def test_rocm_worker_and_missing_environment(self):
        from pathlib import Path
        from workflow.domains.dwpose import generation
        current_manager = generation.DwposeGenerationManager()
        self.assertTrue(current_manager.select_generation_runner().endswith('generators/dwpose/rocm_worker.py'))
        self.assertEqual(current_manager.select_generation_python(), generation.FUN_PYTHON_EXECUTABLE)
        with patch.object(generation, 'inspect_registered_preparation', return_value='idle'), \
                patch.object(generation, 'FUN_PYTHON_EXECUTABLE', Path('/nonexistent/dwpose/python')):
            self.assertFalse(generation.inspect_dwpose_runtime_status()['ready'])
            with self.assertRaisesRegex(ValueError, 'ROCm'):
                current_manager.validate_generation_runtime()

    def test_model_preparation_reports_running_and_avoids_duplicate(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from workflow.domains.dwpose import generation
        with TemporaryDirectory() as current_directory_name:
            current_python_path = Path(current_directory_name) / 'python'
            current_python_path.touch()
            with patch.object(generation, 'FUN_PYTHON_EXECUTABLE', current_python_path), \
                    patch.object(generation, 'inspect_registered_preparation', return_value='running'), \
                    patch.object(generation, 'start_registered_preparation') as current_start_mock:
                current_status_record = generation.inspect_dwpose_runtime_status()
                self.assertFalse(current_status_record['ready'])
                self.assertEqual(generation.DwposeGenerationManager().start_model_preparation()['preparation_status'], 'running')
                current_start_mock.assert_not_called()

    def test_pose_preparation_reserves_queue_and_reuses_existing_downloader(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from generators.dwpose import prepare
        from workflow.common import gpu_job_queue
        with TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_python_path = current_root_path / 'python'
            current_python_path.touch()
            current_queue_path = current_root_path / 'queue'
            def verify_pose_prepare_command(current_command_values, **current_options_values):
                self.assertEqual(current_command_values[1:], ['-m', 'generators.wan_fun.prepare_pose'])
                self.assertEqual(len(list((current_queue_path / 'active').glob('*.json'))), 1)
            with patch.object(prepare, 'FUN_PYTHON_EXECUTABLE', current_python_path), \
                    patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', current_queue_path), \
                    patch.object(prepare, 'validate_fun_pose_assets', side_effect=[ValueError('missing'), None]), \
                    patch.object(prepare.subprocess, 'run', side_effect=verify_pose_prepare_command) as current_run_mock:
                prepare.prepare_dwpose_model_files()
            current_run_mock.assert_called_once()
            self.assertFalse(list((current_queue_path / 'active').glob('*.json')))

    def test_gateway_and_ui_contract(self):
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['dwpose'],'/dwpose')
        self.assertIn('generate',MANAGEMENT_SERVICE_COMMANDS['dwpose'])
        current_mock_calls = []
        current_interface_blocks = build_dwpose_interface('http://127.0.0.1:8770',lambda *current_command_args: current_mock_calls.append(current_command_args))
        self.assertTrue(current_interface_blocks.config['components'])
        self.assertEqual(current_mock_calls,[])


if __name__ == '__main__':
    unittest.main()
