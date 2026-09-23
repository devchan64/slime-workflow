"""도서 출력의 원문 보존·읽기 순서·제목·참조 회귀 검증."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from generators.worldbuilding.bookbinding import plan_document_book
from generators.worldbuilding.book_cleanup import export_cleaned_book, format_chapter_markdown, rewrite_chapter_links
from generators.worldbuilding.documents import load_yaml_document


class BookCleanupTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_handle.cleanup)
        self.current_source_root = Path(self.current_temp_handle.name)/'docs'
        (self.current_source_root/'world').mkdir(parents=True)
        (self.current_source_root/'gameplay').mkdir()
        self.current_run_root = Path(self.current_temp_handle.name)/'state/run'
        self.current_config_values = {'source_document_root': str(self.current_source_root), 'private_state_root': str(self.current_run_root.parent)}
        self.current_request_values = {'collection_id': 'world', 'source_directory_paths': ['world'], 'book_title_text': '세계관'}
        self.current_source_texts = {
            'world/README.md': '# 세계관\n\n상태: 확정\n\n## 도시\n\n도시 소개.\n\n## 길드 전쟁\n\n길드 설명.\n\n## 시장 규칙\n\n경제 설명.\n\n[다음](town.md#주민) [두 번째](town.md#주민-1) [자료](data.yaml) [성장](../gameplay/growth.md)\n\n[참조][target]\n\n[target]: <town.md#주민> "주민"\n\n`[예시](town.md)`\n\n```md\n[예시](town.md)\n```\n',
            'world/town.md': '# 같은 제목\r\n\r\n## 주민\r\n\r\n첫 주민.\r\n\r\n## 주민\r\n\r\n둘째 주민.\r\n\r\n# 별도 규칙\r\n\r\n규칙 보존.\r\n',
            'world/other.md': '# 같은 제목\n\n다른 원본 내용.\n',
            'world/data.yaml': 'name: 자료\ntext: |\n  ```\n  [원문](town.md)\n',
        }
        for current_source_path, current_source_text in self.current_source_texts.items():
            (self.current_source_root/current_source_path).write_bytes(current_source_text.encode())
        (self.current_source_root/'gameplay/growth.md').write_text('# 성장\n')

    def export_test_book(self, current_plan_values=None):
        from generators.worldbuilding.bookbinding import collect_book_sources
        current_source_entries = collect_book_sources(self.current_config_values, ['world'])
        if current_plan_values is None:
            current_plan_values = plan_document_book(self.current_config_values, self.current_request_values)
        return export_cleaned_book(self.current_config_values, self.current_run_root, self.current_request_values, current_plan_values, current_source_entries)

    def test_default_plan_keeps_context_and_whole_document_order(self):
        current_plan_values = plan_document_book(self.current_config_values, self.current_request_values)
        for current_source_path, current_source_text in self.current_source_texts.items():
            current_source_blocks = [current_paragraph_entry for current_paragraph_entry in current_plan_values['paragraph_entries'] if current_paragraph_entry['source_document_path']==current_source_path]
            self.assertEqual(len({current_source_block['chapter_title'] for current_source_block in current_source_blocks}), 1)
            self.assertEqual(''.join(current_source_block['paragraph_text'] for current_source_block in current_source_blocks), current_source_text)

    def test_cleanup_preserves_sources_and_connects_markdown_references(self):
        current_plan_values = plan_document_book(self.current_config_values, self.current_request_values)
        current_plan_values['paragraph_entries'].reverse()
        current_result_values = self.export_test_book(current_plan_values)
        current_book_root = self.current_run_root/'completed-book'
        current_manifest_values = load_yaml_document(current_book_root/'manifest.yaml')
        self.assertEqual(len(current_manifest_values['chapter_entries']), 4)
        self.assertEqual(current_manifest_values['chapter_entries'][0]['source_document_paths'], ['world/README.md'])
        self.assertEqual(current_result_values['internal_link_count'], 4)
        self.assertEqual(current_result_values['outside_reference_count'], 1)
        self.assertEqual(current_result_values['broken_reference_count'], 0)
        self.assertEqual(current_result_values['yaml_document_count'], 1)
        current_saved_blocks = load_yaml_document(current_book_root/'paragraphs.yaml')['paragraph_entries']
        current_markdown_parser = MarkdownIt('commonmark', {'html': False}).enable('table')
        for current_chapter_entry in current_manifest_values['chapter_entries']:
            current_source_path = current_chapter_entry['source_document_paths'][0]
            current_chapter_path = current_book_root/current_chapter_entry['file_path']
            current_chapter_text = current_chapter_path.read_text()
            current_chapter_tokens = current_markdown_parser.parse(current_chapter_text)
            self.assertEqual(sum(current_parser_token.type=='heading_open' and current_parser_token.tag=='h1' for current_parser_token in current_chapter_tokens), 1)
            current_rebuilt_text = ''.join(current_source_block['paragraph_text'] for current_source_block in current_saved_blocks if current_source_block['source_document_path']==current_source_path)
            self.assertEqual(current_rebuilt_text, self.current_source_texts[current_source_path])
            self.assertEqual((self.current_source_root/current_source_path).read_bytes(), self.current_source_texts[current_source_path].encode())
            for current_parser_token in current_chapter_tokens:
                for current_child_token in current_parser_token.children or []:
                    if current_child_token.type=='link_open':
                        current_parsed_url = urlsplit(current_child_token.attrGet('href'))
                        self.assertTrue((current_chapter_path.parent/unquote(current_parsed_url.path)).is_file())
            if current_source_path=='world/data.yaml':
                self.assertEqual(current_chapter_entry['paragraph_count'], 0)
                self.assertEqual(next(current_parser_token.content for current_parser_token in current_chapter_tokens if current_parser_token.type=='fence'), self.current_source_texts[current_source_path])
            if current_source_path=='world/README.md':
                self.assertLess(current_chapter_text.index('도시 소개'), current_chapter_text.index('길드 설명'))
                self.assertLess(current_chapter_text.index('길드 설명'), current_chapter_text.index('경제 설명'))
                self.assertIn('`[예시](town.md)`', current_chapter_text)
                self.assertIn('```md\n[예시](town.md)\n```', current_chapter_text)

    def test_rejects_loss_duplicates_and_changed_content_before_output(self):
        current_plan_values = plan_document_book(self.current_config_values, self.current_request_values)
        current_missing_plan = copy.deepcopy(current_plan_values)
        current_missing_plan['paragraph_entries'].pop()
        current_duplicate_plan = copy.deepcopy(current_plan_values)
        current_duplicate_plan['paragraph_entries'].append(current_duplicate_plan['paragraph_entries'][0])
        current_changed_plan = copy.deepcopy(current_plan_values)
        current_changed_plan['paragraph_entries'][0]['paragraph_text'] = '변경된 원문'
        for current_invalid_plan in (current_missing_plan, current_duplicate_plan, current_changed_plan):
            with self.assertRaises(ValueError):
                self.export_test_book(current_invalid_plan)
            self.assertFalse((self.current_run_root/'completed-book').exists())

    def test_rejects_changed_source_snapshot(self):
        with patch('generators.worldbuilding.book_cleanup.collect_book_sources', return_value={}):
            with self.assertRaisesRegex(ValueError, '편집 중 원문'):
                self.export_test_book()
        self.assertFalse((self.current_run_root/'completed-book').exists())

    def test_reports_existing_broken_links_and_never_overwrites_result(self):
        (self.current_source_root/'world/broken.md').write_text('# 잘못된 참조\n\n[없는 파일](missing.md) [없는 절](town.md#없음)\n')
        current_result_values = self.export_test_book()
        self.assertEqual(current_result_values['broken_reference_count'], 2)
        self.assertTrue(current_result_values['quality_warnings'])
        with self.assertRaisesRegex(ValueError, '덮어쓸'):
            self.export_test_book()

    def test_normalizes_setext_and_missing_titles_without_losing_content(self):
        current_chapter_title, current_chapter_text, current_paragraph_count = format_chapter_markdown('world/a.md', '소개\n\n제목\n====\n\n내용\n\n두번째\n====\n')
        current_parsed_tokens = MarkdownIt().parse(current_chapter_text)
        self.assertEqual(sum(current_parser_token.type=='heading_open' and current_parser_token.tag=='h1' for current_parser_token in current_parsed_tokens), 1)
        self.assertEqual(current_chapter_title, '제목')
        self.assertIn('소개', current_chapter_text)
        self.assertIn('두번째', current_chapter_text)
        self.assertEqual(current_paragraph_count, 2)

    def test_link_rewrite_preserves_nested_parentheses_titles_and_code(self):
        current_source_text = '[설명](<doc (1).md> "제목")\n\n    [코드](<doc (1).md>)\n'
        current_output_text = rewrite_chapter_links(current_source_text, {'doc%20(1).md': '02-chapter.md'})
        self.assertIn('[설명](<02-chapter.md> "제목")', current_output_text)
        self.assertIn('    [코드](<doc (1).md>)', current_output_text)

    def test_refuses_to_change_literal_link_examples(self):
        with self.assertRaisesRegex(ValueError, '본문 또는 코드'):
            rewrite_chapter_links(r'\[예시](a.md) [실제](a.md)', {'a.md': '02-chapter.md'})

    def test_same_filename_in_different_directories_never_overwrites(self):
        for current_folder_name in ('first','second'):
            (self.current_source_root/'world'/current_folder_name).mkdir()
            (self.current_source_root/'world'/current_folder_name/'shared.md').write_text('# 같은 제목\n\n'+current_folder_name+' 원문\n')
        self.export_test_book()
        current_book_root=self.current_run_root/'completed-book'
        current_chapter_entries=load_yaml_document(current_book_root/'manifest.yaml')['chapter_entries']
        self.assertEqual(len({current_chapter_entry['file_path'] for current_chapter_entry in current_chapter_entries}),len(current_chapter_entries))
        for current_chapter_entry in current_chapter_entries:
            current_source_path=current_chapter_entry['source_document_paths'][0]
            if current_source_path.endswith('/shared.md'):
                self.assertIn(Path(current_source_path).parent.name+' 원문',(current_book_root/current_chapter_entry['file_path']).read_text())
