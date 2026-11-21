import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.management.common.generator_changelog import (
    GENERATOR_CHANGELOG_PATHS,
    read_generator_changelog,
    paginate_changelog, read_changelog_page,
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

    def test_date_pages_group_same_date_and_preserve_undated_documents(self):
        pages = paginate_changelog('# 제목\n\n## 2026-01-01\n옛 기록\n\n## 2026-02-01 · 첫째\n내용 A\n\n## 2026-02-01 · 둘째\n내용 B')
        self.assertEqual([page[0] for page in pages], ['2026-02-01', '2026-01-01'])
        self.assertIn('내용 A', pages[0][1])
        self.assertIn('내용 B', pages[0][1])
        self.assertNotIn('옛 기록', pages[0][1])
        self.assertEqual(paginate_changelog('날짜 없는 기록'), [(None, '날짜 없는 기록')])

    def test_long_undated_and_dated_records_are_bounded(self):
        text = '# 제목\n\n' + '\n'.join(f'- 미기재 {i}' for i in range(22))
        text += '\n\n## 2026-01-01\n' + '\n'.join(f'- 날짜 {i}' for i in range(12))
        pages = paginate_changelog(text)
        self.assertEqual([date for date, _ in pages], [None, None, None, '2026-01-01', '2026-01-01'])
        self.assertNotIn('미기재 0', pages[3][1])
        self.assertIn('날짜 11', pages[4][1])

    def test_unregistered_path_is_rejected(self):
        with self.assertRaises(ValueError):
            read_generator_changelog('../../AGENTS.md')

    def test_archive_services_expose_their_changelog_page(self):
        from tools.management.common.management_asgi import GENERATOR_PAGE_PACKAGES
        aliases = {'qwen-21-generator': 'qwen-21', 'qwen-21-circular-generator': 'qwen-21-circular',
                   'character-generator': 'qwen-21', 'expression-generator': 'expression',
                   'building-generator': 'billboard-generator'}
        for name in GENERATOR_PAGE_PACKAGES:
            service = aliases.get(name, name)
            with self.subTest(service=service):
                date, content = paginate_changelog(GENERATOR_CHANGELOG_PATHS[service].read_text())[0]
                page = read_changelog_page(service)
                self.assertEqual((page['date'], page['content']), (date, content))
