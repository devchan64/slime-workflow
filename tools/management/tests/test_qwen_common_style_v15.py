"""새 요청의 공용 화풍과 과거 기록 재개 계약."""
import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from generators.image.common_art_style import compose_common_style_prompt, load_common_style_record
from tools.management.domains.image.qwen_21_generation import validate_styled_qwen_request, verify_qwen_saved_request
from tools.management.domains.image.three_reference_generation import save_three_reference_inputs
from tools.management.domains.image.qwen_circular_generation import QwenCircularGenerationManager
from tools.management.domains.image.expression_generation import ExpressionGenerationManager, load_expression_configuration, verify_expression_saved_request
from tools.management.domains.image.seamless_generation import validate_seamless_request


class CommonStyleV15Tests(unittest.TestCase):
    def setUp(self):
        self.request_values = {'action': 'generate', 'prompt': 'A small tree.', 'images': [], 'width': 768, 'height': 768, 'steps': 40, 'seed': 10107}

    def test_qwen_defaults_deduplication_and_limit(self):
        current_style = load_common_style_record()['prompt']
        for current_request in (self.request_values, {**self.request_values, 'common_style': True}, {**self.request_values, 'prompt': 'Tree. ' + current_style}):
            current_result = validate_styled_qwen_request(current_request)
            self.assertEqual(' '.join(current_result['prompt'].split()).count(' '.join(current_style.split())), 1)
            self.assertEqual(current_result['common_style_v1']['version'], '1.5.0')
        with self.assertRaises(ValueError):
            validate_styled_qwen_request({**self.request_values, 'prompt': 'word ' * 59})

    def test_saved_new_and_legacy_requests_validate_without_current_style(self):
        from tools.management.domains.image.qwen_21_generation import validate_qwen_plain_request
        from unittest.mock import patch
        from unittest.mock import patch
        from generators.image.qwen_21_prompt_options import load_qwen_prompt_options
        current_old_options = {**load_qwen_prompt_options(), 'style_source': 'prompts/art-style.yaml#slime_painterly_diorama_v1', 'common_style': 'Hand-painted game illustration, soft shading, clear materials, moderate detail.'}
        with patch('generators.image.qwen_21_prompt_options.load_qwen_prompt_options', return_value=current_old_options):
            current_legacy = validate_qwen_plain_request({**self.request_values, 'common_style': True})
        current_new = validate_styled_qwen_request(self.request_values)
        current_alpha = validate_styled_qwen_request({**self.request_values, 'transparent_background': True})
        for current_request in (current_legacy, current_new, current_alpha):
            with tempfile.TemporaryDirectory() as current_directory:
                current_root = Path(current_directory)
                current_saved = {**current_request, **save_three_reference_inputs(current_root, current_request)}
                current_saved.pop('images')
                with patch('generators.image.common_art_style.load_common_style_record', side_effect=AssertionError('current style read')):
                    verify_qwen_saved_request(current_root, current_saved)
                if 'common_style_v1' in current_saved:
                    current_saved['common_style_v1']['sha256'] = '0' * 64
                    with self.assertRaises(ValueError):
                        verify_qwen_saved_request(current_root, current_saved)

    def test_circular_expression_and_seamless(self):
        current_circular = QwenCircularGenerationManager().validate_generation_request(self.request_values)
        self.assertIn('Refined 2D fantasy game illustration', current_circular['prompt'])
        current_buffer = io.BytesIO()
        Image.new('RGB', (512, 512), 'white').save(current_buffer, format='PNG')
        current_reference = base64.b64encode(current_buffer.getvalue()).decode()
        for current_expression in load_expression_configuration()['expressions']:
            current_request = {**self.request_values, 'prompt': current_expression['id'], 'images': [current_reference]}
            current_result = ExpressionGenerationManager().validate_generation_request(current_request)
            self.assertLess(len(current_result['prompt'].split()), 100)
            with tempfile.TemporaryDirectory() as current_directory:
                current_root = Path(current_directory)
                current_saved = {**current_result, **save_three_reference_inputs(current_root, current_result)}
                current_saved.pop('images')
                verify_expression_saved_request(current_root, current_saved)
        current_seamless = validate_seamless_request(self.request_values)
        for current_stage in current_seamless['seamless_tile']['stage_prompts']:
            self.assertIn('Refined 2D fantasy game illustration', current_stage)
            self.assertLess(len(current_stage.split()), 100)


if __name__ == '__main__':
    unittest.main()
