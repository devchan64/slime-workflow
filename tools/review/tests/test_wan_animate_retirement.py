"""Animate 폐기와 활성 생성기의 공유 자원 연결을 검사한다."""
import unittest
from pathlib import Path
from tools.review.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS
from tools.review.ui.gradio.management_menu_app import NATIVE_MANAGEMENT_APPLICATIONS

class WanAnimateRetirementTests(unittest.TestCase):
    def test_retired_service_and_ui(self):
        self.assertNotIn('wan22-animate', MANAGEMENT_SERVICE_COMMANDS)
        self.assertNotIn('wan22-animate-generator', NATIVE_MANAGEMENT_APPLICATIONS)
        for current_command_name in ('generate','resume','history','model-status'):
            with self.assertRaisesRegex(ValueError,'폐기'):
                resolve_management_command('wan22-animate',current_command_name,{})
        self.assertFalse(Path('generators/wan_animate').exists())
        self.assertFalse(Path('tools/review/ui/gradio/wan_animate_app.py').exists())

    def test_shared_validation_preserved(self):
        from generators.common.onnx_model_validation import validate_external_tensor_files
        self.assertTrue(callable(validate_external_tensor_files))
        self.assertIn('generators/common/onnx_model_validation.py',Path('generators/kimodo/reference_extraction.py').read_text())
        from generators.wan_vace.contracts import VACE_MODEL_FILES
        self.assertIn('wan_2.1_vae.safetensors',VACE_MODEL_FILES['vae'][0])
