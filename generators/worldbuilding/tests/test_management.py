"""관리 API의 입력 경계와 지속 큐를 검증한다."""
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generators.worldbuilding.documents import save_yaml_document
from generators.worldbuilding.management import WorldbuildingManagement


class ManagementRequestStub:
    def __init__(self,current_request_path,current_request_method,current_header_values,current_body_values):
        self.path=current_request_path
        self.command=current_request_method
        self.headers=current_header_values
        self.server=type('Server',(),{'server_port':8770})()
        self.rfile=BytesIO(json.dumps(current_body_values).encode())
        self.wfile=BytesIO()
        self.response_status_code=None
    def send_response(self,current_response_code):
        self.response_status_code=current_response_code
    def send_error(self,current_response_code,*current_error_values):
        self.response_status_code=current_response_code
    def send_header(self,*current_header_values):
        pass
    def end_headers(self):
        pass


class WorldbuildingManagementTests(unittest.TestCase):
    def setUp(self):
        self.temporary_workspace_handle=tempfile.TemporaryDirectory()
        self.current_source_root=Path(self.temporary_workspace_handle.name)/'docs'
        self.current_source_root.mkdir()
        (self.current_source_root/'world').mkdir()
        (self.current_source_root/'world/README.md').write_text('# 합성 세계관\n')
        self.current_config_path=Path(self.temporary_workspace_handle.name)/'config.yaml'
        save_yaml_document(self.current_config_path,{'workspace_schema_version':1,'source_document_root':str(self.current_source_root),'private_state_root':str(Path(self.temporary_workspace_handle.name)/'state'),'allowed_write_roots':['world'],'required_source_paths':['world/README.md'],'protected_document_paths':['world/README.md'],'managed_catalog_path':''})
        with patch.object(WorldbuildingManagement,'process_pending_jobs'):
            self.current_service_handle=WorldbuildingManagement(self.current_config_path)
        self.current_request_values={'requested_instruction_text':'새로운 도시 설정을 작성해줘','requested_operation_mode':'create','requested_target_path':''}

    def tearDown(self):
        self.current_service_handle.close_management_worker()
        self.temporary_workspace_handle.cleanup()

    def build_http_request(self,current_token_text,current_origin_text='http://127.0.0.1:8770',current_host_text='127.0.0.1:8770'):
        return ManagementRequestStub('/worldbuilding/api/tasks','POST',{'Host':current_host_text,'Origin':current_origin_text,'X-Worldbuilding-Token':current_token_text,'Content-Length':str(len(json.dumps(self.current_request_values).encode()))},self.current_request_values)

    def test_rejects_cross_origin_submission(self):
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token,'https://outside.example')
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,400)
        self.assertEqual(self.current_service_handle.read_management_state()['workflow_job_entries'],[])

    def test_rejects_invalid_csrf_token(self):
        current_http_request=self.build_http_request('incorrect-token')
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,400)

    def test_rejects_unexpected_host(self):
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token,current_host_text='outside.example')
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,403)

    def test_persists_submitted_instruction(self):
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token)
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,200)
        current_state_values=self.current_service_handle.read_management_state()
        self.assertEqual(current_state_values['workflow_job_entries'][0]['requested_instruction_text'],self.current_request_values['requested_instruction_text'])
        self.assertEqual(current_state_values['workflow_job_entries'][0]['current_stage_name'],'queued')

    def test_queues_existing_document_for_target_discovery(self):
        self.current_request_values['requested_operation_mode']='replace'
        current_task_values=self.current_service_handle.submit_document_request(self.current_request_values)
        self.assertIn('workflow_task_id',current_task_values)

    def test_book_plan_requires_csrf_and_build_serves_private_artifact(self):
        self.current_request_values={'book_title_text':'합성 도서','source_directory_paths':['world']}
        current_http_request=self.build_http_request('invalid')
        current_http_request.path='/worldbuilding/api/book-plan'
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,400)
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token)
        current_http_request.path='/worldbuilding/api/book-plan'
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,200)
        self.current_request_values['paragraph_placements']=json.loads(current_http_request.wfile.getvalue())['paragraph_placements']
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token)
        current_http_request.path='/worldbuilding/api/books'
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,200)
        current_book_id=json.loads(current_http_request.wfile.getvalue())['book_id']
        current_read_request=ManagementRequestStub('/worldbuilding/books/'+current_book_id+'/book.html','GET',{'Host':'127.0.0.1:8770'},None)
        self.current_service_handle.handle_management_request(current_read_request)
        self.assertEqual(current_read_request.response_status_code,200)
        self.assertIn('합성 도서',current_read_request.wfile.getvalue().decode())

    def test_file_structure_preview_apply_and_rollback_api(self):
        from generators.worldbuilding.bookbinding import plan_document_book
        (self.current_source_root/'world/first.md').write_text('# 첫 문서\n\n이동할 본문.\n')
        (self.current_source_root/'world/second.md').write_text('# 둘째 문서\n')
        current_plan_values=plan_document_book(self.current_service_handle.workspace_config_values,{'book_title_text':'테스트','source_directory_paths':['world']})
        current_paragraph_entries=sorted(current_plan_values['paragraph_entries'],key=lambda current_paragraph_entry:(current_paragraph_entry['source_document_path'],current_paragraph_entry['source_start_line']))
        current_placements=[{'paragraph_id':current_paragraph_entry['paragraph_id'],'target_document_path':current_paragraph_entry['source_document_path']} for current_paragraph_entry in current_paragraph_entries]
        current_moved_entry=next(current_placement_entry for current_placement_entry,current_paragraph_entry in zip(current_placements,current_paragraph_entries) if current_paragraph_entry['paragraph_text'].startswith('이동할'))
        current_placements.remove(current_moved_entry)
        current_moved_entry['target_document_path']='world/second.md'
        current_placements.append(current_moved_entry)
        self.current_request_values={'source_directory_paths':['world'],'paragraph_placements':current_placements,'new_document_titles':{}}
        current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token)
        current_http_request.path='/worldbuilding/api/reorganize-preview'
        self.current_service_handle.handle_management_request(current_http_request)
        self.assertEqual(current_http_request.response_status_code,200,current_http_request.wfile.getvalue())
        self.current_request_values={'reorganization_id':json.loads(current_http_request.wfile.getvalue())['reorganization_id']}
        for current_operation_name in ('apply','rollback'):
            current_http_request=self.build_http_request(self.current_service_handle.management_csrf_token)
            current_http_request.path='/worldbuilding/api/reorganize-'+current_operation_name
            self.current_service_handle.handle_management_request(current_http_request)
            self.assertEqual(current_http_request.response_status_code,200,current_http_request.wfile.getvalue())
        self.assertEqual((self.current_source_root/'world/first.md').read_text(),'# 첫 문서\n\n이동할 본문.\n')

    def test_rejects_second_manager_for_same_workspace(self):
        with self.assertRaises(RuntimeError):
            WorldbuildingManagement(self.current_config_path)


if __name__=='__main__':
    unittest.main()
