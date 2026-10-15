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
