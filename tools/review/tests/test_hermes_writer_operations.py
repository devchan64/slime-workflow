"""작가 AI 위임 기록과 제안 조회 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import writer_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesWriterOperationsTests(unittest.TestCase):
    def test_legacy_writer_404_falls_back_through_http_gateway(self):
        import json
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.common.management_transport import send_management_json_response
        from tools.review.domains.hermes_agent import writer_operations
        from tools.review.gateway_server import create_gateway_request_handler
        current_routes=[]
        current_job_id='20261115-114927-8d274ccd'
        def handle_legacy_writer_request(current_http_handler):
            current_routes.append(current_http_handler.path)
            if current_http_handler.path in ('/writer-agent/api/token','/writer-agent/api/state'):
                send_management_json_response(current_http_handler,200,{'csrf_token':'test-token'})
            elif current_http_handler.path=='/writer-agent/api/material-page':
                send_management_json_response(current_http_handler,404,{'error':'지원하지 않는 작업 경로'})
            elif current_http_handler.path=='/writer-agent/api/detail':
                send_management_json_response(current_http_handler,200,{'id':current_job_id,'status':{'stage':'review'},'search':{'results':[{'text':'기존 자료'}]}})
            else:
                send_management_json_response(current_http_handler,404,{'error':'지원하지 않는 작업 경로'})
            return True
        current_gateway=ManagementCommandGateway({'writer-agent':handle_legacy_writer_request})
        current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
        current_server.emit_gateway_trace=lambda *current_values:None
        current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
        current_thread.start()
        try:
            with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:'+str(current_server.server_port)}):
                current_page=writer_operations.read_writer_job_material_page({'job_id':current_job_id,'section':'search'})
            self.assertEqual(json.loads(current_page['content'])['results'][0]['text'],'기존 자료')
            self.assertEqual(current_routes.count('/writer-agent/api/material-page'),1)
            self.assertEqual(current_routes.count('/writer-agent/api/detail'),1)
            self.assertEqual(current_routes.count('/writer-agent/api/token'),1)
            self.assertEqual(current_routes.count('/writer-agent/api/state'),1)
        finally:
            current_server.shutdown()
            current_server.server_close()
            current_thread.join(timeout=5)

    def test_writer_material_busy_propagates_through_gateway_without_fallback(self):
        import json
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from generators.writer_agent import management
        from tools.review.common.management_gateway import ManagementCommandGateway
        from tools.review.gateway_server import create_gateway_request_handler
        with TemporaryDirectory() as current_temporary_root:
            current_state_root=Path(current_temporary_root)
            current_job_identifier='20261115-114927-8d274ccd'
            current_job_root=current_state_root/'jobs'/current_job_identifier
            current_job_root.mkdir(parents=True)
            (current_job_root/'status.yaml').write_text('id: '+current_job_identifier+'\nstage: completed\n')
            (current_job_root/'search.yaml').write_text('results: []\n')
            current_writer_manager=management.WriterAgentManager(current_state_root/'workspace.yaml')
            current_gateway=ManagementCommandGateway({'writer-agent':current_writer_manager.handle_writer_request})
            current_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway.handle))
            current_server.emit_gateway_trace=lambda *current_values:None
            current_thread=threading.Thread(target=current_server.serve_forever,daemon=True)
            current_thread.start()
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:'+str(current_server.server_port)}), patch.object(management,'load_workspace_config',return_value={'state_root':str(current_state_root)}), patch.object(current_writer_manager,'read_writer_detail',side_effect=AssertionError('전체 자료 조회 금지')) as current_detail_mock:
                    with management.hold_writer_material_guard(current_state_root/'busy-one'), management.hold_writer_material_guard(current_state_root/'busy-two'):
                        with self.assertRaisesRegex(ValueError,'조회 한도'):
                            writer_operations.read_writer_job_material_page({'job_id':current_job_identifier,'section':'search'})
                    current_page_value=writer_operations.read_writer_job_material_page({'job_id':current_job_identifier,'section':'search'})
                    self.assertEqual(json.loads(current_page_value['content']),{'results':[]})
                    current_detail_mock.assert_not_called()
            finally:
                current_server.shutdown()
                current_server.server_close()
                current_thread.join(timeout=5)

    def test_writer_material_prefers_page_api_and_rejects_bad_response(self):
        from generators.writer_agent.material_pages import build_writer_material_page
        from tools.review.domains.hermes_agent import writer_operations
        current_request={'job_id':'20261115-114927-8d274ccd','section':'search','limit':10}
        current_page=build_writer_material_page(current_request,{'results':[{'text':'자료'}]})
        with patch.object(writer_operations,'call_hermes_writer_service',return_value=current_page) as current_service_mock:
            self.assertEqual(writer_operations.read_writer_job_material_page(current_request),current_page)
            current_service_mock.assert_called_once_with('writer-material-page',current_request)
        with patch.object(writer_operations,'call_hermes_writer_service',return_value={**current_page,'offset':1}):
            with self.assertRaisesRegex(ValueError,'응답 형식'):
                writer_operations.read_writer_job_material_page(current_request)
        with patch.object(writer_operations,'call_hermes_writer_service',return_value={**current_page,'content':'x','next_offset':True}):
            with self.assertRaisesRegex(ValueError,'페이지 위치'):
                writer_operations.read_writer_job_material_page(current_request)
        with patch.object(writer_operations,'call_hermes_writer_service',side_effect=ValueError('관리 API 오류 (400): 요청 오류')) as current_service_mock:
            with self.assertRaisesRegex(ValueError,'요청 오류'):
                writer_operations.read_writer_job_material_page(current_request)
            self.assertEqual(current_service_mock.call_count,1)

    def test_writer_material_pages_reconstruct_complete_json_and_detect_change(self):
        import json
        from tools.review.domains.hermes_agent import writer_operations
        current_job_id='20261115-114927-8d274ccd'
        current_source_value={'results':[{'path':'기획/a.md','text':'가나다/with/path '*2000}], 'prompt':'검색'}
        current_detail_record={'id':current_job_id,'status':{'stage':'review'},'search':current_source_value}
        current_contents=[]
        current_request_value={'job_id':current_job_id,'section':'search','limit':997}
        def respond_legacy_writer_service(current_command_name,current_payload_record):
            if current_command_name=='writer-material-page':raise ValueError('관리 API 오류 (404): 지원하지 않는 경로')
            return current_detail_record
        with patch.object(writer_operations,'call_hermes_writer_service',side_effect=respond_legacy_writer_service):
            while True:
                current_page_value=writer_operations.read_writer_job_material_page(current_request_value)
                current_contents.append(current_page_value['content'])
                if current_page_value['next_offset'] is None:break
                current_request_value.update(offset=current_page_value['next_offset'],snapshot=current_page_value['snapshot'])
            self.assertEqual(json.loads(''.join(current_contents)),current_source_value)
            with self.assertRaisesRegex(ValueError,'snapshot'):
                writer_operations.read_writer_job_material_page({'job_id':current_job_id,'section':'search','offset':1})
            current_source_value['prompt']='changed'
            with self.assertRaisesRegex(ValueError,'변경됐습니다'):
                writer_operations.read_writer_job_material_page(current_request_value)
            current_detail_record['status']['stage']='reasoning'
            with self.assertRaisesRegex(ValueError,'진행 중'):
                writer_operations.read_writer_job_material_page({'job_id':current_job_id,'section':'search'})

    def test_writer_material_stream_matches_canonical_json_across_boundaries(self):
        import hashlib
        import json
        from generators.writer_agent.material_pages import build_writer_material_page
        current_source_value={'가': '😀가\\"'*40000, 'results':[{'text':'끝'}], 'snapshot_hashes':{'hidden':'value'}}
        current_public_value={key:value for key,value in current_source_value.items() if key!='snapshot_hashes'}
        current_expected_text=json.dumps(current_public_value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        current_expected_hash=hashlib.sha256(current_expected_text.encode('utf-8')).hexdigest()
        for current_page_offset in (0,1,65530,65536,65540,len(current_expected_text)-1,len(current_expected_text)):
            with self.subTest(offset=current_page_offset):
                current_request_value={'job_id':'20261115-114927-8d274ccd','section':'search','offset':current_page_offset,'limit':29}
                if current_page_offset:current_request_value['snapshot']=current_expected_hash
                current_page_value=build_writer_material_page(current_request_value,current_source_value)
                self.assertEqual(current_page_value['content'],current_expected_text[current_page_offset:current_page_offset+29])
                self.assertEqual(current_page_value['snapshot'],current_expected_hash)
                self.assertEqual(current_page_value['total_characters'],len(current_expected_text))
                self.assertEqual(current_page_value['next_offset'],current_page_offset+29 if current_page_offset+29<len(current_expected_text) else None)

    def test_writer_index_status_preserves_three_states_and_rejects_bad_contract(self):
        from tools.review.domains.hermes_agent import writer_operations
        for current_status_value in ('fresh','stale','unavailable'):
            with self.subTest(current_status_value=current_status_value), patch.object(writer_operations,'call_hermes_writer_service',return_value={'status':current_status_value}) as current_service_mock:
                current_status_record=writer_operations.read_hermes_writer_index_status()
                self.assertEqual(current_status_record['status'],current_status_value)
                self.assertIn('GPU',current_status_record['note'])
                current_service_mock.assert_called_once_with('writer-index-status',{})
        for current_bad_record in ({'status':'ready'},{'status':'fresh','extra':'value'},{},None):
            with self.subTest(current_bad_record=current_bad_record), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_bad_record), self.assertRaises(ValueError):
                writer_operations.read_hermes_writer_index_status()

    def test_sandbox_writer_search_bridge_accepts_only_request_id(self):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_cases=((b'writer-search-paths {"request_id":"request_123"}\n',True),(b'writer-search-paths {"request_id":"request_123","action":"execute"}\n',False),(b'writer-search-paths {"request_id":"request_123","request_id":"request_456"}\n',False),(b'writer-search-paths {}\n',False))
        for current_request_bytes,current_expected_success in current_cases:
            with self.subTest(current_request_bytes=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                with current_client_socket,patch.object(writer_operations,'read_hermes_writer_search_paths',return_value={'paths':['world/town.md'],'truncated':False}) as current_read_mock:
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                    current_thread_value.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_record=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_value.join(timeout=3)
                    self.assertFalse(current_thread_value.is_alive())
                    if current_expected_success:
                        self.assertEqual(current_response_record,{'paths':['world/town.md'],'truncated':False})
                        current_read_mock.assert_called_once_with('request_123')
                    else:
                        self.assertIn('error',current_response_record)
                        current_read_mock.assert_not_called()

    def test_evidence_path_query_accepts_only_path_response(self):
        current_job_identifier='20261118-120000-12345678'
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service') as current_service_mock:
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_service_mock.return_value={'paths':['world/town.md','world/road.md'],'truncated':True}
            self.assertEqual(writer_operations.read_hermes_writer_search_paths('request_123'),current_service_mock.return_value)
            current_service_mock.assert_called_once_with('writer-search-paths',{'id':current_job_identifier})
            for current_bad_response in ({'paths':['../secret'],'truncated':False},{'paths':['/secret'],'truncated':False},{'paths':['.hidden/a'],'truncated':False},{'paths':['world/a.md'],'truncated':False,'text':'secret'},{'paths':['a','a'],'truncated':False}):
                current_service_mock.return_value=current_bad_response
                with self.subTest(current_bad_response=current_bad_response),self.assertRaises(ValueError):writer_operations.read_hermes_writer_search_paths('request_123')
            current_service_mock.side_effect=OSError('/private/secret')
            with self.assertRaises(ValueError) as current_error:writer_operations.read_hermes_writer_search_paths('request_123')
            self.assertNotIn('/private/secret',str(current_error.exception))
            current_store_mock.return_value.read_service_delegation.return_value={'state':'unknown'}
            current_service_mock.reset_mock()
            with self.assertRaises(ValueError):writer_operations.read_hermes_writer_search_paths('request_123')
            current_service_mock.assert_not_called()

    def test_sandbox_writer_job_search_validates_request_contract(current_test_case):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_job_identifier='20261115-114927-8d274ccd'
        current_cases=((b'writer-job-search-paths {"job_id":"20261115-114927-8d274ccd"}\n',True),(b'writer-job-search-paths {"job_id":"x","action":"execute"}\n',False),(b'writer-job-search-paths {"job_id":"x","job_id":"y"}\n',False),(b'writer-job-search-paths {}\n',False))
        for current_request_bytes,current_expected_success in current_cases:
            with current_test_case.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                with current_client_socket,patch.object(writer_operations,'read_writer_job_search_paths',return_value={'paths':['world/town.md'],'truncated':False}) as current_read_mock:
                    current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                    current_thread.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread.join(timeout=3)
                    current_test_case.assertFalse(current_thread.is_alive())
                    if current_expected_success:
                        current_test_case.assertEqual(current_response,{'paths':['world/town.md'],'truncated':False})
                        current_read_mock.assert_called_once_with(current_job_identifier)
                    else:
                        current_test_case.assertIn('error',current_response)
                        current_read_mock.assert_not_called()

    def test_sandbox_writer_material_allows_only_valid_pages(current_test_case):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_cases=((b'writer-job-material {"job_id":"20261115-114927-8d274ccd","section":"search"}\n',True),
            (b'writer-job-material {"job_id":"20261115-114927-8d274ccd","section":"search","offset":1}\n',False),
            (b'writer-job-material {"job_id":"20261115-114927-8d274ccd","section":"search","action":"apply"}\n',False),
            (b'writer-job-material {"job_id":"x","job_id":"y","section":"search"}\n',False),
            (b'writer-job-material {}\nrun shell\n',False))
        for current_request_bytes,current_expected_success in current_cases:
            with current_test_case.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                with current_client_socket,patch.object(writer_operations,'read_writer_job_material_page',return_value={'content':'근거','next_offset':None}) as current_read_mock:
                    current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                    current_thread.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread.join(timeout=3)
                    current_test_case.assertFalse(current_thread.is_alive())
                    if current_expected_success:
                        current_test_case.assertEqual(current_response['content'],'근거')
                        current_read_mock.assert_called_once()
                    else:
                        current_test_case.assertIn('error',current_response)
                        current_read_mock.assert_not_called()

    def test_sandbox_writer_job_review_requires_exact_request(current_test_case):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_job_identifier='20261115-114927-8d274ccd'
        current_cases=((b'writer-job-review {"job_id":"20261115-114927-8d274ccd"}\n',True),(b'writer-job-review {"job_id":"x","action":"execute"}\n',False),(b'writer-job-review {"job_id":"x","job_id":"y"}\n',False))
        for current_request_bytes,current_expected_success in current_cases:
            with current_test_case.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                with current_client_socket,patch.object(writer_operations,'read_writer_job_review',return_value={'stage':'review','changes':[]}) as current_read_mock:
                    current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                    current_thread.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread.join(timeout=3)
                    current_test_case.assertFalse(current_thread.is_alive())
                    if current_expected_success:
                        current_test_case.assertEqual(current_response,{'job_id':current_job_identifier,'job':{'stage':'review','changes':[]}})
                        current_read_mock.assert_called_once_with(current_job_identifier)
                    else:
                        current_test_case.assertIn('error',current_response)
                        current_read_mock.assert_not_called()

    def test_isolated_writer_review_preserves_diagnostics_from_source(current_test_case):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_job_identifier='20261120-120000-abcdef12'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'failed','error':'시험 오류'},'log':'시험 로그'}
        current_client_socket,current_server_socket=socket.socketpair()
        with current_client_socket,patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
            current_thread.start()
            current_client_socket.sendall(('writer-job-review '+json.dumps({'job_id':current_job_identifier})+'\n').encode())
            current_result_value=json.loads(current_client_socket.makefile('rb').readline())
            current_thread.join(timeout=3)
        current_test_case.assertFalse(current_thread.is_alive())
        current_test_case.assertEqual(current_result_value['job']['diagnostic']['error'],'시험 오류')
        current_test_case.assertEqual(current_result_value['job']['diagnostic']['log_tail'],'시험 로그')

    def test_direct_writer_job_search_validates_identifier_and_response(current_test_case):
        current_job_identifier = '20261120-120000-abcdef12'
        with patch.object(writer_operations, 'call_hermes_writer_service', return_value={'paths':['world/town.md'],'truncated':False}) as current_service_mock:
            current_test_case.assertEqual(writer_operations.read_writer_job_search_paths(current_job_identifier), {'paths':['world/town.md'],'truncated':False})
            current_service_mock.assert_called_once_with('writer-search-paths', {'id':current_job_identifier})
            current_service_mock.reset_mock()
            with current_test_case.assertRaises(ValueError):
                writer_operations.read_writer_job_search_paths('../secret')
            current_service_mock.assert_not_called()
            current_service_mock.return_value={'paths':['../secret'],'truncated':False}
            with current_test_case.assertRaises(ValueError):
                writer_operations.read_writer_job_search_paths(current_job_identifier)

    def test_writer_service_filters_paths_before_transport(self):
        from generators.writer_agent.management import WriterAgentManager
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            (current_root_path/'world').mkdir()
            (current_root_path/'world'/'town.md').write_text('비공개 본문')
            (current_root_path/'world'/'road.md').write_text('비공개 본문')
            (current_root_path/'excluded').mkdir()
            (current_root_path/'excluded'/'secret.md').write_text('제외 문서')
            (current_root_path/'outside-link').symlink_to('/tmp')
            current_secret_text='비공개 본문과 제목'
            current_detail_record={'status':{'stage':'review'},'search':{'prompt':current_secret_text,'results':[{'path':'world/town.md','text':current_secret_text},{'path':'world/road.md','text':current_secret_text},{'path':'/private/secret.md'},{'path':'../escape.md'},{'path':'a//b.md'},{'path':'outside-link/nope'},{'path':'excluded/secret.md'}]}}
            current_manager_value=WriterAgentManager()
            with patch.object(current_manager_value,'read_writer_detail',return_value=current_detail_record), patch('generators.writer_agent.management.load_workspace_config',return_value={'document_root':str(current_root_path),'state_root':str(current_root_path.parent/'unused-state'),'excluded_roots':['excluded']}):
                current_result_record=current_manager_value.read_writer_search_paths('job-1')
                self.assertEqual(current_result_record,{'paths':['world/town.md','world/road.md'],'truncated':True})
                self.assertNotIn(current_secret_text,str(current_result_record))
                current_detail_record['status']['stage']='failed'
                self.assertEqual(current_manager_value.read_writer_search_paths('job-1'),current_result_record)
                current_detail_record['status']['stage']='interrupted'
                self.assertEqual(current_manager_value.read_writer_search_paths('job-1'),current_result_record)
                current_detail_record['status']['stage']='running'
                with self.assertRaises(ValueError):current_manager_value.read_writer_search_paths('job-1')
                current_detail_record['status']['stage']='review'
                current_detail_record.pop('search')
                current_detail_record['proposal']={'evidence':[{'path':'world/town.md','text':current_secret_text}]}
                with self.assertRaises(ValueError):current_manager_value.read_writer_search_paths('job-1')

    def test_writer_search_rejects_workspace_configuration_changes(self):
        from generators.writer_agent.management import WriterAgentManager
        current_manager_value=WriterAgentManager()
        current_detail_record={'status':{'stage':'review'},'search':{'results':[]}}
        current_initial_config={'document_root':'/first','state_root':'/state','excluded_roots':[]}
        current_changed_config={'document_root':'/second','state_root':'/state','excluded_roots':[]}
        with patch.object(current_manager_value,'read_writer_detail',return_value=current_detail_record) as current_detail_mock, patch('generators.writer_agent.management.load_workspace_config',side_effect=[current_initial_config,current_changed_config]):
            with self.assertRaisesRegex(ValueError,'설정이 변경'):
                current_manager_value.read_writer_search_paths('job-1')
            current_detail_mock.assert_called_once_with('job-1',current_initial_config)

    def test_writer_search_rejects_configuration_changes_during_path_validation(self):
        from generators.writer_agent.management import WriterAgentManager
        current_manager_value=WriterAgentManager()
        current_detail_record={'status':{'stage':'review'},'search':{'results':[]}}
        current_initial_config={'document_root':'/first','state_root':'/state','excluded_roots':[]}
        current_changed_config={'document_root':'/second','state_root':'/state','excluded_roots':[]}
        with patch.object(current_manager_value,'read_writer_detail',return_value=current_detail_record), patch('generators.writer_agent.management.load_workspace_config',side_effect=[current_initial_config,current_initial_config,current_changed_config]):
            with self.assertRaisesRegex(ValueError,'설정이 변경'):
                current_manager_value.read_writer_search_paths('job-1')

    def test_cancellation_requires_matching_receipt_and_job(self):
        current_job_identifier='20261118-120000-12345678'
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value={'id':current_job_identifier,'status':'running','cancel_requested':True}) as current_gateway_mock:
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            with self.assertRaises(ValueError):writer_operations.cancel_hermes_writer_request('request_123','20261118-120000-ffffffff')
            current_gateway_mock.assert_not_called()
            self.assertTrue(writer_operations.cancel_hermes_writer_request('request_123',current_job_identifier)['cancel_requested'])
            current_gateway_mock.assert_called_once_with('writer-cancel',{'id':current_job_identifier})
            current_gateway_mock.return_value={'id':'wrong','cancel_requested':True}
            with self.assertRaises(ValueError):writer_operations.cancel_hermes_writer_request('request_123',current_job_identifier)

    def test_writer_job_id_duplicate_and_sanitized_status(self):
        current_request_value={'mode':'write','prompt':'마을 설명'}
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'job_path':'/private/secret','status':{'stage':'review','proposal_hash':'a'*64,'summary':'변경 1개','error':'private'},'proposal':{'changes':[{'path':'world/town.md','diff':'-이전\n+변경','after':'secret'}],'warnings':['검토']},'log':'private'}
        def execute_writer_command(current_command_name,current_payload_value):
            if current_command_name=='writer-submit':return {'id':current_job_identifier,'job_path':'/private'}
            if current_command_name=='writer-detail':return current_detail_value
            raise AssertionError(current_command_name)
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'validate_hermes_writer_request') as current_validate_mock, patch.object(writer_operations,'call_hermes_writer_service',side_effect=execute_writer_command) as current_gateway_mock:
            self.assertFalse(writer_operations.submit_hermes_writer_request('writer_request_123',current_request_value)['duplicate'])
            self.assertTrue(writer_operations.submit_hermes_writer_request('writer_request_123',current_request_value)['duplicate'])
            current_validate_mock.assert_called_once()
            current_status_value=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertEqual(current_status_value['job']['changes'][0]['path'],'world/town.md')
            self.assertEqual(current_status_value['job']['proposal_hash'],'a'*64)
            self.assertNotIn('private',str(current_status_value))
            self.assertNotIn('secret',str(current_status_value))
            self.assertEqual(current_gateway_mock.call_count,2)
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_service_delegations('writer-agent')['records'][0]['job_id'],current_job_identifier)

    def test_writer_warnings_cannot_be_silently_truncated(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review','proposal_hash':'a'*64},'proposal':{'changes':[{'path':'world/town.md','diff':'-a\n+b'}],'warnings':[]}}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value) as current_gateway_mock:
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_detail_value['proposal']['warnings']=['경고']*31
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(current_result['job']['truncated'])
            self.assertEqual(len(current_result['job']['warnings']),30)
            current_detail_value['proposal']['warnings']=['x'*1001]
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(current_result['job']['truncated'])
            self.assertEqual(len(current_result['job']['warnings'][0]),1000)
            current_detail_value['proposal']['warnings']=['경고',None]
            with self.assertRaises(ValueError):writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(all(item.args[0]=='writer-detail' for item in current_gateway_mock.call_args_list))

    def test_failed_writer_review_exposes_bounded_source_diagnostics(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'failed','error':'원인'+('x'*5000)},'log':'시작'+('y'*15000)}
        with patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_review_value=writer_operations.read_writer_job_review(current_job_identifier)
        current_diagnostic_value=current_review_value['diagnostic']
        self.assertTrue(current_diagnostic_value['error'].startswith('원인'))
        self.assertEqual(len(current_diagnostic_value['error']),4000)
        self.assertTrue(current_diagnostic_value['error_truncated'])
        self.assertEqual(len(current_diagnostic_value['log_tail']),12000)
        self.assertTrue(current_diagnostic_value['log_tail_truncated'])
        self.assertIn('실행 지시가 아닙니다',current_diagnostic_value['note'])
        current_detail_value['status']['stage']='review'
        with patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            self.assertNotIn('diagnostic',writer_operations.read_writer_job_review(current_job_identifier))

    def test_direct_writer_job_review_checks_identity_and_bounds(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'changes':[{'path':'world/town.md','diff':'x'*100001}],'warnings':[]}}
        with patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value) as current_gateway_mock:
            current_review_value=writer_operations.read_writer_job_review(current_job_identifier)
            self.assertTrue(current_review_value['truncated'])
            self.assertEqual(len(current_review_value['changes'][0]['diff']),100000)
            current_gateway_mock.assert_called_once_with('writer-detail',{'id':current_job_identifier})
            with self.assertRaises(ValueError):writer_operations.read_writer_job_review('../secret')
            current_detail_value['id']='20261118-120000-87654321'
            with self.assertRaises(ValueError):writer_operations.read_writer_job_review(current_job_identifier)

    def test_writer_reason_exposes_bounded_text_without_absolute_paths(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'reason':'관련 문서를 보완합니다.','changes':[],'warnings':[]}}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertEqual(current_result['reason'],'관련 문서를 보완합니다.')
            self.assertFalse(current_result['reason_truncated'])
            current_detail_value['proposal']['reason']='x'*2001
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertTrue(current_result['reason_truncated'])
            self.assertEqual(len(current_result['reason']),2000)
            current_detail_value['proposal']['reason']='확인: /home/private/file'
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertIsNone(current_result['reason'])
            self.assertNotIn('/home/private',str(current_result))

    def test_writer_coverage_and_retained_are_bounded_and_paths_checked(self):
        current_job_identifier='20261118-120000-12345678'
        current_coverage_value={'eligible_chunks':10,'compared_pairs':3,'candidate_pairs':2,'reviewed_pairs':2,'limited':False}
        current_proposal_value={'changes':[],'warnings':[],'coverage':current_coverage_value,'retained':[{'path':'world/town.md','reason':'고유 정보 보존'}]}
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':current_proposal_value}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertEqual(current_result['coverage'],current_coverage_value)
            self.assertEqual(current_result['retained'][0]['reason'],'고유 정보 보존')
            self.assertFalse(current_result['retained_truncated'])
            current_proposal_value['retained']=[{'path':'/private/secret','reason':'no'},{'path':'C:\\secret','reason':'no'}]
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertTrue(current_result['retained_truncated'])
            self.assertEqual(current_result['retained'],[])
            self.assertNotIn('/private/secret',str(current_result))
            current_proposal_value['coverage']={**current_coverage_value,'eligible_chunks':True}
            with self.assertRaises(ValueError):writer_operations.read_hermes_writer_status('writer_request_123')

    def test_writer_evidence_limits_content_and_blocks_unsafe_paths(self):
        current_chunk={'path':'world/town.md','heading':'마을','text':'기존 설정','id':'chunk-1'}
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([current_chunk])
        self.assertFalse(current_truncated)
        self.assertEqual(current_values[0]['text'],'기존 설정')
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([{'keep':current_chunk,'remove':current_chunk,'reason':'중복'}])
        self.assertFalse(current_truncated)
        self.assertEqual(current_values[0]['reason'],'중복')
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([{**current_chunk,'path':'/private/secret'},{**current_chunk,'text':'x'*4001}])
        self.assertTrue(current_truncated)
        self.assertEqual(len(current_values[0]['text']),4000)
        self.assertNotIn('/private/secret',str(current_values))
        with self.assertRaises(ValueError):writer_operations.summarize_hermes_writer_evidence([{'path':'x'}])

    def test_warning_truncation_blocks_writer_apply(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review','proposal_hash':current_hash_value},'proposal':{'changes':[{'path':'world/town.md','diff':'-a\n+b'}],'warnings':['경고']*31}}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{},lambda current_request:{'id':current_job_identifier},lambda current_request:None)
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    writer_operations.apply_hermes_writer_proposal_once('writer_apply_123','writer_request_123',current_job_identifier,current_hash_value)
                self.assertTrue(all(item.args[0]!='writer-apply' for item in current_gateway_mock.call_args_list))

    def test_lost_writer_response_not_retried(self):
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'validate_hermes_writer_request'), patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                writer_operations.submit_hermes_writer_request('writer_request_456',{'mode':'write','prompt':'제안'})
            self.assertEqual(writer_operations.read_hermes_writer_status('writer_request_456')['receipt']['state'],'unknown')
            self.assertTrue(writer_operations.submit_hermes_writer_request('writer_request_456',{'mode':'write','prompt':'제안'})['duplicate'])
            current_gateway_mock.assert_called_once()

    def test_writer_checks_fresh_index_before_submission(self):
        current_request_value={'mode':'write','prompt':'제안'}
        with patch('generators.writer_agent.jobs.validate_job_request'), patch.object(writer_operations,'call_hermes_writer_service',side_effect=[{'configured':True,'ready':True,'trained':True,'active_job':None},{'status':'stale'}]) as current_gateway_mock:
            with self.assertRaisesRegex(ValueError,'색인이 오래'):
                writer_operations.validate_hermes_writer_request(current_request_value)
            self.assertEqual([item.args[0] for item in current_gateway_mock.call_args_list],['writer-state','writer-index-status'])
        with patch('generators.writer_agent.jobs.validate_job_request'), patch.object(writer_operations,'call_hermes_writer_service',return_value={'configured':True,'ready':True,'trained':False,'active_job':None}) as current_gateway_mock:
            writer_operations.validate_hermes_writer_request({'mode':'learn','prompt':''})
            self.assertEqual(current_gateway_mock.call_count,1)

    def test_writer_reports_concurrent_document_change_without_paths(self):
        current_job_identifier='20261118-120000-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_998','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            current_reply_value={'id':current_job_identifier,'status':{'stage':'failed','error':'검토 중 원문이 변경되어 /private 오류'}}
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_reply_value):
                current_result_value=writer_operations.read_hermes_writer_status('writer_request_998')
            self.assertIn('원문이 변경',current_result_value['job']['failure_reason'])
            self.assertNotIn('/private',str(current_result_value))

    def test_oversized_writer_apply_receipt_blocks_reapplication(self):
        from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            (current_root_path/'apply_request_123.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            with patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path)),patch.object(writer_operations,'call_hermes_writer_service') as current_writer_mock:
                with self.assertRaises(ValueError):
                    writer_operations.apply_hermes_writer_proposal_once('apply_request_123','writer_request_123','20261118-120000-12345678','a'*64)
                current_writer_mock.assert_not_called()

    def test_apply_approved_proposal_once_and_recover(self):
        from concurrent.futures import ThreadPoolExecutor
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'world/town.md','diff':'-old\n+new'}]}}
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value), patch.object(writer_operations,'call_hermes_writer_service',return_value={'status':'applied','paths':['private']}) as current_apply_mock:
            def submit_current_apply(unused_index_value):
                return writer_operations.apply_hermes_writer_proposal_once('apply_request_123','writer_request_123',current_job_identifier,current_hash_value)
            with ThreadPoolExecutor(max_workers=4) as current_pool_value:
                current_results_list=list(current_pool_value.map(submit_current_apply,range(4)))
            self.assertEqual(sum(not item['duplicate'] for item in current_results_list),1)
            current_apply_mock.assert_called_once_with('writer-apply',{'id':current_job_identifier,'proposal_hash':current_hash_value})
            self.assertNotIn('private',str(current_results_list))
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_request_123')['state'],'completed')
            self.assertEqual(writer_operations.list_writer_apply_receipts()['records'][0]['job_id'],current_job_identifier)
            with self.assertRaises(ValueError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_123','writer_request_123',current_job_identifier,'b'*64)
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_delegation_receipts()['records'],[])

    def test_apply_rejects_mismatched_receipt_and_preserves_changed_record(self):
        import json
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'other','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'world/town.md','diff':'x'}]}}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_record_path=current_store_value.resolve_delegation_record_path('apply_request_123')
            def current_apply_response(current_command_name,current_payload_value):
                current_record_value=json.loads(current_record_path.read_text())
                current_record_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_record_value))
                return {'status':'applied'}
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',side_effect=current_apply_response) as current_apply_mock:
                current_arguments=('apply_request_123','writer_request_123',current_job_identifier,current_hash_value)
                with self.assertRaises(ValueError):writer_operations.apply_hermes_writer_proposal_once(*current_arguments)
                current_apply_mock.assert_not_called()
                current_status_value['receipt']['service']='writer-agent'
                current_status_value['receipt']['request_id']='other_request_123'
                with self.assertRaises(ValueError):writer_operations.apply_hermes_writer_proposal_once(*current_arguments)
                current_apply_mock.assert_not_called()
                current_status_value['receipt']['request_id']='writer_request_123'
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):writer_operations.apply_hermes_writer_proposal_once(*current_arguments)
                self.assertEqual(writer_operations.apply_hermes_writer_proposal_once(*current_arguments)['state'],'unknown')
                current_apply_mock.assert_called_once()
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_apply_rejects_truncated_or_changed_and_preserves_unknown(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':True,'changes':[{'path':'world/town.md','diff':'...'}]}}
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value), patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('lost')) as current_apply_mock:
            with self.assertRaises(ValueError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)
            current_apply_mock.assert_not_called()
            current_status_value['job']['truncated']=False
            with self.assertRaises(OSError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_request_456')['state'],'unknown')
            self.assertTrue(writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)['duplicate'])
            current_apply_mock.assert_called_once()

    def test_apply_different_ids_race_with_existing_delegation(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'example.md','diff':'x'}]}}
        current_start_barrier=threading.Barrier(3)
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',return_value={'status':'applied'}) as current_apply_mock:
                def submit_racing_writer_apply(current_index_value):
                    current_start_barrier.wait(timeout=5)
                    try:
                        return writer_operations.apply_hermes_writer_proposal_once(f'apply_racing_{current_index_value:03d}','writer_request_123',current_job_identifier,current_hash_value)['state']
                    except ValueError as current_error_value:
                        return str(current_error_value)
                with ThreadPoolExecutor(max_workers=3) as current_pool_value:
                    current_result_values=list(current_pool_value.map(submit_racing_writer_apply,range(3)))
                self.assertEqual(current_result_values.count('completed'),1)
                self.assertEqual(sum('기존 적용 접수' in current_result_value for current_result_value in current_result_values),2)
                current_apply_mock.assert_called_once()

    def test_apply_rejects_different_id_for_unknown_proposal(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'example.md','diff':'x'}]}}
        with TemporaryDirectory() as current_root_name,patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('response lost')) as current_apply_mock:
            with self.assertRaises(OSError):writer_operations.apply_hermes_writer_proposal_once('apply_original_123','writer_request_123',current_job_identifier,current_hash_value)
            with self.assertRaisesRegex(ValueError,'기존 적용 접수'):
                writer_operations.apply_hermes_writer_proposal_once('apply_different_123','writer_request_123',current_job_identifier,current_hash_value)
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_original_123')['state'],'unknown')
            current_apply_mock.assert_called_once()

    def test_writer_rejects_unsafe_diff_path(self):
        current_job_identifier='20261118-120000-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_789','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            for current_unsafe_path in ('../private','C:\\private\\secret.md','world/../secret.md','world//town.md','world/secret\nfile.md',''):
                current_reply_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'changes':[{'path':current_unsafe_path,'diff':'x'}]}}
                with self.subTest(path=current_unsafe_path),patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'call_hermes_writer_service',return_value=current_reply_value),self.assertRaises(ValueError):
                    writer_operations.read_hermes_writer_status('writer_request_789')
