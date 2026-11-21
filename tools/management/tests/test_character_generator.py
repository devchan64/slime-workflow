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

    def test_character_page_resolves_to_archive(self):
        from tools.management.common.management_catalog import resolve_management_page_path
        row = {'id': 'character-generator', 'uiMode': 'archive'}
        self.assertEqual(resolve_management_page_path(row), '/management/frame/character-generator/')

