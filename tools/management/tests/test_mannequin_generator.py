"""마네킨 제작 단계와 공용 생성 요청 연결 검증."""
import base64
import importlib
import io
import unittest

from tools.management.domains.image.qwen_21_generation import validate_styled_qwen_request
from tools.management.ui.shared.qwen_generator_page import prepare_reference_image_bytes


class MannequinGeneratorTests(unittest.TestCase):
    def test_clothed_preset_uses_faced_body_and_preserves_face(self):
        current_module = importlib.import_module('generators.mannequin-generator.page.interface')
        current_description, current_preview, current_unused = current_module.preview_mannequin_preset('clothed')
        current_prompt, current_first_image, current_second_image = current_module.load_mannequin_preset('clothed')
        self.assertIn('neutral-body-faced-four-directions.png', current_description)
        self.assertIn('Preserve the existing facial features and expression', current_prompt)
        self.assertNotIn('no facial features', current_prompt.lower())
        self.assertEqual(current_preview.tobytes(), current_first_image.tobytes())
        self.assertIsNone(current_unused)
        self.assertIsNone(current_second_image)
        current_request = validate_styled_qwen_request({'action': 'generate', 'prompt': current_prompt, 'images': [base64.b64encode(prepare_reference_image_bytes([current_first_image])[0]).decode()], 'width': 768, 'height': 1152, 'steps': 40, 'seed': 10110})
        self.assertLess(current_request['qwen21']['prompt_word_count'], 100)
        self.assertEqual(current_request['common_style_v1']['version'], '1.5.0')

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

    def test_mannequin_service_is_separate_from_general_qwen(self):
        from tools.management.domains.image.mannequin_generation import MannequinGenerationManager
        from tools.management.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from tools.management.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS
        from tools.management.domains.image.three_reference_generation import validate_three_reference_job_path
        current_mannequin_manager = MannequinGenerationManager()
        current_general_manager = QwenPlainGenerationManager()
        self.assertNotEqual(current_mannequin_manager.job_storage_root, current_general_manager.job_storage_root)
        self.assertNotEqual(current_mannequin_manager.history_storage_path(), current_general_manager.history_storage_path())
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['mannequin-generator'], '/mannequin-generator')
        self.assertEqual(MANAGEMENT_SERVICE_COMMANDS['mannequin-generator'], MANAGEMENT_SERVICE_COMMANDS['qwen-21'])
        self.assertEqual(validate_three_reference_job_path(current_mannequin_manager.job_storage_root / 'example'), (current_mannequin_manager.job_storage_root / 'example').resolve())

    def test_page_integrates_with_management_menu(self):
        from tools.management.common.management_asgi import build_management_blocks
        from tools.management.common.management_catalog import DEFAULT_PAGE_RECORDS, resolve_management_page_path
        from unittest.mock import patch
        from pathlib import Path
        current_record = next(current_item for current_item in DEFAULT_PAGE_RECORDS if current_item['id'] == 'mannequin-generator')
        self.assertEqual(resolve_management_page_path(current_record), '/management/frame/mannequin-generator/')
        with patch('tools.management.ui.gradio.management_menu_app.load_manager_page_records', return_value=[]):
            current_blocks, _ = build_management_blocks('mannequin-generator', 8770, Path('/tmp/no-menu.json'))
        current_labels = [current_item.get('props', {}).get('label') for current_item in current_blocks.config['components']]
        self.assertIn('제작 단계', current_labels)
        self.assertIn('제작 단계 프롬프트 예시', current_labels)
        self.assertLess(current_labels.index('제작 단계'), current_labels.index('프롬프트'))
        current_preview_callback = next(current_function.fn for current_function in current_blocks.fns.values() if getattr(current_function.fn, '__name__', '') == 'preview_mannequin_stage')
        current_module = importlib.import_module('generators.mannequin-generator.page.interface')
        for current_preset_id, current_preset_record in current_module.MANNEQUIN_PRESET_RECORDS.items():
            self.assertEqual(current_preview_callback(current_preset_id)[3], current_preset_record[3])
        current_apply_callback = next(current_function.fn for current_function in current_blocks.fns.values() if getattr(current_function.fn, '__name__', '') == 'apply_mannequin_stage')
        self.assertEqual(current_apply_callback('face')[-2:], (1056, 1056))
        self.assertEqual(current_apply_callback('face-on-body')[-2:], (768, 1152))


if __name__ == '__main__':
    unittest.main()
