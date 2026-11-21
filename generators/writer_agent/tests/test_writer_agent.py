"""작성·삭제의 원문 보존, 색인 갱신, 적용 계약을 검증한다."""
from pathlib import Path
from io import BytesIO
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest import TestCase,main
from unittest.mock import patch
import json
from jsonschema import Draft202012Validator,ValidationError
from generators.writer_agent.documents import (load_workspace_config,save_yaml_document,scan_workspace_documents,snapshot_document_hashes,chunk_document_blocks,resolve_document_path,parse_unique_json)
from generators.writer_agent.management import WriterAgentManager
from generators.writer_agent.documents import calculate_content_hash
from generators.writer_agent.index import (learn_document_index,load_current_index,find_duplicate_candidates)
from generators.writer_agent.agent import (build_writing_proposal,inspect_writer_draft,apply_writer_review,build_duplicate_proposal,apply_reviewed_proposal,WRITER_OUTPUT_SCHEMA,collect_writing_context)
from generators.writer_agent.jobs import validate_job_request,resolve_job_directory,create_writer_job,update_job_status,generate_reviewed_writer_result

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

    def test_legacy_cuda_manifest_does_not_mark_runtime_ready(self):
        from generators.writer_agent import prepare
        current_install_root = Path(self.temporary_root_handle.name)/'runtime'
        current_install_root.mkdir()
        (current_install_root/'prepared.json').write_text(json.dumps({'server_binary_sha256':'legacy'}))
        with patch.object(prepare, 'RUNTIME_INSTALL_ROOT', current_install_root):
            current_manager_service = WriterAgentManager(self.workspace_config_path)
            self.assertFalse(current_manager_service.read_workspace_state()['ready'])

    def test_embedding_precision_change_rebuilds_without_reusing_vectors(self):
        import sqlite3
        from generators.writer_agent.index import PREVIOUS_INDEX_SCHEMA_VERSION
        current_first_result = learn_document_index(self.workspace_config_values, generate_test_vector, lambda current_progress_values: None)
        with sqlite3.connect(current_first_result['index_path']) as current_database_handle:
            current_database_handle.execute('UPDATE metadata SET value=? WHERE key=?', (PREVIOUS_INDEX_SCHEMA_VERSION, 'version'))
        with self.assertRaisesRegex(ValueError, '색인'):
            load_current_index(self.workspace_config_values)
        current_second_result = learn_document_index(self.workspace_config_values, generate_test_vector, lambda current_progress_values: None)
        self.assertGreater(current_second_result['chunks'], 0)
        self.assertEqual(current_second_result['reused_chunks'], 0)
        load_current_index(self.workspace_config_values)

    def create_test_proposal(self,current_mode_name='append'):
        current_model_values={'target_path':'world/main.md' if current_mode_name=='append' else 'world/new-topic.md','heading':'새 설정','paragraphs':['사서는 관측 기구를 수리하는 작은 작업대를 운영한다.'],'reason':'관련 원본과 같은 위치','source_ids':[self.document_chunk_entries[0]['id']],'warnings':[]}
        current_proposal_values=build_writing_proposal(self.workspace_config_values,self.document_entry_lookup,self.document_chunk_entries,current_model_values)
        current_proposal_values['snapshot_hashes']=snapshot_document_hashes(self.document_entry_lookup)
        return current_proposal_values

    def test_context_marks_protected_sources_read_only(self):
        current_context_entries=collect_writing_context(self.document_entry_lookup,self.document_chunk_entries,self.document_chunk_entries)
        for current_chunk_entry in current_context_entries:
            self.assertEqual(current_chunk_entry['can_append'],current_chunk_entry['path'] not in {'CATALOG.md','world/README.md'})

    def test_context_includes_document_opening_for_status(self):
        current_document_chunks=sorted((current_entry for current_entry in self.document_chunk_entries if current_entry['path']=='world/main.md'),key=lambda current_entry:current_entry['start'])
        current_selected_entries=collect_writing_context(self.document_entry_lookup,self.document_chunk_entries,[current_document_chunks[-1]])
        self.assertIn(current_document_chunks[0]['id'],[current_entry['id'] for current_entry in current_selected_entries])

    def test_structured_paragraph_contract(self):
        current_model_values={'target_path':'world/main.md','heading':'새 절','paragraphs':['첫 문단','둘째 문단'],'reason':'근거','source_ids':[self.document_chunk_entries[0]['id']],'warnings':[]}
        Draft202012Validator(WRITER_OUTPUT_SCHEMA).validate(current_model_values)
        current_proposal_values=build_writing_proposal(self.workspace_config_values,self.document_entry_lookup,self.document_chunk_entries,current_model_values)
        self.assertIn('## 새 절\n\n첫 문단\n\n둘째 문단\n',current_proposal_values['changes'][0]['after'])
        for current_invalid_text in ('[링크](bad.md)','줄바꿈\n본문','큰"따옴표','역'+chr(92)+'슬래시'):
            current_model_values['paragraphs']=[current_invalid_text]
            with self.assertRaises(ValidationError):Draft202012Validator(WRITER_OUTPUT_SCHEMA).validate(current_model_values)

    def test_review_blocks_unsupported_proposal(self):
        current_proposal_values=self.create_test_proposal()
        current_review_values={'approved':False,'issues':['서로 다른 요청을 구분하지 못하는 식별자']}
        current_reviewed_proposal=apply_writer_review(current_proposal_values,current_review_values)
        self.assertEqual(current_reviewed_proposal['changes'],[])
        self.assertIn('서로 다른 요청을 구분하지 못하는 식별자',current_reviewed_proposal['warnings'])
        self.assertTrue(current_reviewed_proposal['evidence'])

    def test_unsupported_status_and_id_combination_are_flagged(self):
        current_model_result={'heading':'납품','reason':'미확정 제안','paragraphs':['시즌 ID와 개인 인증자를 결합한 식별자를 쓰고 CLAIMED 상태로 기록한다.']}
        current_issue_values=inspect_writer_draft(current_model_result,[{'text':'납품은 미확정 제안이다.'}])
        self.assertTrue(any('CLAIMED' in current_issue for current_issue in current_issue_values))
        self.assertTrue(any('식별자 조합' in current_issue for current_issue in current_issue_values))
        current_model_result['paragraphs']=['시즌 경계에서 재전송이 거부되는지 확인한다.']
        self.assertTrue(any('재전송' in current_issue for current_issue in inspect_writer_draft(current_model_result,[{'text':'재요청 시 기존 결과를 확인한다.'}])))

    def test_rejected_draft_is_revised_and_reviewed_once(self):
        current_draft_values={'target_path':'world/main.md','paragraphs':['초안']}
        current_revised_values={'target_path':'world/main.md','paragraphs':['수정안']}
        current_model_input={'instruction':'검토','sources':[],'folders':['world']}
        current_request_calls=[]
        current_responses=iter([current_draft_values,{'approved':False,'issues':['원문 상태 확인']},current_revised_values,{'approved':True,'issues':[]}])
        def request_test_result(*current_request_values):
            current_request_calls.append(current_request_values)
            return next(current_responses)
        current_result_values,current_review_values=generate_reviewed_writer_result(current_model_input,{},self.job_record_root,request_test_result)
        self.assertEqual(current_result_values,current_revised_values)
        self.assertTrue(current_review_values['approved'])
        self.assertEqual(current_request_calls[2][1]['review_feedback'],['원문 상태 확인'])
        self.assertTrue((self.job_record_root/'writing-review-1.yaml').is_file())
        self.assertTrue((self.job_record_root/'writing-review-2.yaml').is_file())

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

    def test_apply_api_rejects_stale_hash_and_replay(self):
        current_job_identifier=create_writer_job(self.workspace_config_values,{'mode':'write','prompt':'새 절 추가'})
        current_job_root=resolve_job_directory(self.workspace_config_values,current_job_identifier)
        save_yaml_document(current_job_root/'proposal.yaml',self.create_test_proposal())
        current_proposal_hash=calculate_content_hash((current_job_root/'proposal.yaml').read_bytes())
        update_job_status(current_job_root,'review',proposal_hash=current_proposal_hash)
        current_manager_service=WriterAgentManager(self.workspace_config_path)
        for current_hash_value,current_expected_status in [('wrong',400),(current_proposal_hash,200),(current_proposal_hash,400)]:
            current_body_bytes=json.dumps({'id':current_job_identifier,'proposal_hash':current_hash_value}).encode()
            current_http_handler=SimpleNamespace(path='/writer-agent/api/apply',command='POST',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','X-Writer-Token':current_manager_service.csrf_token_value,'Content-Type':'application/json','Content-Length':str(len(current_body_bytes))},server=SimpleNamespace(server_port=8770),rfile=BytesIO(current_body_bytes),wfile=BytesIO(),status_code=None)
            current_http_handler.send_response=lambda current_status_code:setattr(current_http_handler,'status_code',current_status_code)
            current_http_handler.send_header=lambda current_header_name,current_header_value:None
            current_http_handler.end_headers=lambda:None
            current_manager_service.handle_writer_request(current_http_handler)
            self.assertEqual(current_http_handler.status_code,current_expected_status,current_http_handler.wfile.getvalue())
        self.assertEqual((self.document_root_path/'world/main.md').read_text().count('## 새 설정'),1)

    def test_stale_dependency_snapshot_rejects_apply(self):
        current_proposal_values=self.create_test_proposal()
        (self.document_root_path/'ideas/notes.md').write_text('# 변경\n\n[참조](../world/main.md)\n')
        with self.assertRaisesRegex(ValueError,'의존 관계'):apply_reviewed_proposal(self.workspace_config_values,self.job_record_root,current_proposal_values)
        self.assertFalse((self.job_record_root/'application.yaml').exists())

    def test_hermes_gateway_applies_only_reviewed_isolated_document(self):
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from tools.management.common.management_gateway import ManagementCommandGateway,execute_management_command
        from tools.management.gateway_server import create_gateway_request_handler
        from tools.management.domains.hermes_agent.service import HermesServiceManager
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_root_path=Path(self.temporary_root_handle.name)
        current_job_identifier=create_writer_job(self.workspace_config_values,{'mode':'write','prompt':'격리 제안'})
        current_job_root=resolve_job_directory(self.workspace_config_values,current_job_identifier)
        save_yaml_document(current_job_root/'proposal.yaml',self.create_test_proposal())
        current_proposal_hash=calculate_content_hash((current_job_root/'proposal.yaml').read_bytes())
        update_job_status(current_job_root,'review',proposal_hash=current_proposal_hash)
        current_store_value=HermesDelegationStore(current_root_path/'receipts')
        current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{'mode':'write','prompt':'격리 제안'},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
        current_writer_service=WriterAgentManager(self.workspace_config_path)
        current_hermes_service=HermesServiceManager(current_root_path/'hermes-jobs',current_root_path/'hermes-sessions')
        current_gateway_value=ManagementCommandGateway({'writer-agent':current_writer_service.handle_writer_request,'hermes-agent':current_hermes_service.handle_hermes_request})
        current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
        current_server_value.emit_gateway_trace=lambda *current_values:None
        current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_thread_value.start()
        current_address_value=f'http://127.0.0.1:{current_server_value.server_port}'
        try:
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_address_value}), patch('tools.management.domains.hermes_agent.writer_operations.HermesDelegationStore',return_value=current_store_value):
                current_review_value=execute_management_command('hermes-agent','hermes-writer-status',{'request_id':'writer_request_123'},current_address_value)
                self.assertEqual(current_review_value['job']['stage'],'review')
                self.assertFalse(current_review_value['job']['truncated'])
                current_apply_request={'request_id':'writer_apply_123','writer_request_id':'writer_request_123','job_id':current_job_identifier,'proposal_hash':current_proposal_hash}
                current_apply_result=execute_management_command('hermes-agent','hermes-writer-apply',current_apply_request,current_address_value)
                self.assertEqual(current_apply_result['state'],'completed')
                self.assertFalse(current_apply_result['duplicate'])
                self.assertTrue(execute_management_command('hermes-agent','hermes-writer-apply',current_apply_request,current_address_value)['duplicate'])
                self.assertEqual(execute_management_command('hermes-agent','hermes-writer-apply-status',{'request_id':'writer_apply_123'},current_address_value)['state'],'completed')
                self.assertEqual(execute_management_command('hermes-agent','hermes-writer-apply-history',{},current_address_value)['records'][0]['job_id'],current_job_identifier)
            self.assertEqual((self.document_root_path/'world/main.md').read_text().count('## 새 설정'),1)
        finally:
            current_server_value.shutdown()
            current_thread_value.join(timeout=5)
            current_server_value.server_close()

    def test_shared_gateway_applies_and_reads_same_saved_record(self):
        from tools.management.common.management_gateway import ManagementCommandGateway
        current_job_identifier=create_writer_job(self.workspace_config_values,{'mode':'write','prompt':'격리 적용'})
        current_job_root=resolve_job_directory(self.workspace_config_values,current_job_identifier)
        save_yaml_document(current_job_root/'proposal.yaml',self.create_test_proposal())
        current_proposal_hash=calculate_content_hash((current_job_root/'proposal.yaml').read_bytes())
        update_job_status(current_job_root,'review',proposal_hash=current_proposal_hash)
        current_manager_service=WriterAgentManager(self.workspace_config_path)
        current_gateway_service=ManagementCommandGateway({'writer-agent':current_manager_service.handle_writer_request})
        for current_command_name,current_request_payload,current_expected_status in (
            ('writer-apply',{'id':current_job_identifier,'proposal_hash':'stale'},400),
            ('writer-apply',{'id':current_job_identifier,'proposal_hash':current_proposal_hash},200),
            ('writer-detail',{'id':current_job_identifier},200),
            ('writer-apply',{'id':current_job_identifier,'proposal_hash':current_proposal_hash},400),
        ):
            current_body_bytes=json.dumps({'service':'writer-agent','command':current_command_name,'payload':current_request_payload}).encode()
            current_http_handler=SimpleNamespace(path='/management/command',command='POST',headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','X-Writer-Token':current_manager_service.csrf_token_value,'Content-Type':'application/json','Content-Length':str(len(current_body_bytes))},server=SimpleNamespace(server_port=8770),rfile=BytesIO(current_body_bytes),wfile=BytesIO(),status_code=None)
            current_http_handler.send_response=lambda current_status_code:setattr(current_http_handler,'status_code',current_status_code)
            current_http_handler.send_header=lambda current_header_name,current_header_value:None
            current_http_handler.end_headers=lambda:None
            current_gateway_service.handle(current_http_handler)
            self.assertEqual(current_http_handler.status_code,current_expected_status,current_http_handler.wfile.getvalue())
            if current_command_name=='writer-detail':
                current_detail_record=json.loads(current_http_handler.wfile.getvalue())
                self.assertEqual(current_detail_record['status']['stage'],'applied')
                self.assertEqual(current_detail_record['application']['status'],'applied')
                self.assertEqual(current_detail_record['id'],current_job_identifier)
        self.assertEqual((self.document_root_path/'world/main.md').read_text().count('## 새 설정'),1)

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

class WriterRuntimePreparationTest(TestCase):
    def test_uses_workflow_uv_when_missing_from_path(self):
        from generators.writer_agent import prepare
        with TemporaryDirectory() as current_directory_name:
            current_test_root=Path(current_directory_name)
            current_uv_path=current_test_root/'.venv/bin/uv'
            current_uv_path.parent.mkdir(parents=True)
            current_uv_path.write_text('')
            current_uv_path.chmod(0o755)
            current_hip_path=current_test_root/'rocm/bin/hipcc'
            current_hip_path.parent.mkdir(parents=True)
            current_hip_path.touch()
            current_python_path=current_test_root/'runtime/venv/bin/python'
            current_python_path.parent.mkdir(parents=True)
            current_python_path.touch()
            with patch.object(prepare,'WORKFLOW_REPOSITORY_ROOT',current_test_root), patch.object(prepare,'RUNTIME_PYTHON_PATH',current_python_path), patch.object(prepare,'inspect_gpu_environment',return_value='gfx1151'), patch.object(prepare.shutil,'which',side_effect=lambda current_name: '/usr/bin/g++' if current_name=='g++' else None), patch.dict(prepare.os.environ,{'ROCM_PATH':str(current_test_root/'rocm')}), patch.object(prepare,'execute_logged_command',side_effect=RuntimeError('검증 중단')) as current_command_mock:
                with self.assertRaisesRegex(RuntimeError,'검증 중단'):
                    prepare.prepare_runtime_environment()
            self.assertEqual(current_command_mock.call_args.args[0][0],str(current_uv_path))

if __name__=='__main__':main()
