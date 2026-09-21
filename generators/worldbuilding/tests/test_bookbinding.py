"""도서 문단 재배치의 원문 보존·출처·경로·갱신 경계를 검증한다."""
from pathlib import Path
import tempfile
import unittest
from generators.worldbuilding.bookbinding import (plan_document_book,build_document_book,list_document_books,read_book_artifact)
from generators.worldbuilding.documents import load_yaml_document


class DocumentBookTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle=tempfile.TemporaryDirectory()
        self.current_source_root=Path(self.current_temp_handle.name)/'docs'
        (self.current_source_root/'world').mkdir(parents=True)
        self.current_private_root=self.current_source_root/'private/.state'
        self.current_private_root.mkdir(parents=True)
        self.current_config_values={'source_document_root':str(self.current_source_root),'private_state_root':str(self.current_private_root)}
        self.current_source_texts={'world/first.md':'# 항구\n\n상태: 신규 제안\n\n## 주민\n\n은빛 주민은 바다를 살핀다.\n\n[다른 주민](second.md#주민)\n\n| 이름 | 직책 |\n| --- | --- |\n| 라온 | 대표 |\n\n```text\n<script>bad()</script>\n\n코드 원문\n```\n','world/second.md':'# 마을\n\n## 주민\n\n마을 주민은 숲을 살핀다.\n\n<script>bad()</script>\n','world/data.yaml':'name: 은빛\nstatus: proposal\n'}
        for current_source_path,current_source_text in self.current_source_texts.items():
            (self.current_source_root/current_source_path).write_text(current_source_text)
        (self.current_private_root/'secret.md').write_text('보관 제외')
        self.current_request_values={'book_title_text':'합성 설정집','source_directory_paths':['world']}

    def tearDown(self):
        self.current_temp_handle.cleanup()

    def test_reorders_paragraphs_without_loss_and_connects_links(self):
        current_plan_values=plan_document_book(self.current_config_values,self.current_request_values)
        current_placements=list(reversed(current_plan_values['paragraph_placements']))
        current_request_values={**self.current_request_values,'paragraph_placements':current_placements}
        current_manifest_values=build_document_book(self.current_config_values,current_request_values)
        current_book_root=self.current_private_root/'books'/current_manifest_values['book_id']
        current_paragraph_entries=load_yaml_document(current_book_root/'paragraphs.yaml')['paragraph_entries']
        self.assertEqual([current_paragraph_entry['paragraph_id'] for current_paragraph_entry in current_paragraph_entries],[current_placement_entry['paragraph_id'] for current_placement_entry in current_placements])
        for current_source_path,current_source_text in self.current_source_texts.items():
            current_rebuilt_text=''.join(current_paragraph_entry['paragraph_text'] for current_paragraph_entry in sorted(current_paragraph_entries,key=lambda current_paragraph_entry:current_paragraph_entry['source_start_line']) if current_paragraph_entry['source_document_path']==current_source_path)
            self.assertEqual(current_rebuilt_text,current_source_text)
            self.assertEqual((self.current_source_root/current_source_path).read_text(),current_source_text)
        current_html_text=(current_book_root/'book.html').read_text()
        self.assertNotIn('<script>bad()',current_html_text)
        self.assertIn('<table>',current_html_text)
        self.assertIn('href="#paragraph-',current_html_text)
        self.assertNotIn('@@TITLE@@',current_html_text)
        self.assertIn('보존 원문',current_html_text)

    def test_rejects_missing_duplicate_unknown_or_changed_paragraph(self):
        current_plan_values=plan_document_book(self.current_config_values,self.current_request_values)
        current_placements=current_plan_values['paragraph_placements']
        for invalid_placement_entries in (current_placements[:-1],current_placements+[current_placements[0]],[{**current_placements[0],'paragraph_id':'unknown'},*current_placements[1:]]):
            with self.assertRaisesRegex(ValueError,'문단 누락'):
                build_document_book(self.current_config_values,{**self.current_request_values,'paragraph_placements':invalid_placement_entries})
        (self.current_source_root/'world/first.md').write_text('변경된 원문')
        with self.assertRaisesRegex(ValueError,'원문 변경'):
            build_document_book(self.current_config_values,{**self.current_request_values,'paragraph_placements':current_placements})

    def test_preserves_crlf_and_reference_style_links(self):
        current_source_text='# 원문\r\n\r\n[주민][people]\r\n\r\n[people]: second.md#주민\r\n'
        (self.current_source_root/'world/first.md').write_bytes(current_source_text.encode())
        current_plan_values=plan_document_book(self.current_config_values,self.current_request_values)
        current_original_text=''.join(current_paragraph_entry['paragraph_text'] for current_paragraph_entry in current_plan_values['paragraph_entries'] if current_paragraph_entry['source_document_path']=='world/first.md')
        self.assertEqual(current_original_text,current_source_text)
        current_manifest_values=build_document_book(self.current_config_values,self.current_request_values)
        current_html_text=read_book_artifact(self.current_config_values,current_manifest_values['book_id'],'book.html').decode()
        self.assertIn('href="#paragraph-',current_html_text)
        self.assertFalse(list_document_books(self.current_config_values)['book_entries'][0]['source_changed_flag'])

    def test_rejects_traversal_and_symlinks(self):
        for current_directory_path in ('../outside','/tmp','private/.state'):
            with self.assertRaises(ValueError):
                plan_document_book(self.current_config_values,{**self.current_request_values,'source_directory_paths':[current_directory_path]})
        (self.current_source_root/'linked').symlink_to(self.current_source_root/'world',target_is_directory=True)
        with self.assertRaises(ValueError):
            plan_document_book(self.current_config_values,{**self.current_request_values,'source_directory_paths':['linked']})
        with self.assertRaises(ValueError):
            read_book_artifact(self.current_config_values,'../world','first.md')

    def test_deduplicates_overlapping_directories_and_marks_stale(self):
        current_request_values={**self.current_request_values,'source_directory_paths':['.','world']}
        current_plan_values=plan_document_book(self.current_config_values,current_request_values)
        self.assertEqual(current_plan_values['source_count'],3)
        build_document_book(self.current_config_values,current_request_values)
        self.assertFalse(list_document_books(self.current_config_values)['book_entries'][0]['source_changed_flag'])
        (self.current_source_root/'world/new.md').write_text('# 추가 문서\n')
        self.assertTrue(list_document_books(self.current_config_values)['book_entries'][0]['source_changed_flag'])


if __name__=='__main__':
    unittest.main()
