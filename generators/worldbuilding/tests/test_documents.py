"""문서 승계·입력 경계·동시 수정·복구를 합성 자료로 검증한다."""
import copy
from pathlib import Path
import tempfile
import unittest

from generators.worldbuilding.documents import (load_yaml_document,parse_unique_json,load_workspace_config,save_yaml_document,scan_source_documents,build_inherited_context,validate_change_bundle,apply_document_changes,rollback_document_changes,include_catalog_changes,calculate_text_digest,resolve_document_path)


class WorldbuildingDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temporary_workspace_handle=tempfile.TemporaryDirectory()
        self.source_document_root=Path(self.temporary_workspace_handle.name)/'docs'
        self.source_document_root.mkdir()
        (self.source_document_root/'world').mkdir()
        (self.source_document_root/'world/README.md').write_text('# 세계관\n은빛 도시는 길드가 운영한다. 왕은 없다.\n')
        (self.source_document_root/'world/cities.md').write_text('# 도시 설정\n은빛 도시는 항구다.\n새벽 도시는 산악 도시다.\n')
        (self.source_document_root/'APPROVAL.md').write_text('# 승인\n기존 두 도시만 확정이다.\n')
        (self.source_document_root/'CATALOG.md').write_text('# 목록\n\n## 세계관 (2)\n\n| 문서 | 경로 |\n|---|---|\n| [세계관](world/README.md) | `world/README.md` |\n| [도시 설정](world/cities.md) | `world/cities.md` |\n')
        self.workspace_config_path=Path(self.temporary_workspace_handle.name)/'workspace.yaml'
        save_yaml_document(self.workspace_config_path,{'workspace_schema_version':1,'source_document_root':str(self.source_document_root),'private_state_root':str(Path(self.temporary_workspace_handle.name)/'state'),'allowed_write_roots':['world'],'required_source_paths':['world/README.md','APPROVAL.md'],'protected_document_paths':['APPROVAL.md','CATALOG.md'],'managed_catalog_path':'CATALOG.md'})
        self.workspace_config_values=load_workspace_config(self.workspace_config_path)
        self.current_request_values={'requested_instruction_text':'기존 도시 설정을 참고하여 새로운 도시를 정의해줘','requested_operation_mode':'create','requested_target_path':''}
        self.source_document_entries=scan_source_documents(self.workspace_config_values)
        self.selected_chunk_entries=build_inherited_context(self.workspace_config_values,self.current_request_values,self.source_document_entries)
        self.current_result_values={'result_summary_text':'도시 후보 작성','source_reference_ids':[self.selected_chunk_entries[0]['source_reference_id']],'quality_warnings':[],'document_change_entries':[{'document_relative_path':'world/new-city.md','document_change_mode':'create','existing_fragment_text':'','replacement_fragment_text':'# 새 도시\n\n상태: 신규 제안\n기존 항구 도시와 교역하는 도시다.\n'}]}
        self.current_run_root=Path(self.workspace_config_values['private_state_root'])/'run'
        self.current_run_root.mkdir()

    def tearDown(self):
        self.temporary_workspace_handle.cleanup()

    def validate_current_result(self):
        return validate_change_bundle(self.workspace_config_values,self.current_request_values,self.current_result_values,self.source_document_entries,self.selected_chunk_entries)

    def test_inherits_relevant_city_sources(self):
        self.assertIn('world/cities.md',[current_chunk_entry['source_document_path'] for current_chunk_entry in self.selected_chunk_entries])
        self.assertTrue(all(current_chunk_entry['source_content_hash'] for current_chunk_entry in self.selected_chunk_entries))

    def test_rejects_unknown_model_request_field(self):
        self.current_request_values['model']='remote-model'
        with self.assertRaises(Exception):
            build_inherited_context(self.workspace_config_values,self.current_request_values,self.source_document_entries)

    def test_rejects_duplicate_yaml_keys(self):
        invalid_yaml_path=self.current_run_root/'bad.yaml'
        invalid_yaml_path.write_text('name: first\nname: second\n')
        with self.assertRaises(ValueError):
            load_yaml_document(invalid_yaml_path)

    def test_rejects_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            parse_unique_json('{"name":1,"name":2}')

    def test_rejects_unseen_citation(self):
        self.current_result_values['source_reference_ids']=['invented:1-2']
        with self.assertRaises(ValueError):
            self.validate_current_result()

    def test_rejects_path_escape(self):
        self.current_result_values['document_change_entries'][0]['document_relative_path']='../outside.md'
        with self.assertRaises(ValueError):
            self.validate_current_result()

    def test_rejects_symlink_escape(self):
        (self.source_document_root/'world/link').symlink_to(self.current_run_root,target_is_directory=True)
        with self.assertRaises(ValueError):
            resolve_document_path(self.source_document_root,'world/link/doc.md')

    def test_rejects_existing_file_create(self):
        self.current_result_values['document_change_entries'][0]['document_relative_path']='world/cities.md'
        with self.assertRaises(ValueError):
            self.validate_current_result()

    def test_rejects_missing_proposal_status(self):
        self.current_result_values['document_change_entries'][0]['replacement_fragment_text']='# 도시\n확정 설정이다.'
        with self.assertRaises(ValueError):
            self.validate_current_result()

    def test_preserves_original_when_appending(self):
        self.current_request_values.update(requested_operation_mode='append',requested_target_path='world/cities.md')
        self.current_result_values['document_change_entries'][0].update(document_relative_path='world/cities.md',document_change_mode='append',replacement_fragment_text='## 추가 제안\n상태: 신규 제안\n항구의 축제 이야기.')
        planned_change_entries=self.validate_current_result()
        self.assertTrue(planned_change_entries[0]['next_document_text'].startswith(self.source_document_entries['world/cities.md']['source_document_body']))

    def test_rejects_ambiguous_fragment_replace(self):
        self.current_request_values.update(requested_operation_mode='replace',requested_target_path='world/cities.md')
        self.current_result_values['document_change_entries'][0].update(document_relative_path='world/cities.md',document_change_mode='replace',existing_fragment_text='도시',replacement_fragment_text='마을')
        with self.assertRaises(ValueError):
            self.validate_current_result()

    def test_detects_changed_target_before_apply(self):
        planned_change_entries=self.validate_current_result()
        (self.source_document_root/'world/new-city.md').write_text('# 사용자의 새 글\n')
        with self.assertRaises(ValueError):
            apply_document_changes(self.workspace_config_values,self.current_run_root,planned_change_entries)
        self.assertEqual((self.source_document_root/'world/new-city.md').read_text(),'# 사용자의 새 글\n')

    def test_applies_catalog_and_rolls_back(self):
        planned_change_entries=include_catalog_changes(self.workspace_config_values,self.source_document_entries,self.validate_current_result())
        apply_document_changes(self.workspace_config_values,self.current_run_root,planned_change_entries)
        self.assertIn('world/new-city.md',(self.source_document_root/'CATALOG.md').read_text())
        self.assertIn('세계관 (3)',(self.source_document_root/'CATALOG.md').read_text())
        rollback_document_changes(self.workspace_config_values,self.current_run_root)
        self.assertFalse((self.source_document_root/'world/new-city.md').exists())
        self.assertEqual((self.source_document_root/'CATALOG.md').read_text(),self.source_document_entries['CATALOG.md']['source_document_body'])

    def test_refuses_rollback_over_external_edit(self):
        apply_document_changes(self.workspace_config_values,self.current_run_root,self.validate_current_result())
        (self.source_document_root/'world/new-city.md').write_text('# 사용자 후속 수정\n')
        with self.assertRaises(ValueError):
            rollback_document_changes(self.workspace_config_values,self.current_run_root)

    def test_ignores_private_state_documents(self):
        private_state_root=self.source_document_root/'world/.runtime'
        private_state_root.mkdir()
        (private_state_root/'private.md').write_text('# 실행 기록\n')
        self.assertNotIn('world/.runtime/private.md',scan_source_documents(self.workspace_config_values))


if __name__=='__main__':
    unittest.main()
