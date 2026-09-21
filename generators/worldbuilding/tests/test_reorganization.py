"""원본 파일 분리·문단 이동의 보존, 충돌 감지와 트랜잭션 복구를 확인한다."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from generators.worldbuilding.bookbinding import plan_document_book
from generators.worldbuilding.reorganization import preview_document_reorganization,execute_document_reorganization
from generators.worldbuilding import documents


class DocumentReorganizationTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle=tempfile.TemporaryDirectory()
        self.current_source_root=Path(self.current_temp_handle.name)/'docs'
        (self.current_source_root/'world').mkdir(parents=True)
        self.current_state_root=Path(self.current_temp_handle.name)/'state'
        self.current_state_root.mkdir()
        self.current_config_values={'source_document_root':str(self.current_source_root),'private_state_root':str(self.current_state_root),'allowed_write_roots':['world'],'protected_document_paths':['world/rules.md'],'managed_catalog_path':''}
        self.current_source_texts={'world/first.md':'# 첫 문서\r\n\r\n남길 문단.\r\n\r\n## 이동할 절\r\n\r\n원문을 그대로 이동한다.\r\n','world/second.md':'# 두 번째 문서\n\n기존 내용.\n','world/rules.md':'# 보호 기준\n\n변경 금지.\n'}
        for current_source_path,current_source_text in self.current_source_texts.items():
            (self.current_source_root/current_source_path).write_bytes(current_source_text.encode())
        self.current_plan_values=plan_document_book(self.current_config_values,{'book_title_text':'구조 편집','source_directory_paths':['world']})
        self.current_paragraph_entries=sorted(self.current_plan_values['paragraph_entries'],key=lambda current_paragraph_entry:(current_paragraph_entry['source_document_path'],current_paragraph_entry['source_start_line']))
        self.current_request_values={'source_directory_paths':['world'],'paragraph_placements':[{'paragraph_id':current_paragraph_entry['paragraph_id'],'target_document_path':current_paragraph_entry['source_document_path']} for current_paragraph_entry in self.current_paragraph_entries],'new_document_titles':{}}

    def tearDown(self):
        self.current_temp_handle.cleanup()

    def move_source_paragraphs(self,current_target_path):
        current_move_ids={current_paragraph_entry['paragraph_id'] for current_paragraph_entry in self.current_paragraph_entries if current_paragraph_entry['source_document_path']=='world/first.md' and current_paragraph_entry['source_start_line']>=5}
        for current_placement_entry in self.current_request_values['paragraph_placements']:
            if current_placement_entry['paragraph_id'] in current_move_ids:
                current_placement_entry['target_document_path']=current_target_path
        self.current_request_values['paragraph_placements'].sort(key=lambda current_placement_entry:current_placement_entry['paragraph_id'] in current_move_ids)

    def test_split_preserves_crlf_and_rollback_restores_exact_bytes(self):
        self.move_source_paragraphs('world/new.md')
        self.current_request_values['new_document_titles']={'world/new.md':'새 파일'}
        current_preview_values=preview_document_reorganization(self.current_config_values,self.current_request_values)
        self.assertFalse((self.current_source_root/'world/new.md').exists())
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        self.assertEqual((self.current_source_root/'world/first.md').read_bytes().decode(),'# 첫 문서\r\n\r\n남길 문단.\r\n\r\n')
        self.assertIn('## 이동할 절\r\n\r\n원문을 그대로 이동한다.\r\n',(self.current_source_root/'world/new.md').read_bytes().decode())
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'rollback')
        self.assertFalse((self.current_source_root/'world/new.md').exists())
        for current_source_path,current_source_text in self.current_source_texts.items():
            self.assertEqual((self.current_source_root/current_source_path).read_bytes().decode(),current_source_text)

    def test_moves_between_existing_files_and_rejects_repeat_apply(self):
        self.move_source_paragraphs('world/second.md')
        current_preview_values=preview_document_reorganization(self.current_config_values,self.current_request_values)
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        self.assertIn('원문을 그대로 이동한다.',(self.current_source_root/'world/second.md').read_text())
        with self.assertRaisesRegex(ValueError,'이미 처리'):
            execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')

    def test_stale_preview_and_external_edit_block_apply_and_rollback(self):
        self.move_source_paragraphs('world/second.md')
        current_preview_values=preview_document_reorganization(self.current_config_values,self.current_request_values)
        (self.current_source_root/'world/unrelated.md').write_text('# 외부 변경\n')
        with self.assertRaisesRegex(ValueError,'원문이 변경'):
            execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        (self.current_source_root/'world/unrelated.md').unlink()
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        (self.current_source_root/'world/second.md').write_text('# 사용자 편집\n')
        with self.assertRaisesRegex(ValueError,'외부 수정'):
            execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'rollback')
        self.assertEqual((self.current_source_root/'world/second.md').read_text(),'# 사용자 편집\n')

    def test_rejects_missing_duplicate_protected_and_outside_paths(self):
        self.move_source_paragraphs('world/rules.md')
        with self.assertRaisesRegex(ValueError,'수정할 수 없는'):
            preview_document_reorganization(self.current_config_values,self.current_request_values)
        self.current_request_values['paragraph_placements'].append(self.current_request_values['paragraph_placements'][0])
        with self.assertRaisesRegex(ValueError,'누락·중복'):
            preview_document_reorganization(self.current_config_values,self.current_request_values)
        self.current_request_values['paragraph_placements'].pop()
        self.current_request_values['paragraph_placements'][0]['target_document_path']='../outside.md'
        with self.assertRaises(ValueError):
            preview_document_reorganization(self.current_config_values,self.current_request_values)

    def test_rejects_breaking_incoming_anchor(self):
        (self.current_source_root/'outside.md').write_text('# 참조\n\n[절](world/first.md#이동할-절)\n')
        self.move_source_paragraphs('world/second.md')
        with self.assertRaisesRegex(ValueError,'링크가 끊어'):
            preview_document_reorganization(self.current_config_values,self.current_request_values)

    def test_failure_during_write_restores_prior_files(self):
        self.move_source_paragraphs('world/second.md')
        current_preview_values=preview_document_reorganization(self.current_config_values,self.current_request_values)
        original_write_function=documents.write_atomic_document
        def fail_second_document(current_target_path,current_document_text):
            if current_target_path==self.current_source_root/'world/second.md':
                raise OSError('합성 쓰기 실패')
            original_write_function(current_target_path,current_document_text)
        with patch.object(documents,'write_atomic_document',side_effect=fail_second_document):
            with self.assertRaisesRegex(OSError,'합성 쓰기 실패'):
                execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        for current_source_path,current_source_text in self.current_source_texts.items():
            self.assertEqual((self.current_source_root/current_source_path).read_bytes().decode(),current_source_text)


if __name__=='__main__':
    unittest.main()
