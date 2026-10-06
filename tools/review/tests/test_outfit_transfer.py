"""복장 착용 생성기의 참조 순서·CLI·공용 UI 계약."""
import base64
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.domains.image.outfit_transfer_generation import OutfitTransferGenerationManager, load_outfit_transfer_prompt
from tools.review.common.management_gateway import execute_gateway_arguments


class OutfitTransferContractTests(unittest.TestCase):
    def test_worker_accepts_registered_storage_only(self):
        from tools.review.domains.image.three_reference_generation import validate_three_reference_job_path
        current_service_manager = OutfitTransferGenerationManager()
        current_job_directory = current_service_manager.job_storage_root / '2026-10-05_23-16-36-65f2ed35'
        self.assertEqual(validate_three_reference_job_path(current_job_directory), current_job_directory.resolve())
        with self.assertRaises(ValueError):
            validate_three_reference_job_path(current_service_manager.job_storage_root / '..' / 'unregistered' / 'job')
        with tempfile.TemporaryDirectory() as current_temp_directory:
            with self.assertRaises(ValueError):
                validate_three_reference_job_path(current_temp_directory)

    def test_saved_reference_count_checked(self):
        from tools.review.domains.image.outfit_transfer_generation import validate_outfit_transfer_contract
        current_saved_request = {'references': ['reference-1.png', 'reference-2.png'], 'width': 768, 'height': 768}
        validate_outfit_transfer_contract(current_saved_request, saved_request_enabled=True)
        with self.assertRaises(ValueError):
            validate_outfit_transfer_contract({**current_saved_request, 'references': ['reference-1.png']}, saved_request_enabled=True)

    def test_reference_order_and_count(self):
        current_image_values = []
        for current_color_name in ('red', 'blue'):
            current_image_buffer = io.BytesIO()
            Image.new('RGB', (32, 32), current_color_name).save(current_image_buffer, format='PNG')
            current_image_values.append(base64.b64encode(current_image_buffer.getvalue()).decode())
        current_request_record = dict(action='generate', images=current_image_values, prompt=load_outfit_transfer_prompt(), width=768, height=768, steps=40, seed=1)
        current_service_manager = OutfitTransferGenerationManager()
        current_saved_record = current_service_manager.validate_generation_request(current_request_record)
        self.assertEqual(current_saved_record['images'], current_image_values)
        self.assertEqual(current_service_manager.route_prefix_value, '/outfit-transfer')
        for current_invalid_images in ([], current_image_values[:1], current_image_values * 2):
            with self.assertRaises(ValueError):
                current_service_manager.validate_generation_request({**current_request_record, 'images': current_invalid_images})

    def test_cli_uses_default_prompt(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_reference_path = Path(current_temp_directory) / 'reference.png'
            Image.new('RGB', (32, 32)).save(current_reference_path)
            with patch('tools.review.common.management_gateway.call_management_api', return_value={'id': 'test'}) as current_api_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments('outfit-transfer', ['generate', '--reference', str(current_reference_path), '--reference', str(current_reference_path), '--detach'])
            current_payload_record = current_api_mock.call_args.args[2]
            self.assertEqual(current_api_mock.call_args.args[1], '/outfit-transfer/jobs')
            self.assertEqual(current_payload_record['prompt'], load_outfit_transfer_prompt())
            self.assertEqual(current_payload_record['width'], 768)
            self.assertEqual(len(current_payload_record['images']), 2)

    def test_shared_ui_has_two_named_inputs(self):
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        current_interface_value = build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, outfit_transfer_enabled=True)
        current_component_values = current_interface_value.get_config_file()['components']
        current_image_labels = [record['props']['label'] for record in current_component_values if record['type'] == 'image']
        self.assertEqual(current_image_labels, ['바디 레퍼런스 · 필수', '아웃핏 레퍼런스 · 필수'])
