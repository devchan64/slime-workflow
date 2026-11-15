"""신체 비율 기준·선택·실행 기록의 무결성 검증."""
import base64
import importlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import gradio as gr
from tools.review.domains.image.qwen_21_generation import validate_styled_qwen_request, verify_qwen_saved_request
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs


class CharacterBodyReferenceTests(unittest.TestCase):
    def setUp(self):
        self.body_module = importlib.import_module('generators.character-generator.body_references')
        self.body_catalog = self.body_module.load_body_reference_catalog()
        self.request_values = {'action': 'generate', 'prompt': 'A character. ' + self.body_module.BODY_REFERENCE_ROLE_PROMPT, 'images': [], 'width': 768, 'height': 768, 'steps': 40, 'seed': 1}

    def test_catalog_images_and_version(self):
        self.assertEqual({current_record['id'] for current_record in self.body_catalog}, {'neutral-body-jointed', 'neutral-body-clothed'})
        for current_record in self.body_catalog:
            self.assertEqual(self.body_module.load_body_reference_image(current_record['id']).size, (1536, 1024))
        with self.assertRaises(ValueError):
            self.body_module.load_body_reference_image('../outside')

    def test_reference_record_and_resume_uses_saved_image(self):
        for current_record in self.body_catalog:
            current_buffer = io.BytesIO()
            self.body_module.load_body_reference_image(current_record['id']).save(current_buffer, format='PNG')
            current_input = {**self.request_values, 'body_reference_id': current_record['id'], 'images': [base64.b64encode(current_buffer.getvalue()).decode()]}
            current_request = validate_styled_qwen_request(current_input)
            self.assertEqual(current_request['body_reference_sources'][0]['source_sha256'], current_record['sha256'])
            with tempfile.TemporaryDirectory() as current_directory:
                current_root = Path(current_directory)
                current_saved = {**current_request, **save_three_reference_inputs(current_root, current_request)}
                current_saved.pop('images')
                with patch.object(self.body_module, 'load_body_reference_catalog', side_effect=AssertionError('현재 목록을 읽으면 안 됨')):
                    verify_qwen_saved_request(current_root, current_saved)
                current_saved['body_reference_sources'][0]['pixel_sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    verify_qwen_saved_request(current_root, current_saved)
        with self.assertRaisesRegex(ValueError, '첫 참조'):
            validate_styled_qwen_request({**self.request_values, 'body_reference_id': self.body_catalog[0]['id']})
        current_buffer = io.BytesIO()
        Image.new('RGB', (512, 512), 'white').save(current_buffer, format='PNG')
        with self.assertRaisesRegex(ValueError, '첫 참조'):
            validate_styled_qwen_request({**self.request_values, 'body_reference_id': self.body_catalog[0]['id'], 'images': [base64.b64encode(current_buffer.getvalue()).decode()]})

    def test_character_page_has_reference_selection(self):
        current_page = importlib.import_module('generators.character-generator.page.interface')
        current_blocks = current_page.build_generator_page('http://127.0.0.1:8770', 8770)
        current_components = current_blocks.config['components']
        self.assertTrue(any(current_item['props'].get('label') == '신체 비율 참조 선택' for current_item in current_components))
        self.assertTrue(any(current_item['props'].get('value') == '선택 기준을 첫 참조에 적용' for current_item in current_components))
        current_image_control = next(current_component for current_component in current_blocks.blocks.values() if isinstance(current_component, gr.Image) and current_component.label == '참조 이미지 1')
        current_original_image = self.body_module.load_body_reference_image('neutral-body-jointed')
        current_roundtrip_image = current_image_control.preprocess(current_image_control.postprocess(current_original_image))
        self.assertEqual(current_image_control.format, 'png')
        self.assertEqual(current_roundtrip_image.tobytes(), current_original_image.tobytes())
        current_apply_callback = next(current_function.fn for current_function in current_blocks.fns.values() if getattr(current_function.fn, '__name__', '') == 'apply_character_body')
        current_image, current_prompt, current_identifier = current_apply_callback('neutral-body-jointed', current_page.load_character_default_prompt(), False)
        self.assertEqual(current_identifier, 'neutral-body-jointed')
        self.assertEqual(current_prompt.count(self.body_module.BODY_REFERENCE_ROLE_PROMPT), 1)
        self.assertEqual(current_apply_callback('neutral-body-clothed', current_prompt, False)[1], current_prompt)
        with self.assertRaises(Exception):
            current_apply_callback('neutral-body-jointed', current_prompt, True)


if __name__ == '__main__':
    unittest.main()
