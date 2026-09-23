"""작성·삭제의 원문 보존, 색인 갱신, 적용 계약을 검증한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,main
from unittest.mock import patch
import json
from jsonschema import Draft202012Validator,ValidationError
from generators.writer_agent.documents import (load_workspace_config,save_yaml_document,scan_workspace_documents,snapshot_document_hashes,chunk_document_blocks,resolve_document_path,parse_unique_json)
from generators.writer_agent.index import (learn_document_index,load_current_index,find_duplicate_candidates)
from generators.writer_agent.agent import (build_writing_proposal,build_duplicate_proposal,apply_reviewed_proposal,WRITER_OUTPUT_SCHEMA)
from generators.writer_agent.jobs import validate_job_request,resolve_job_directory

TEST_PARAGRAPH_TEXT='별빛 도서관은 항해 기록의 관측 시각과 장소를 확인한다. 사서는 두 관측자의 결과가 일치한 경우에만 정식 항로로 등록한다. 폭풍이 일어난 날의 기록은 검토함에 보관한다. 확인되지 않은 항로는 임시 표식을 붙여 정식 항로와 구분한다.'

def generate_test_vector(current_source_text):
    return [1.0]+[0.0]*1023

class WriterAgentContracts(TestCase):
    def setUp(self):
        self.temporary_root_handle=TemporaryDirectory()
        self.addCleanup(self.temporary_root_handle.cleanup)
        self.document_root_path=Path(self.temporary_root_handle.name)/'docs'
        (self.document_root_path/'world').mkdir(parents=True)
        (self.document_root_path/'ideas').mkdir()
        (self.document_root_path/'world/main.md').write_text('# 도서관 원본\n\n'+TEST_PARAGRAPH_TEXT+'\n')
        (self.document_root_path/'ideas/notes.md').write_text('# 도서관 메모\n\n'+TEST_PARAGRAPH_TEXT+'\n\n별도 고유 정보는 보존한다.\n')
        (self.document_root_path/'world/README.md').write_text('# 안내\n\n[원본](main.md)\n')
        (self.document_root_path/'CATALOG.md').write_text('# 전체 목록\n\n## 세계 (2)\n\n| 문서 | 경로 |\n|---|---|\n| [안내](world/README.md) | `world/README.md` |\n| [도서관 원본](world/main.md) | `world/main.md` |\n\n## 아이디어 (1)\n\n| 문서 | 경로 |\n|---|---|\n| [도서관 메모](ideas/notes.md) | `ideas/notes.md` |\n')
        self.workspace_config_path=Path(self.temporary_root_handle.name)/'config.yaml'
        self.workspace_config_values={'schema_version':1,'document_root':str(self.document_root_path),'state_root':str(Path(self.temporary_root_handle.name)/'state'),'write_roots':['world','ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':'CATALOG.md'}
        save_yaml_document(self.workspace_config_path,self.workspace_config_values)
        self.workspace_config_values=load_workspace_config(self.workspace_config_path)
        self.document_entry_lookup=scan_workspace_documents(self.workspace_config_values)
        self.document_chunk_entries=[current_chunk_entry for current_document_entry in self.document_entry_lookup.values() for current_chunk_entry in chunk_document_blocks(current_document_entry)]
        self.job_record_root=Path(self.workspace_config_values['state_root'])/'job'
        self.job_record_root.mkdir()

    def create_test_proposal(self,current_mode_name='append'):
        current_model_values={'mode':current_mode_name,'target_path':'world/main.md' if current_mode_name=='append' else 'world/new-topic.md','content':('## ' if current_mode_name=='append' else '# ')+'새 설정\n\n사서는 관측 기구를 수리하는 작은 작업대를 운영한다.','reason':'관련 원본과 같은 위치','source_ids':[self.document_chunk_entries[0]['id']],'warnings':[]}
        current_proposal_values=build_writing_proposal(self.workspace_config_values,self.document_entry_lookup,self.document_chunk_entries,current_model_values)
        current_proposal_values['snapshot_hashes']=snapshot_document_hashes(self.document_entry_lookup)
        return current_proposal_values

    def test_append_preserves_original(self):
        current_proposal_values=self.create_test_proposal()
        current_before_text=(self.document_root_path/'world/main.md').read_text()
        self.assertEqual((self.document_root_path/'world/main.md').read_text(),current_before_text)
        apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)
        self.assertTrue((self.document_root_path/'world/main.md').read_text().startswith(current_before_text))
        with self.assertRaises(ValueError):apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)

    def test_create_updates_catalog_and_preserves_existing_rows(self):
        current_proposal_values=self.create_test_proposal('create')
        self.assertEqual(len(current_proposal_values['changes']),2)
        apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)
        current_catalog_text=(self.document_root_path/'CATALOG.md').read_text()
        self.assertIn('## 세계 (3)',current_catalog_text)
        self.assertIn('world/new-topic.md',current_catalog_text)
        self.assertIn('ideas/notes.md',current_catalog_text)
        self.assertTrue((self.document_root_path/'world/new-topic.md').is_file())

    def test_stale_dependency_snapshot_rejects_apply(self):
        current_proposal_values=self.create_test_proposal()
        (self.document_root_path/'ideas/notes.md').write_text('# 변경\n\n[참조](../world/main.md)\n')
        with self.assertRaisesRegex(ValueError,'의존 관계'):apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)
        self.assertFalse((self.job_record_root/'application.yaml').exists())

    def test_failed_multi_file_apply_rolls_back(self):
        current_proposal_values=self.create_test_proposal('create')
        from generators.writer_agent.documents import write_atomic_bytes
        def fail_catalog_write(current_target_path,current_source_bytes):
            if current_target_path.name=='CATALOG.md':raise OSError('강제 쓰기 실패')
            write_atomic_bytes(current_target_path,current_source_bytes)
        with patch('generators.writer_agent.agent.write_atomic_bytes',side_effect=fail_catalog_write),self.assertRaises(OSError):
            apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)
        self.assertFalse((self.document_root_path/'world/new-topic.md').exists())
        self.assertIn('rolled_back',(self.job_record_root/'application.yaml').read_text())

    def test_catalog_tampering_rejected(self):
        current_proposal_values=self.create_test_proposal('create')
        current_proposal_values['changes'][1]['after']='arbitrary overwrite'
        with self.assertRaisesRegex(ValueError,'목록 갱신'):apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)

    def test_index_incremental_and_stale_policy(self):
        current_first_result=learn_document_index(self.workspace_config_values,generate_test_vector,lambda current_progress_values:None)
        with patch(__name__+'.generate_test_vector',side_effect=AssertionError('재임베딩 금지')):
            current_second_result=learn_document_index(self.workspace_config_values,generate_test_vector,lambda current_progress_values:None)
        self.assertEqual(current_first_result['chunks'],current_second_result['reused_chunks'])
        load_current_index(self.workspace_config_values)
        self.workspace_config_values['protected_paths']=['world']
        with self.assertRaisesRegex(ValueError,'색인 버전'):load_current_index(self.workspace_config_values)
        self.workspace_config_values['protected_paths']=[]
        (self.document_root_path/'ideas/new.md').write_text('# 새 문서\n')
        with self.assertRaisesRegex(ValueError,'오래되었습니다'):load_current_index(self.workspace_config_values)

    def test_weak_dependency_duplicate_only_and_unique_retention(self):
        for current_chunk_entry in self.document_chunk_entries:current_chunk_entry['vector']=generate_test_vector('')
        for current_chunk_entry in self.document_chunk_entries:
            if current_chunk_entry['path'].startswith('ideas/'):current_chunk_entry['vector']=[0.0,1.0]+[0.0]*1022
        current_candidate_pairs,current_coverage_values=find_duplicate_candidates(self.document_entry_lookup,self.document_chunk_entries)
        self.assertEqual(len(current_candidate_pairs),1)
        self.assertEqual(current_candidate_pairs[0]['keep']['path'],'world/main.md')
        self.assertEqual(current_candidate_pairs[0]['remove']['path'],'ideas/notes.md')
        current_verdict_values={'equivalent':True,'unique_information':False,'confidence':.99,'reason':'같은 모든 조건'}
        current_proposal_values=build_duplicate_proposal(self.document_entry_lookup,[(current_candidate_pairs[0],current_verdict_values)],current_coverage_values)
        self.assertNotIn(TEST_PARAGRAPH_TEXT,current_proposal_values['changes'][0]['after'])
        self.assertIn('별도 고유 정보',current_proposal_values['changes'][0]['after'])
        current_verdict_values['unique_information']=True
        self.assertEqual(build_duplicate_proposal(self.document_entry_lookup,[(current_candidate_pairs[0],current_verdict_values)],current_coverage_values)['changes'],[])

    def test_equal_dependency_different_documents_never_delete(self):
        for current_document_entry in self.document_entry_lookup.values():current_document_entry.update(title='동등 문서',incoming=0,writable=True)
        for current_chunk_entry in self.document_chunk_entries:current_chunk_entry.update(vector=generate_test_vector(''),heading='동등 절')
        self.assertEqual(find_duplicate_candidates(self.document_entry_lookup,self.document_chunk_entries)[0],[])

    def test_approved_blocks_and_links_are_not_removable(self):
        current_document_entry={'path':'ideas/extra.md','title':'제안','incoming':0,'writable':True,'text':'# 제안\n\n## 승인 기록\n\n'+TEST_PARAGRAPH_TEXT+'\n\n## 일반\n\n'+TEST_PARAGRAPH_TEXT+' [근거](../world/main.md)\n'}
        self.assertFalse(any(current_chunk_entry['removable'] for current_chunk_entry in chunk_document_blocks(current_document_entry)))

    def test_path_schema_and_model_override_rejected(self):
        for current_relative_path in ('../escape.md','/tmp/a.md','.hidden/a.md','world/../../x.md'):
            with self.assertRaises(ValueError):resolve_document_path(self.document_root_path,current_relative_path)
        (self.document_root_path/'world/escape.md').symlink_to('/tmp')
        with self.assertRaises(ValueError):resolve_document_path(self.document_root_path,'world/escape.md')
        with self.assertRaises(ValueError):validate_job_request({'mode':'write','prompt':'test','model':'injected'})
        with self.assertRaises(ValueError):parse_unique_json('{"mode":1,"mode":2}')
        with self.assertRaises(ValueError):parse_unique_json('{"value":NaN}')
        with self.assertRaises(ValueError):resolve_job_directory(self.workspace_config_values,'../escape')
        with self.assertRaises(ValidationError):Draft202012Validator(WRITER_OUTPUT_SCHEMA).validate({'mode':'append'})

if __name__=='__main__':main()
