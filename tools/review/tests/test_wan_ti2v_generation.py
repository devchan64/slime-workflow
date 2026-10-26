import base64
import io
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from generators.wan_ti2v.contracts import TI2V_DEFAULT_SETTINGS, validate_ti2v_request
from tools.review.common.management_gateway import resolve_management_command


class WanTi2vGenerationContractTest(unittest.TestCase):
    def test_gui_payload_matches_gateway_contract(self):
        from tools.review.ui.gradio.wan_ti2v_app import build_ti2v_payload
        current_payload_record = build_ti2v_payload(None, 'A character walks.', '', 5, 42, 2, 8, 5)
        self.assertNotIn('tag', current_payload_record)
        validate_ti2v_request(current_payload_record)
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_reference_path = Path(current_temporary_directory) / 'reference.png'
            Image.new('RGB', (400, 600), 'white').save(current_reference_path)
            current_payload_record = build_ti2v_payload(str(current_reference_path), 'A character walks.', '', 5, 42, 2, 8, 5)
            self.assertEqual(len(validate_ti2v_request(current_payload_record)['images']), 1)

    def test_gui_rejects_fractional_and_boolean_integers(self):
        from tools.review.ui.gradio.wan_ti2v_app import build_ti2v_payload
        for current_invalid_value in (5.5, True, float('nan')):
            with self.assertRaises(ValueError):
                build_ti2v_payload(None, 'Walk.', '', current_invalid_value, 42, 2, 8, 5)

    def test_model_check_rejects_truncated_files_and_wrong_runtime(self):
        import generators.wan_ti2v.contracts as current_contract_module
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_workspace_root = Path(current_temporary_directory)
            current_runtime_root = current_workspace_root / 'runtime'
            for current_runtime_name, current_revision_text in (('ComfyUI', current_contract_module.TI2V_RUNTIME_REVISION), ('ComfyUI-GGUF', current_contract_module.TI2V_GGUF_REVISION)):
                current_revision_path = current_runtime_root / current_runtime_name / 'PINNED_REVISION'
                current_revision_path.parent.mkdir(parents=True)
                current_revision_path.write_text(current_revision_text)
            for current_relative_path in current_contract_module.TI2V_MODEL_FILES.values():
                current_model_path = current_workspace_root / current_relative_path
                current_model_path.parent.mkdir(parents=True, exist_ok=True)
                current_model_path.write_bytes(b'1234')
            with patch.object(current_contract_module, 'TI2V_WORKSPACE_ROOT', current_workspace_root), patch.object(current_contract_module, 'TI2V_RUNTIME_DIRECTORY', current_runtime_root), patch.object(current_contract_module, 'TI2V_MODEL_SIZES', {'diffusion': 4, 'encoder': 4, 'vae': 4}):
                self.assertTrue(current_contract_module.inspect_ti2v_assets()['ready'])
                current_model_path.write_bytes(b'1')
                self.assertFalse(current_contract_module.inspect_ti2v_assets()['ready'])
                current_model_path.write_bytes(b'1234')
                current_revision_path.write_text('wrong')
                self.assertFalse(current_contract_module.inspect_ti2v_assets()['ready'])

    def build_reference_image_text(self):
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (832, 480), 'white').save(current_image_buffer, format='PNG')
        return base64.b64encode(current_image_buffer.getvalue()).decode()

    def build_request_record(self, image_values=None):
        return {'action': 'generate', 'prompt': 'A full-body character walks forward naturally.', 'negative_prompt': '', 'images': image_values or [], 'width': 832, 'height': 480, 'frames': TI2V_DEFAULT_SETTINGS['frames'], 'steps': TI2V_DEFAULT_SETTINGS['steps'], 'seed': TI2V_DEFAULT_SETTINGS['seed'], 'flow_shift': TI2V_DEFAULT_SETTINGS['flow_shift'], 'guidance_scale': TI2V_DEFAULT_SETTINGS['guidance_scale']}

    def test_text_to_video_request_is_accepted(self):
        self.assertEqual(validate_ti2v_request(self.build_request_record())['tag'], 'wan22-ti2v')

    def test_one_start_frame_request_is_accepted(self):
        self.assertEqual(len(validate_ti2v_request(self.build_request_record([self.build_reference_image_text()]))['images']), 1)

    def test_gateway_uses_ti2v_job_route(self):
        self.assertEqual(resolve_management_command('wan22-ti2v', 'generate', self.build_request_record()), ('POST', '/wan22-ti2v/jobs'))

    def test_second_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '1장만'):
            validate_ti2v_request(self.build_request_record([self.build_reference_image_text(), self.build_reference_image_text()]))
