import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.review.common.gradio_generator_changelog import (
    GENERATOR_CHANGELOG_PATHS,
    read_generator_changelog,
)


class GeneratorChangelogTests(unittest.TestCase):
    def test_registered_documents_are_distinct_and_readable(self):
        self.assertEqual(len(GENERATOR_CHANGELOG_PATHS), len(set(GENERATOR_CHANGELOG_PATHS.values())))
        for current_identifier, current_path in GENERATOR_CHANGELOG_PATHS.items():
            with self.subTest(generator=current_identifier):
                self.assertTrue(current_path.is_file())
                self.assertEqual(read_generator_changelog(current_identifier), current_path.read_text(encoding='utf-8'))

    def test_refresh_reads_original_and_missing_file_is_reported(self):
        with tempfile.TemporaryDirectory() as current_directory:
            current_path = Path(current_directory) / 'CHANGELOG.md'
            with patch.dict(GENERATOR_CHANGELOG_PATHS, {'test-generator': current_path}):
                self.assertIn('읽을 수 없습니다', read_generator_changelog('test-generator'))
                current_path.write_text('첫 번째', encoding='utf-8')
                self.assertEqual(read_generator_changelog('test-generator'), '첫 번째')
                current_path.write_text('두 번째', encoding='utf-8')
                self.assertEqual(read_generator_changelog('test-generator'), '두 번째')

    def test_unregistered_path_is_rejected(self):
        with self.assertRaises(ValueError):
            read_generator_changelog('../../AGENTS.md')

    def test_composed_generator_pages_show_their_changelog(self):
        from tools.review.common.management_asgi import GENERATOR_PAGE_PACKAGES, build_management_blocks
        current_changelog_names = {
            'qwen-21-generator': 'qwen-21',
            'qwen-21-circular-generator': 'qwen-21-circular',
            'expression-generator': 'expression',
            'building-generator': 'billboard-generator',
        }
        for current_tool_name in GENERATOR_PAGE_PACKAGES:
            with self.subTest(generator=current_tool_name):
                with patch('tools.review.ui.gradio.management_menu_app.load_manager_page_records', return_value=[]):
                    current_blocks, _ = build_management_blocks(current_tool_name, 8770, Path('/tmp/slime-test-no-menu.json'))
                current_expected_text = read_generator_changelog(current_changelog_names.get(current_tool_name, current_tool_name))
                current_components = current_blocks.config['components']
                self.assertTrue(any(current_component.get('props', {}).get('value') == current_expected_text.strip() for current_component in current_components))
