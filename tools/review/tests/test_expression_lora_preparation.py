"""표정 LoRA의 고정 출처·무결성·모델 관리 연결."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.review.common.management_gateway import resolve_management_command
from tools.review.domains.image import expression_generation


class ExpressionLoraPreparationTests(unittest.TestCase):
    def test_gateway_and_model_catalog_contract(self):
        from tools.review.ui.gradio.model_management_app import MODEL_PREPARATION_SERVICES
        self.assertIn(('Qwen 2.1 표정 LoRA', 'expression-lora'), MODEL_PREPARATION_SERVICES)
        self.assertEqual(resolve_management_command('expression-lora', 'prepare', {'action': 'prepare'}), ('POST', '/expression-lora/jobs'))
        with self.assertRaises(ValueError):
            resolve_management_command('expression-lora', 'prepare', {'action': 'prepare', 'path': '/tmp/other'})

    def test_verified_download_and_existing_file_protection(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path = Path(current_temp_directory)
            current_target_path = current_root_path / 'model' / 'adapter.safetensors'
            current_expected_hash = hashlib.sha256(b'verified').hexdigest()
            def download_test_file(**current_download_options):
                current_download_path = Path(current_download_options['local_dir']) / 'adapter.safetensors'
                current_download_path.write_bytes(b'verified')
                self.assertEqual(current_download_options['revision'], '90abd1e')
                return str(current_download_path)
            with patch.object(expression_generation, 'WORKFLOW_ROOT_PATH', current_root_path), patch.object(expression_generation, 'EXPRESSION_ADAPTER_PATH', current_target_path), patch.object(expression_generation, 'EXPRESSION_ADAPTER_SHA256', current_expected_hash), patch('tools.review.common.model_huggingface_download.tracked_hf_hub_download', side_effect=download_test_file):
                self.assertEqual(expression_generation.download_expression_adapter(), current_target_path)
                self.assertEqual(current_target_path.read_bytes(), b'verified')
                current_target_path.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError, '해시'):
                    expression_generation.download_expression_adapter()
                self.assertEqual(current_target_path.read_bytes(), b'corrupt')

    def test_hash_mismatch_does_not_install_file(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path = Path(current_temp_directory)
            current_target_path = current_root_path / 'model' / 'adapter.safetensors'
            def download_wrong_file(**current_download_options):
                current_download_path = Path(current_download_options['local_dir']) / 'adapter.safetensors'
                current_download_path.write_bytes(b'wrong')
                return str(current_download_path)
            with patch.object(expression_generation, 'WORKFLOW_ROOT_PATH', current_root_path), patch.object(expression_generation, 'EXPRESSION_ADAPTER_PATH', current_target_path), patch('tools.review.common.model_huggingface_download.tracked_hf_hub_download', side_effect=download_wrong_file):
                with self.assertRaisesRegex(ValueError, '해시'):
                    expression_generation.download_expression_adapter()
                self.assertFalse(current_target_path.exists())
