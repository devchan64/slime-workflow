"""두 도서의 고정 선택·루트 확장·경로 경계와 편집 범위를 검증한다."""
from pathlib import Path
import tempfile
import unittest
from generators.worldbuilding.book_collections import load_document_collections,update_document_collection,resolve_collection_request
from generators.worldbuilding.bookbinding import plan_document_book,build_document_book,list_document_books
from generators.worldbuilding.reorganization import preview_document_reorganization,execute_document_reorganization


class DocumentCollectionTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle=tempfile.TemporaryDirectory()
        self.current_source_root=Path(self.current_temp_handle.name)/'docs'
        self.current_state_root=Path(self.current_temp_handle.name)/'state'
        self.current_state_root.mkdir()
        for current_directory_path in ('world','gameplay','extra'):
            (self.current_source_root/current_directory_path).mkdir(parents=True)
            (self.current_source_root/current_directory_path/'guide.md').write_text('# 안내\n\n첫 문단.\n\n두 번째 문단.\n')
        self.current_config_values={'source_document_root':str(self.current_source_root),'private_state_root':str(self.current_state_root),'allowed_write_roots':['world'],'protected_document_paths':['world/rules.md'],'managed_catalog_path':''}

    def tearDown(self):
        self.current_temp_handle.cleanup()

    def test_fixed_two_collections_and_persistent_root_addition(self):
        current_collection_entries=load_document_collections(self.current_config_values)
        self.assertEqual([current_collection_entry['book_title_text'] for current_collection_entry in current_collection_entries],['세계관','시스템 설계'])
        self.assertEqual(current_collection_entries[1]['source_directory_paths'],['gameplay'])
        update_document_collection(self.current_config_values,{'collection_id':'world','source_directory_paths':['world','extra']})
        self.assertEqual(load_document_collections(self.current_config_values)[0]['source_directory_paths'],['world','extra'])
        update_document_collection(self.current_config_values,{'collection_id':'world','source_directory_paths':[]})
        self.assertTrue((self.current_source_root/'world/guide.md').exists())

    def test_rejects_unknown_overlap_traversal_and_stale_selection(self):
        for current_root_values in (['.'],['../outside'],['world','world'],['gameplay']):
            with self.assertRaises(Exception):
                update_document_collection(self.current_config_values,{'collection_id':'world','source_directory_paths':current_root_values})
        with self.assertRaises(Exception):
            update_document_collection(self.current_config_values,{'collection_id':'third','source_directory_paths':['extra']})
        update_document_collection(self.current_config_values,{'collection_id':'world','source_directory_paths':['world','extra']})
        with self.assertRaisesRegex(ValueError,'변경되었습니다'):
            resolve_collection_request(self.current_config_values,{'collection_id':'world','source_directory_paths':['world']})

    def test_system_document_move_is_scoped_to_selected_book(self):
        current_book_request={'collection_id':'system-design','book_title_text':'시스템 설계','source_directory_paths':['gameplay']}
        current_plan_values=plan_document_book(self.current_config_values,current_book_request)
        current_paragraph_entries=sorted(current_plan_values['paragraph_entries'],key=lambda current_paragraph_entry:current_paragraph_entry['source_start_line'])
        current_move_request={'collection_id':'system-design','source_directory_paths':['gameplay'],'paragraph_placements':[{'paragraph_id':current_paragraph_entry['paragraph_id'],'target_document_path':'gameplay/split.md' if current_paragraph_entry==current_paragraph_entries[-1] else current_paragraph_entry['source_document_path']} for current_paragraph_entry in current_paragraph_entries],'new_document_titles':{'gameplay/split.md':'분리한 설정'}}
        current_preview_values=preview_document_reorganization(self.current_config_values,current_move_request)
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'apply')
        self.assertTrue((self.current_source_root/'gameplay/split.md').exists())
        execute_document_reorganization(self.current_config_values,current_preview_values['reorganization_id'],'rollback')
        self.assertEqual(self.current_config_values['allowed_write_roots'],['world'])
        current_move_request['paragraph_placements'][-1]['target_document_path']='extra/split.md'
        current_move_request['new_document_titles']={'extra/split.md':'범위 밖'}
        with self.assertRaisesRegex(ValueError,'수정할 수 없는'):
            preview_document_reorganization(self.current_config_values,current_move_request)

    def test_edition_keeps_collection_identity_after_root_change(self):
        current_book_values=build_document_book(self.current_config_values,{'collection_id':'world','book_title_text':'세계관','source_directory_paths':['world']})
        self.assertEqual(current_book_values['collection_id'],'world')
        update_document_collection(self.current_config_values,{'collection_id':'world','source_directory_paths':['world','extra']})
        self.assertEqual(list_document_books(self.current_config_values)['book_entries'][0]['collection_id'],'world')
        self.assertTrue(list_document_books(self.current_config_values)['book_entries'][0]['collection_roots_changed_flag'])


if __name__=='__main__':
    unittest.main()
