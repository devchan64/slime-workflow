"""마네킨 제작 단계와 공용 생성 요청 연결 검증."""
import base64
import importlib
import io
import unittest

from tools.review.domains.image.qwen_21_generation import validate_styled_qwen_request
from tools.review.ui.shared.qwen_generator_page import prepare_reference_image_bytes


class MannequinGeneratorTests(unittest.TestCase):
    def test_presets_produce_valid_requests(self):
        current_module = importlib.import_module('generators.mannequin-generator.page.interface')
        for current_key in current_module.MANNEQUIN_PRESET_RECORDS:
            with self.subTest(preset=current_key):
                current_prompt, *current_images = current_module.load_mannequin_preset(current_key)
                current_bytes = prepare_reference_image_bytes(current_images, composite_transparent_background=True)
                current_request = validate_styled_qwen_request({'action': 'generate', 'prompt': current_prompt, 'images': [base64.b64encode(current_value).decode() for current_value in current_bytes], 'width': 768, 'height': 768, 'steps': 40, 'seed': 10107})
                self.assertLessEqual(len(current_request['prompt'].split()), 99)
                self.assertEqual(len(current_bytes), 2 if current_key == 'face-on-body' else 1)
        current_description, current_body_preview, current_face_preview = current_module.preview_mannequin_preset('face-on-body')
        self.assertIn('참조 1: `neutral-body-four-directions.png`', current_description)
        self.assertIn('참조 2: `neutral-head-basic-four-directions.png`', current_description)
        self.assertEqual(current_body_preview.tobytes(), current_module.load_mannequin_preset('jointed')[1].tobytes())
        self.assertEqual(current_face_preview.tobytes(), current_module.load_mannequin_preset('face')[1].tobytes())
        current_description, current_preview, current_unused = current_module.preview_mannequin_preset('jointed')
        self.assertIn('neutral-body-four-directions.png', current_description)
        self.assertIsNotNone(current_preview)
        self.assertIsNone(current_unused)
        with self.assertRaises(ValueError):
            current_module.load_mannequin_preset('../outside')

    def test_page_integrates_with_management_menu(self):
        from tools.review.common.management_asgi import build_management_blocks
        from tools.review.ui.gradio.management_menu_app import DEFAULT_PAGE_RECORDS, resolve_management_page_path
        from unittest.mock import patch
        from pathlib import Path
        current_record = next(current_item for current_item in DEFAULT_PAGE_RECORDS if current_item['id'] == 'mannequin-generator')
        self.assertEqual(resolve_management_page_path(current_record), '/management/frame/mannequin-generator/')
        with patch('tools.review.ui.gradio.management_menu_app.load_manager_page_records', return_value=[]):
            current_blocks, _ = build_management_blocks('mannequin-generator', 8770, Path('/tmp/no-menu.json'))
        current_labels = [current_item.get('props', {}).get('label') for current_item in current_blocks.config['components']]
        self.assertIn('제작 단계', current_labels)
        self.assertTrue(any(getattr(current_function.fn, '__name__', '') == 'load_mannequin_preset' for current_function in current_blocks.fns.values()))


if __name__ == '__main__':
    unittest.main()
