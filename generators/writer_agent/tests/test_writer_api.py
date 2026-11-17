"""管理 API의 출처·경로·요청 계약을 검사한다."""
from io import BytesIO
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import patch
import json
import os
from generators.writer_agent.jobs import read_process_identity
from generators.writer_agent.management import WriterAgentManager

class WriterApiContracts(TestCase):
    def setUp(self):
        self.temporary_root_handle=TemporaryDirectory()
        self.addCleanup(self.temporary_root_handle.cleanup)
        self.writer_manager_service=WriterAgentManager(Path(self.temporary_root_handle.name)/'missing.yaml')

    def build_request_handler(self,current_route_path,current_method_name='GET',current_body_values=None,**current_header_values):
        current_body_bytes=json.dumps(current_body_values).encode()
        current_headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','X-Writer-Token':self.writer_manager_service.csrf_token_value,'Content-Type':'application/json','Content-Length':str(len(current_body_bytes)),**current_header_values}
        current_http_handler=SimpleNamespace(path=current_route_path,command=current_method_name,headers=current_headers,server=SimpleNamespace(server_port=8770),rfile=BytesIO(current_body_bytes),wfile=BytesIO(),status_code=None)
        current_http_handler.send_response=lambda current_status_code:setattr(current_http_handler,'status_code',current_status_code)
        current_http_handler.send_header=lambda current_header_name,current_header_value:None
        current_http_handler.end_headers=lambda:None
        return current_http_handler

    def test_external_worker_identity_and_interrupted_status(self):
        current_status_values={'id':'test-job','stage':'indexing','process_id':os.getpid(),'process_identity':read_process_identity(os.getpid())}
        self.assertEqual(self.writer_manager_service.resolve_observed_status(current_status_values)['stage'],'indexing')
        current_status_values['process_identity']='different-process-start'
        self.assertEqual(self.writer_manager_service.resolve_observed_status(current_status_values)['stage'],'interrupted')

    def test_queued_job_survives_manager_restart_and_reports_failure(self):
        current_job_root=Path(self.temporary_root_handle.name)/'job'
        current_job_root.mkdir()
        current_status_values={'id':'test-job','stage':'queued'}
        (current_job_root/'queue-process.json').write_text(json.dumps({'pid':os.getpid(),'identity':read_process_identity(os.getpid())}))
        (current_job_root/'status.json').write_text(json.dumps({'status':'queued','queue_position':2,'message':'GPU 대기'}))
        current_fresh_manager=WriterAgentManager(self.writer_manager_service.workspace_config_path)
        current_observed_status=current_fresh_manager.resolve_observed_status(current_status_values,current_job_root)
        self.assertEqual(current_observed_status['stage'],'queued')
        self.assertEqual(current_observed_status['queue_position'],2)
        (current_job_root/'status.json').write_text(json.dumps({'status':'failed','error':'GPU 조회 실패'}))
        current_observed_status=current_fresh_manager.resolve_observed_status(current_status_values,current_job_root)
        self.assertEqual(current_observed_status['stage'],'failed')
        self.assertEqual(current_observed_status['error'],'GPU 조회 실패')

    def test_search_all_history_and_move_only_finished_job_to_trash(self):
        from generators.writer_agent.documents import save_yaml_document,load_workspace_config
        from generators.writer_agent.jobs import create_writer_job,resolve_job_directory,update_job_status
        current_test_root=Path(self.temporary_root_handle.name)
        current_documents_root=current_test_root/'docs'
        (current_documents_root/'ideas').mkdir(parents=True)
        current_original_path=current_documents_root/'ideas/original.md'
        current_original_path.write_text('원본 보존')
        current_workspace_path=current_test_root/'workspace.yaml'
        save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_test_root/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
        current_config_values=load_workspace_config(current_workspace_path)
        current_identifiers=[]
        for current_job_number in range(45):
            current_identifier=create_writer_job(current_config_values,{'mode':'write','prompt':'고유검증사십이' if current_job_number==42 else f'검색대상 {current_job_number}'})
            update_job_status(resolve_job_directory(current_config_values,current_identifier),'completed')
            current_identifiers.append(current_identifier)
        current_manager=WriterAgentManager(current_workspace_path)
        self.assertEqual(current_manager.search_writer_history('')['count'],45)
        self.assertEqual(current_manager.search_writer_history('고유검증사십이')['count'],1)
        current_deleted_identifier=current_identifiers[0]
        current_manager.delete_writer_history(current_deleted_identifier)
        self.assertFalse(resolve_job_directory(current_config_values,current_deleted_identifier).exists())
        self.assertTrue((current_test_root/'state/.history-trash'/current_deleted_identifier/'request.yaml').is_file())
        self.assertEqual(current_original_path.read_text(),'원본 보존')
        current_active_identifier=current_identifiers[1]
        update_job_status(resolve_job_directory(current_config_values,current_active_identifier),'indexing',process_id=os.getpid(),process_identity=read_process_identity(os.getpid()))
        with self.assertRaisesRegex(ValueError,'실행 중'):
            current_manager.delete_writer_history(current_active_identifier)

    def test_submit_uses_shared_queue_and_rejects_duplicate_after_restart(self):
        from generators.writer_agent.documents import save_yaml_document
        current_test_root=Path(self.temporary_root_handle.name)
        current_documents_root=current_test_root/'docs'
        (current_documents_root/'ideas').mkdir(parents=True)
        current_workspace_path=current_test_root/'workspace.yaml'
        save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_test_root/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
        current_manager=WriterAgentManager(current_workspace_path)
        current_runtime_path=current_test_root/'python'
        current_runtime_path.touch()
        def launch_mock_queue(current_command_parts,current_job_root,current_service_name,**current_options):
            self.assertEqual(current_service_name,'writer-agent')
            (current_job_root/'status.json').write_text(json.dumps({'status':'queued','queue_position':1}))
            return SimpleNamespace(pid=os.getpid(),poll=lambda:None)
        with patch('generators.writer_agent.prepare.RUNTIME_PYTHON_PATH',current_runtime_path), patch('generators.writer_agent.management.launch_gpu_process',side_effect=launch_mock_queue) as current_launch_mock, patch('generators.writer_agent.management.inspect_detached_preparation',return_value='idle'), patch('generators.writer_agent.management.threading.Thread'):
            current_submitted_job=current_manager.launch_writer_process({'mode':'learn','prompt':''})
            self.assertEqual(current_launch_mock.call_count,1)
            current_fresh_manager=WriterAgentManager(current_workspace_path)
            self.assertEqual(current_fresh_manager.read_workspace_state()['active_job'],current_submitted_job['id'])
            with self.assertRaisesRegex(ValueError,'대기 중'):
                current_fresh_manager.launch_writer_process({'mode':'learn','prompt':''})

    def test_unconfigured_state_is_visible(self):
        current_http_handler=self.build_request_handler('/writer-agent/api/state')
        self.assertTrue(self.writer_manager_service.handle_writer_request(current_http_handler))
        self.assertEqual(current_http_handler.status_code,200)
        self.assertFalse(json.loads(current_http_handler.wfile.getvalue())['configured'])

    def test_foreign_origin_host_or_token_blocks_write(self):
        for current_header_values in ({'Origin':'https://other.example'},{'Host':'attacker.example:8770'},{'X-Writer-Token':'wrong'}):
            current_http_handler=self.build_request_handler('/writer-agent/api/jobs','POST',{'mode':'learn','prompt':''},**current_header_values)
            with patch.object(self.writer_manager_service,'launch_writer_process') as current_launch_mock:
                self.writer_manager_service.handle_writer_request(current_http_handler)
                current_launch_mock.assert_not_called()
            self.assertEqual(current_http_handler.status_code,400)

    def test_valid_request_dispatch_and_unknown_routes(self):
        current_http_handler=self.build_request_handler('/writer-agent/api/jobs','POST',{'mode':'learn','prompt':''})
        with patch.object(self.writer_manager_service,'launch_writer_process',return_value={'id':'test-job'}) as current_launch_mock:
            self.writer_manager_service.handle_writer_request(current_http_handler)
            current_launch_mock.assert_called_once_with({'mode':'learn','prompt':''})
        self.assertEqual(current_http_handler.status_code,202)
        current_http_handler=self.build_request_handler('/writer-agent/../../secret')
        self.writer_manager_service.handle_writer_request(current_http_handler)
        self.assertEqual(current_http_handler.status_code,404)
        self.assertFalse(self.writer_manager_service.handle_writer_request(self.build_request_handler('/worldbuilding/api/state')))

    def test_gateway_preserves_writer_token_and_payload(self):
        from tools.review.common.management_gateway import ManagementCommandGateway
        current_gateway_value=ManagementCommandGateway({'writer-agent':self.writer_manager_service.handle_writer_request})
        for current_token_value,current_expected_status in [('wrong',400),(self.writer_manager_service.csrf_token_value,202)]:
            current_request_handler=self.build_request_handler('/management/command','POST',{'service':'writer-agent','command':'writer-submit','payload':{'mode':'learn','prompt':''}},**{'X-Writer-Token':current_token_value})
            with patch.object(self.writer_manager_service,'launch_writer_process',return_value={'id':'mock-job'}) as current_launch_mock:
                current_gateway_value.handle(current_request_handler)
                self.assertEqual(current_launch_mock.call_count,int(current_expected_status==202))
            self.assertEqual(current_request_handler.status_code,current_expected_status)

    def test_gateway_detail_uses_existing_record_reader(self):
        from tools.review.common.management_gateway import ManagementCommandGateway
        current_gateway_value=ManagementCommandGateway({'writer-agent':self.writer_manager_service.handle_writer_request})
        current_request_handler=self.build_request_handler('/management/command','POST',{'service':'writer-agent','command':'writer-detail','payload':{'id':'mock-job'}})
        with patch.object(self.writer_manager_service,'read_writer_detail',return_value={'id':'mock-job'}) as current_read_mock:
            current_gateway_value.handle(current_request_handler)
            current_read_mock.assert_called_once_with('mock-job')
        self.assertEqual(current_request_handler.status_code,200)

if __name__=='__main__':main()
