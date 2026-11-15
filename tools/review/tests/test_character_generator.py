"""캐릭터 화면의 공용 화풍 및 공유 생성 계약."""
import importlib
import unittest

import yaml


class CharacterGeneratorTest(unittest.TestCase):
    def test_default_prompt_preserves_style_and_word_limit(self):
        current_page_module = importlib.import_module('generators.character-generator.page.interface')
        current_style_record = yaml.safe_load(current_page_module.STYLE_PROMPT_PATH.read_text(encoding='utf-8'))
        current_prompt_text = current_page_module.load_character_default_prompt()
        self.assertTrue(current_prompt_text.endswith(current_style_record['prompt']))
        self.assertLessEqual(len(current_prompt_text.split()), 99)
        self.assertNotIn('five-head-tall', current_prompt_text)

    def test_management_page_builds(self):
        from tools.review.common.management_asgi import QWEN_INTERFACE_OPTIONS
        from tools.review.ui.shared.qwen_generator_page import build_qwen_2511_interface
        current_page_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', **QWEN_INTERFACE_OPTIONS['character-generator'])
        self.assertEqual(current_page_blocks.title, 'Qwen 2.1 캐릭터 이미지 생성기')
        current_buttons = [current_component for current_component in current_page_blocks.blocks.values() if getattr(current_component, 'value', None) == '대기열에 추가']
        self.assertEqual(len(current_buttons), 1)
        self.assertTrue(current_buttons[0].interactive)


if __name__ == '__main__':
    unittest.main()
