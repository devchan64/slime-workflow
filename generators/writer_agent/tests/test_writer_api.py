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

    def test_material_page_reads_only_requested_source_and_status(self):
        import yaml
        from generators.writer_agent import management
        current_state_root=Path(self.temporary_root_handle.name)
        current_job_identifier='20261115-114927-8d274ccd'
        current_job_root=current_state_root/'jobs'/current_job_identifier
        current_job_root.mkdir(parents=True)
        (current_job_root/'status.yaml').write_text(yaml.safe_dump({'id':current_job_identifier,'stage':'review'}))
        (current_job_root/'search.yaml').write_text(yaml.safe_dump({'results':[{'text':'안녕'*1000}],'snapshot_hashes':{'private':'excluded'}},allow_unicode=True))
        (current_job_root/'proposal.yaml').write_text('invalid: [')
        (current_job_root/'execution.log').write_text('로그를 읽으면 안 됩니다')
        current_request_record={'job_id':current_job_identifier,'section':'search','limit':1000}
        current_http_handler=self.build_request_handler('/writer-agent/api/material-page','POST',current_request_record)
        with patch.object(management,'load_workspace_config',return_value={'state_root':str(current_state_root)}),patch.object(management,'read_yaml_document',wraps=management.read_yaml_document) as current_read_mock:
            self.assertTrue(self.writer_manager_service.handle_writer_request(current_http_handler))
        self.assertEqual(current_http_handler.status_code,200)
        current_page_value=json.loads(current_http_handler.wfile.getvalue())
        self.assertEqual(current_page_value['section'],'search')
        self.assertEqual({current_call.args[0].name for current_call in current_read_mock.call_args_list},{'status.yaml','search.yaml'})
        self.assertNotIn('snapshot_hashes',current_page_value['content'])
        self.assertIsNotNone(current_page_value['next_offset'])

    def test_older_active_job_blocks_new_submission_after_manager_restart(self):
        from generators.writer_agent.documents import save_yaml_document
        current_test_root=Path(self.temporary_root_handle.name)
        current_jobs_root=current_test_root/'jobs'
        current_jobs_root.mkdir()
        current_config_path=current_test_root/'workspace.yaml'
        current_config_path.write_text('configured')
        current_workspace_config={'state_root':str(current_test_root),'document_root':str(current_test_root/'documents')}
        current_old_identifier='20261101-000000-00000000'
        current_old_root=current_jobs_root/current_old_identifier
        current_old_root.mkdir()
        save_yaml_document(current_old_root/'status.yaml',{'id':current_old_identifier,'stage':'queued'})
        (current_old_root/'queue-process.json').write_text(json.dumps({'pid':os.getpid(),'identity':read_process_identity(os.getpid())}))
        (current_old_root/'status.json').write_text(json.dumps({'status':'queued','queue_position':1}))
        for current_job_number in range(45):
            current_job_identifier=f'20261120-000000-{current_job_number:08x}'
            current_job_root=current_jobs_root/current_job_identifier
            current_job_root.mkdir()
            save_yaml_document(current_job_root/'status.yaml',{'id':current_job_identifier,'stage':'completed'})
        current_manager_value=WriterAgentManager(current_config_path)
        with patch('generators.writer_agent.management.load_workspace_config',return_value=current_workspace_config), patch('generators.writer_agent.management.launch_gpu_process') as current_launch_mock, patch('generators.writer_agent.management.create_writer_job') as current_create_mock:
            current_state_value=current_manager_value.read_workspace_state()
            self.assertEqual(len(current_state_value['jobs']),40)
            self.assertEqual(current_state_value['active_job'],current_old_identifier)
            with self.assertRaisesRegex(ValueError,'실행 중이거나 대기 중'):
                current_manager_value.launch_writer_process({'mode':'learn','prompt':''})
            current_create_mock.assert_not_called()
            current_launch_mock.assert_not_called()

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

    def test_writer_cancel_checks_live_queue_and_keeps_documents_untouched(self):
        from generators.writer_agent.documents import save_yaml_document
        from tools.review.common.management_gateway import ManagementCommandGateway
        current_test_root=Path(self.temporary_root_handle.name)
        current_docs_root=current_test_root/'docs'
        (current_docs_root/'ideas').mkdir(parents=True)
        current_document_path=current_docs_root/'ideas/original.md'
        current_document_path.write_text('원문 보존')
        current_workspace_path=current_test_root/'workspace.yaml'
        save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_docs_root),'state_root':str(current_test_root/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
        current_job_identifier='20261118-120000-12345678'
        current_job_root=current_test_root/'state/jobs'/current_job_identifier
        current_job_root.mkdir(parents=True)
        save_yaml_document(current_job_root/'status.yaml',{'id':current_job_identifier,'stage':'reasoning'})
        (current_job_root/'status.json').write_text(json.dumps({'status':'running'}))
        (current_job_root/'queue-process.json').write_text(json.dumps({'pid':os.getpid(),'identity':read_process_identity(os.getpid())}))
        current_manager_value=WriterAgentManager(current_workspace_path)
        current_gateway_value=ManagementCommandGateway({'writer-agent':current_manager_value.handle_writer_request})
        current_handler_value=self.build_request_handler('/management/command','POST',{'service':'writer-agent','command':'writer-cancel','payload':{'id':current_job_identifier}},**{'X-Writer-Token':current_manager_value.csrf_token_value})
        current_gateway_value.handle(current_handler_value)
        self.assertEqual(current_handler_value.status_code,200,current_handler_value.wfile.getvalue())
        self.assertTrue(json.loads(current_handler_value.wfile.getvalue())['cancel_requested'])
        self.assertTrue((current_job_root/'cancel.request').exists())
        self.assertEqual(current_document_path.read_text(),'원문 보존')
        (current_job_root/'cancel.request').unlink()
        (current_job_root/'queue-process.json').write_text(json.dumps({'pid':os.getpid(),'identity':'stale'}))
        with self.assertRaisesRegex(ValueError,'실행기'):current_manager_value.request_writer_cancellation(current_job_identifier)
        self.assertFalse((current_job_root/'cancel.request').exists())
        save_yaml_document(current_job_root/'status.yaml',{'id':current_job_identifier,'stage':'review'})
        with self.assertRaisesRegex(ValueError,'작가 작업만'):current_manager_value.request_writer_cancellation(current_job_identifier)

    def test_writer_material_global_capacity_recovers_after_error(self):
        from generators.writer_agent.management import hold_writer_material_guard
        current_test_root=Path(self.temporary_root_handle.name)
        with hold_writer_material_guard(current_test_root/'first.yaml'), hold_writer_material_guard(current_test_root/'second.yaml'):
            with self.assertRaisesRegex(ValueError,'조회 한도'):
                with hold_writer_material_guard(current_test_root/'third.yaml'):
                    self.fail('용량 초과 조회가 허용되었습니다.')
        with self.assertRaisesRegex(RuntimeError,'가상 실패'):
            with hold_writer_material_guard(current_test_root/'third.yaml'):
                raise RuntimeError('가상 실패')
        with hold_writer_material_guard(current_test_root/'third.yaml'):
            pass

    def test_writer_material_concurrent_reads_are_limited_per_section(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from generators.writer_agent import management
        current_state_root=Path(self.temporary_root_handle.name)
        current_job_identifier='20261118-120000-12345678'
        current_job_root=current_state_root/'jobs'/current_job_identifier
        current_job_root.mkdir(parents=True)
        for current_file_name in ('status.yaml','search.yaml','proposal.yaml'):
            (current_job_root/current_file_name).write_text('{}')
        current_entered_event=Event()
        current_release_event=Event()
        def read_test_document(current_file_path):
            if current_file_path.name=='status.yaml':return {'id':current_job_identifier,'stage':'completed'}
            if current_file_path.name=='search.yaml':
                current_entered_event.set()
                if not current_release_event.wait(5):raise RuntimeError('테스트 조회 대기 시간 초과')
            return {'results':[]}
        current_search_request={'job_id':current_job_identifier,'section':'search','limit':1000}
        current_proposal_request={'job_id':current_job_identifier,'section':'proposal','limit':1000}
        current_other_manager=WriterAgentManager(current_state_root/'other.yaml')
        with patch.object(management,'load_workspace_config',return_value={'state_root':str(current_state_root)}), patch.object(management,'read_yaml_document',side_effect=read_test_document), ThreadPoolExecutor(max_workers=1) as current_test_executor:
            current_first_result=current_test_executor.submit(self.writer_manager_service.read_writer_material_page,current_search_request)
            try:
                self.assertTrue(current_entered_event.wait(5))
                with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                    current_other_manager.read_writer_material_page(current_search_request)
                self.assertEqual(current_other_manager.read_writer_material_page(current_proposal_request)['section'],'proposal')
            finally:
                current_release_event.set()
            self.assertEqual(current_first_result.result(timeout=5)['section'],'search')
            self.assertEqual(current_other_manager.read_writer_material_page(current_search_request)['section'],'search')

    def test_passive_writer_history_uses_recorded_stage_without_prompt(self):
        from generators.writer_agent.documents import save_yaml_document
        current_test_root=Path(self.temporary_root_handle.name)
        current_documents_root=current_test_root/'docs'
        (current_documents_root/'ideas').mkdir(parents=True)
        current_workspace_path=current_test_root/'workspace.yaml'
        save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_test_root/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
        current_manager=WriterAgentManager(current_workspace_path)
        current_job_root=current_test_root/'state'/'jobs'/'20261118-120000-12345678'
        current_job_root.mkdir(parents=True)
        save_yaml_document(current_job_root/'status.yaml',{'id':current_job_root.name,'stage':'reasoning','summary':'secret'})
        save_yaml_document(current_job_root/'request.yaml',{'prompt':'private'})
        with patch.object(current_manager,'resolve_observed_status') as current_resolve_mock:
            current_result_value=current_manager.observe_writer_history({})
        self.assertEqual(current_result_value['records'],[{'id':current_job_root.name,'recorded_status':'reasoning','status_source':'job'}])
        self.assertNotIn('private',str(current_result_value))
        self.assertNotIn('secret',str(current_result_value))
        from tools.review.common.generation_records import hold_history_observation_guard
        with hold_history_observation_guard(current_test_root/'state'/'jobs'):
            with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                current_manager.observe_writer_history({})
        self.assertEqual(current_manager.observe_writer_history({})['total'],1)
        current_searched_value=current_manager.observe_writer_history({'query':'12345678'})
        self.assertEqual(current_searched_value['total'],1)
        self.assertEqual(current_manager.observe_writer_history({'query':'87654321'})['total'],0)
        with self.assertRaises(ValueError):current_manager.observe_writer_history({'query':'87654321','snapshot':current_searched_value['snapshot']})
        current_resolve_mock.assert_not_called()
        (current_job_root/'status.yaml').write_text('invalid: [')
        self.assertEqual(current_manager.observe_writer_history({})['records'][0]['recorded_status'],'unknown')
        with self.assertRaises(ValueError):current_manager.observe_writer_history({'offset':1})

    def test_writer_history_concurrent_observation_rejects_same_storage(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from generators.writer_agent import management
        current_state_root=Path(self.temporary_root_handle.name)
        current_job_root=current_state_root/'jobs'/'20261118-120000-12345678'
        current_job_root.mkdir(parents=True)
        (current_job_root/'status.yaml').write_text('stage: completed\n')
        current_entered_event=Event()
        current_release_event=Event()
        def hold_status_read(current_status_path):
            current_entered_event.set()
            if not current_release_event.wait(5):raise RuntimeError('테스트 조회 대기 시간 초과')
            return {'id':current_job_root.name,'stage':'completed'}
        current_other_manager=WriterAgentManager(current_state_root/'other.yaml')
        with patch.object(management,'load_workspace_config',return_value={'state_root':str(current_state_root)}), patch.object(management,'read_yaml_document',side_effect=hold_status_read), ThreadPoolExecutor(max_workers=1) as current_test_executor:
            current_first_result=current_test_executor.submit(self.writer_manager_service.observe_writer_history,{})
            try:
                self.assertTrue(current_entered_event.wait(5))
                with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                    current_other_manager.observe_writer_history({})
            finally:
                current_release_event.set()
            self.assertEqual(current_first_result.result(timeout=5)['total'],1)
            self.assertEqual(current_other_manager.observe_writer_history({})['total'],1)

    def test_writer_history_delete_rejects_unknown_or_active_queue_records(self):
        from generators.writer_agent.documents import save_yaml_document,load_workspace_config
        from generators.writer_agent.jobs import create_writer_job,resolve_job_directory,update_job_status
        current_test_root=Path(self.temporary_root_handle.name)
        current_documents_root=current_test_root/'docs'
        (current_documents_root/'ideas').mkdir(parents=True)
        current_workspace_path=current_test_root/'workspace.yaml'
        save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_test_root/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
        current_config_values=load_workspace_config(current_workspace_path)
        current_job_identifier=create_writer_job(current_config_values,{'mode':'learn','prompt':''})
        current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
        current_manager_value=WriterAgentManager(current_workspace_path)
        for current_queue_value in ({'status':'queued'},{'status':'running'},{'status':'paused'},{'bad':'record'}):
            update_job_status(current_job_root,'completed')
            (current_job_root/'status.json').write_text(json.dumps(current_queue_value))
            with self.subTest(current_queue_value=current_queue_value), self.assertRaisesRegex(ValueError,'삭제할 수 없습니다'):
                current_manager_value.delete_writer_history(current_job_identifier)
            self.assertTrue(current_job_root.is_dir())
        (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
        save_yaml_document(current_job_root/'status.yaml',{'id':current_job_identifier,'stage':'unrecognized'})
        with self.assertRaisesRegex(ValueError,'상태를 확인'):
            current_manager_value.delete_writer_history(current_job_identifier)
        self.assertTrue(current_job_root.is_dir())
        update_job_status(current_job_root,'completed')
        self.assertTrue(current_manager_value.delete_writer_history(current_job_identifier)['recoverable'])

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

    def test_history_observe_requires_same_origin_and_writer_token(self):
        from tools.review.common.management_gateway import resolve_management_command
        self.assertEqual(resolve_management_command('writer-agent','writer-token',{}),('GET','/writer-agent/api/token'))
        with self.assertRaises(ValueError):
            resolve_management_command('writer-agent','writer-token',{'extra':True})
        current_token_handler=self.build_request_handler('/writer-agent/api/token')
        with patch.object(self.writer_manager_service,'read_workspace_state',side_effect=AssertionError('전체 상태 조회 금지')):
            self.writer_manager_service.handle_writer_request(current_token_handler)
        self.assertEqual(current_token_handler.status_code,200)
        self.assertEqual(json.loads(current_token_handler.wfile.getvalue()),{'csrf_token':self.writer_manager_service.csrf_token_value})
        current_invalid_host=self.build_request_handler('/writer-agent/api/token',Host='example.invalid:8770')
        self.writer_manager_service.handle_writer_request(current_invalid_host)
        self.assertEqual(current_invalid_host.status_code,400)
        for current_headers in ({'X-Writer-Token':'wrong'},{'Origin':'http://example.invalid'}):
            current_history_handler=self.build_request_handler('/writer-agent/api/history/observe','POST',{},**current_headers)
            with patch.object(self.writer_manager_service,'observe_writer_history') as current_observe_mock:
                self.writer_manager_service.handle_writer_request(current_history_handler)
            self.assertEqual(current_history_handler.status_code,400)
            current_observe_mock.assert_not_called()

    def test_foreign_origin_host_or_token_blocks_write(self):
        for current_header_values in ({'Origin':'https://other.example'},{'Host':'attacker.example:8770'},{'X-Writer-Token':'wrong'}):
            current_http_handler=self.build_request_handler('/writer-agent/api/jobs','POST',{'mode':'learn','prompt':''},**current_header_values)
            with patch.object(self.writer_manager_service,'launch_writer_process') as current_launch_mock:
                self.writer_manager_service.handle_writer_request(current_http_handler)
                current_launch_mock.assert_not_called()
            self.assertEqual(current_http_handler.status_code,400)

    def test_index_status_classifies_fresh_stale_and_unavailable(self):
        for current_index_effect,current_expected_status in ((None,'fresh'),(ValueError('문서 추가·수정·삭제 이후 색인이 오래되었습니다. 학습 갱신이 필요합니다.'),'stale'),(ValueError('private details'),'unavailable')):
            current_handler_value=self.build_request_handler('/writer-agent/api/index-status','POST',{})
            with patch('generators.writer_agent.management.load_workspace_config',return_value={}), patch('generators.writer_agent.index.load_current_index',side_effect=current_index_effect):
                self.writer_manager_service.handle_writer_request(current_handler_value)
            self.assertEqual(current_handler_value.status_code,200)
            self.assertEqual(json.loads(current_handler_value.wfile.getvalue()),{'status':current_expected_status})
        current_handler_value=self.build_request_handler('/writer-agent/api/index-status','POST',{'path':'private'})
        self.writer_manager_service.handle_writer_request(current_handler_value)
        self.assertEqual(current_handler_value.status_code,400)

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
