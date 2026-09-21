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

    def test_rejects_second_manager_for_same_workspace(self):
        with self.assertRaises(RuntimeError):
            WorldbuildingManagement(self.current_config_path)


if __name__=='__main__':
    unittest.main()
