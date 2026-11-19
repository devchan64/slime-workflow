import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.review.common.management_gateway import resolve_management_command, identify_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.service import HermesServiceManager
from tools.review.tests.test_hermes_mcp import hermes_module_value


class HermesCaptureCommandTests(unittest.TestCase):
    def test_capture_display_labels_preserve_identifiers_and_settings(self):
        from tools.review.ui.gradio.hermes_agent_app import format_capture_settings_for_conversation
        current_display_text=format_capture_settings_for_conversation({'map':'contrast','show_character':True,'edges':False,'width':768,'ground':'grass'})
        self.assertIn('맵 ID: contrast',current_display_text)
        self.assertIn('캐릭터 표시: 켜짐',current_display_text)
        self.assertIn('경계 표시: 꺼짐',current_display_text)
        self.assertIn('너비: 768',current_display_text)
        self.assertIn('바닥: 풀',current_display_text)

    def test_chat_shows_validated_capture_settings_and_execution_limit(self):
        from tools.review.ui.gradio.hermes_agent_app import format_hermes_conversation_answer
        current_answer_text='검토하세요.\nHERMES_CAPTURE_PROPOSAL\n{"service":"map-review","settings":{"map":"ash-edge"}}\nEND_HERMES_CAPTURE_PROPOSAL'
        current_display_value=format_hermes_conversation_answer(current_answer_text)
        self.assertIn('맵 검수 캡처',current_display_value)
        self.assertIn('ash-edge',current_display_value)
        self.assertIn('실행은 지원하지 않습니다',current_display_value)
        self.assertIn('맵 등록 여부는 별도 확인이 필요합니다',current_display_value)
        self.assertNotIn('HERMES_CAPTURE_PROPOSAL',current_display_value)
        self.assertEqual(format_hermes_conversation_answer(current_answer_text,True),current_answer_text)

    def test_capture_proposal_requires_valid_single_block_and_completed_job(self):
        from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
        current_answer_text='검토 제안\nHERMES_CAPTURE_PROPOSAL\n{"service":"map-review","settings":{"map":"ash-edge"}}\nEND_HERMES_CAPTURE_PROPOSAL'
        current_proposal_value=parse_hermes_capture_proposal(current_answer_text)
        self.assertEqual(current_proposal_value['settings']['map'],'ash-edge')
        self.assertFalse(current_proposal_value['settings']['edges'])
        for current_invalid_text in (current_answer_text+'\n'+current_answer_text,current_answer_text.replace('ash-edge','../bad'),current_answer_text.replace('"map":"ash-edge"','"map":"ash-edge","map":"other"'),current_answer_text.replace('map-review','unsupported')):
            with self.subTest(value=current_invalid_text),self.assertRaises(ValueError):parse_hermes_capture_proposal(current_invalid_text)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_job_record={'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}
            with patch.object(current_manager_value,'resolve_hermes_job_path',return_value=current_root_path),patch.object(current_manager_value,'read_hermes_job_record',return_value=current_job_record):
                self.assertEqual(current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})['proposal'],current_proposal_value)
                current_job_record['final_response_truncated']=True
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})
                current_job_record['final_response_truncated']=False
                current_job_record['status']['status']='running'
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})

    def test_mcp_capture_proposal_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_proposal('job-1')
            current_gateway_mock.assert_called_once_with('hermes-capture-proposal',{'id':'job-1'})

    def test_sandbox_bridge_reads_verified_queued_capture_from_temp_records(self):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        from tools.review.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once, normalize_capture_delegation_request
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_job_identifier='2026-11-20_00-00-00-12345678'
            current_job_path=current_root_path/'.tmp'/'test'/'review-capture'/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_settings_value=normalize_capture_delegation_request('map-review',{'map':'ash-edge'})
            prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},lambda current_request_value:{'id':current_job_identifier})
            (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':current_settings_value}))
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'review-capture','command':['python','-m','tools.review.domains.hermes_agent.capture_worker','--job-dir',str(current_job_path)]}))
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            current_client_socket,current_server_socket=socket.socketpair()
            self.addCleanup(current_client_socket.close)
            with patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value),patch('tools.review.common.management_environment.WORKFLOW_ROOT_DIRECTORY',current_root_path):
                current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_value.start()
                current_client_socket.sendall(b'capture-status {"service":"map-review","request_id":"request_123"}\n')
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_value.join(timeout=3)
            self.assertEqual(current_response_value['receipt']['job_id'],current_job_identifier)
            self.assertEqual(current_response_value['job'],{'status':'queued','result_available':False})
            self.assertNotIn(str(current_root_path),json.dumps(current_response_value))

    def test_sandbox_bridge_allows_only_capture_status_contract(self):
        import json
        import socket
        import threading
        from tools.review.domains.hermes_agent import management_bridge
        current_requests=((b'capture-status {"service":"map-review","request_id":"request_123"}\n',True),(b'capture-status {"service":"map-review","request_id":"request_123","action":"execute"}\n',False),(b'capture-status {"service":"map-review","service":"character-review","request_id":"request_123"}\n',False),(b'capture-execute {}\n',False))
        for current_request_bytes,current_allowed_value in current_requests:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.review.domains.hermes_agent.capture_status.read_capture_delegation_status',return_value={'receipt':{'state':'not_found'},'job':None}) as current_status_mock:
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_value.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_value.join(timeout=3)
                    self.assertEqual(current_status_mock.call_count,int(current_allowed_value))
                    self.assertIn('receipt' if current_allowed_value else 'error',current_response_value)

    def test_discovery_links_status_but_keeps_capture_execution_restricted(self):
        from tools.review.domains.hermes_agent.capabilities import list_management_service_registration
        current_catalog_value=list_management_service_registration()
        current_services_value={current_record['service']:current_record for current_record in current_catalog_value['services']}
        for current_service_name in ('map-review','character-review'):
            with self.subTest(service=current_service_name):
                current_service_record=current_services_value[current_service_name]
                self.assertIn('hermes-capture-status',current_service_record['hermes_links'])
                self.assertIn('hermes-capture-proposal',current_service_record['hermes_links'])
                self.assertTrue(any(current_limit['command']=='capture' and '실행하지 않는다' in current_limit['note'] for current_limit in current_service_record['conditional_limitations']))

    def test_gateway_and_service_read_missing_receipt_without_execution(self):
        current_payload_value={'request_id':'request_123','service':'map-review'}
        current_method_name,current_route_path=resolve_management_command('hermes-agent','hermes-capture-status',current_payload_value)
        self.assertEqual(identify_management_command(current_route_path,current_method_name,current_payload_value),('hermes-agent','hermes-capture-status',current_payload_value))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            with patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value):
                current_result_value=current_manager_value.execute_hermes_command('hermes-capture-status',current_payload_value)
                self.assertEqual(current_result_value['receipt']['state'],'not_found')
                self.assertIsNone(current_result_value['job'])
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{'request_id':'request_123','service':'unsupported'})
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{**current_payload_value,'extra':True})

    def test_mcp_uses_fixed_status_command_without_input_payload(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_status('request_123','map-review')
            current_gateway_mock.assert_called_once_with('hermes-capture-status',{'request_id':'request_123','service':'map-review'})
