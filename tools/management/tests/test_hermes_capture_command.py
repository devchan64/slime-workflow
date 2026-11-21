import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.management.common.management_gateway import resolve_management_command, identify_management_command
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.management.domains.hermes_agent.service import HermesServiceManager
from tools.management.tests.test_hermes_mcp import hermes_module_value


class HermesCaptureCommandTests(unittest.TestCase):
    def test_capture_display_labels_preserve_identifiers_and_settings(self):
        from tools.management.ui.gradio.hermes_agent_app import format_capture_settings_for_conversation
        current_display_text=format_capture_settings_for_conversation({'map':'contrast','show_character':True,'edges':False,'width':768,'ground':'grass'})
        self.assertIn('맵 ID: contrast',current_display_text)
        self.assertIn('캐릭터 표시: 켜짐',current_display_text)
        self.assertIn('경계 표시: 꺼짐',current_display_text)
        self.assertIn('너비: 768',current_display_text)
        self.assertIn('바닥: 풀',current_display_text)

    def test_chat_shows_validated_capture_settings_and_execution_limit(self):
        from tools.management.ui.gradio.hermes_agent_app import format_hermes_conversation_answer
        current_answer_text='검토하세요.\nHERMES_CAPTURE_PROPOSAL\n{"service":"map-review","settings":{"map":"ash-edge"}}\nEND_HERMES_CAPTURE_PROPOSAL'
        current_display_value=format_hermes_conversation_answer(current_answer_text)
        self.assertIn('맵 검수 캡처',current_display_value)
        self.assertIn('ash-edge',current_display_value)
        self.assertIn('실행은 지원하지 않습니다',current_display_value)
        self.assertIn('맵 등록 여부는 별도 확인이 필요합니다',current_display_value)
        self.assertIn('도구 탐색에서 맵 검수 화면을 열어',current_display_value)
        self.assertIn('GPU를 사용할 수 있습니다',current_display_value)
        current_character_answer='HERMES_CAPTURE_PROPOSAL\n{"service":"character-review","settings":{}}\nEND_HERMES_CAPTURE_PROPOSAL'
        current_character_display=format_hermes_conversation_answer(current_character_answer)
        self.assertIn('캐릭터 표현 검수 화면은 폐기',current_character_display)
        self.assertIn('현재 대기 항목에서 확인된 캡처 접수만 상태를 조회',current_character_display)
        self.assertIn('그 밖의 기록과 결과는 기존 원 서비스에서 확인',current_character_display)
        self.assertNotIn('HERMES_CAPTURE_PROPOSAL',current_display_value)
        self.assertEqual(format_hermes_conversation_answer(current_answer_text,True),current_answer_text)

    def test_capture_proposal_requires_valid_single_block_and_completed_job(self):
        from tools.management.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
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

    def test_capture_map_registration_distinguishes_missing_and_unavailable(self):
        from tools.management.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
        current_proposal_record={'service':'map-review','settings':{'map':'test-map'}}
        for current_menu_records,current_expected_state in (([{'id':'test-map'}],'registered'),([{'id':'other'}],'not_registered'),([{'id':'test-map'},{'id':'test-map'}],'unavailable'),([{}],'unavailable')):
            with self.subTest(state=current_expected_state),patch('tools.management.common.map_asset_sources.load_review_map_menu',return_value=current_menu_records),patch('tools.management.domains.map_review.capture.capture_map_review',side_effect=AssertionError('캡처 금지')):
                self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':current_expected_state,'map':'test-map'})
        with patch('tools.management.common.map_asset_sources.load_review_map_menu',side_effect=OSError('private path')):
            self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})
        self.assertEqual(inspect_capture_map_registration({'service':'character-review','settings':{}}),{'status':'not_applicable'})
        import yaml
        with patch('tools.management.common.map_asset_sources.load_review_map_menu',side_effect=yaml.YAMLError('손상된 원본')):
            self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})

    def test_capture_map_registration_rejects_overlapping_scans(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from tools.management.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
        current_entered_event=Event()
        current_release_event=Event()
        def hold_test_map_menu():
            current_entered_event.set()
            if not current_release_event.wait(5):raise RuntimeError('모의 조회 시간 초과')
            return [{'id':'test-map'}]
        current_proposal_record={'service':'map-review','settings':{'map':'test-map'}}
        with patch('tools.management.common.map_asset_sources.load_review_map_menu',side_effect=hold_test_map_menu) as current_menu_mock,ThreadPoolExecutor(max_workers=1) as current_executor:
            current_first_result=current_executor.submit(inspect_capture_map_registration,current_proposal_record)
            try:
                self.assertTrue(current_entered_event.wait(5))
                self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})
                self.assertEqual(current_menu_mock.call_count,1)
            finally:
                current_release_event.set()
            self.assertEqual(current_first_result.result(timeout=5)['status'],'registered')
            self.assertEqual(inspect_capture_map_registration(current_proposal_record)['status'],'registered')

    def test_conversation_capture_review_is_read_only_and_checks_job_identity(self):
        from tools.management.ui.gradio import hermes_agent_app
        from tools.management.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
        current_answer_text='HERMES_CAPTURE_PROPOSAL\n{"service":"map-review","settings":{"map":"test-map"}}\nEND_HERMES_CAPTURE_PROPOSAL'
        current_proposal_value=parse_hermes_capture_proposal(current_answer_text)
        current_job_record={'job':{'final_response':current_answer_text,'final_response_truncated':False}}
        current_response_record={'job_id':'job-1','proposal':current_proposal_value,'map_registration':{'status':'registered','map':'test-map'}}
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response_record) as current_gateway_mock:
            current_route_values=hermes_agent_app.route_conversation_proposal('session-1','job-1')
            self.assertEqual(current_route_values[-2]['area'],'capture')
            current_route_record=current_route_values[-2]
            current_output_values=hermes_agent_app.open_routed_conversation_proposal(current_route_record,'session-1','job-1')
            self.assertIn('확인하고 있습니다',current_output_values[-1])
            current_result_record=hermes_agent_app.collect_routed_capture_review(current_route_record,'session-1','job-1')
            current_notice_text=hermes_agent_app.render_routed_capture_review(current_route_record,'session-1','job-1',current_result_record)
            self.assertIn('등록된 맵',current_notice_text)
            self.assertIn('캡처 실행은 지원하지 않으며',current_notice_text)
            current_session_identifier='a'*32
            current_link_notice=hermes_agent_app.read_conversation_capture_review(current_session_identifier,'job-1')
            self.assertIn('/management/frame/map-review/?map=test-map&townPage=1&session='+current_session_identifier,current_link_notice)
            current_gateway_mock.assert_called_with('hermes-agent','hermes-capture-proposal',{'id':'job-1'})
            import gradio as gr
            self.assertEqual(hermes_agent_app.render_routed_capture_review(None,'session-1','job-1',current_result_record),gr.skip())
            self.assertEqual(hermes_agent_app.render_routed_capture_review({**current_route_record,'nonce':'new'},'session-1','job-1',current_result_record),gr.skip())
            self.assertEqual(hermes_agent_app.render_routed_capture_review(current_route_record,'session-1','other-job',current_result_record),gr.skip())
            for current_state_name,current_expected_text in (('not_registered','등록 맵 목록에 없음'),('unavailable','등록 여부 확인 불가')):
                current_response_record['map_registration']={'status':current_state_name,'map':'test-map'}
                current_result_record=hermes_agent_app.collect_routed_capture_review(current_route_record,'session-1','job-1')
                self.assertIn(current_expected_text,current_result_record['notice'])
                self.assertNotIn('/management/frame/map-review/',current_result_record['notice'])
                self.assertIn('캡처 실행은 지원하지 않으며',current_result_record['notice'])
            current_response_record['map_registration']={'status':'registered','map':'other'}
            current_result_record=hermes_agent_app.collect_routed_capture_review(current_route_record,'session-1','job-1')
            self.assertIn('확인하지 못했습니다',current_result_record['notice'])

    def test_mcp_capture_proposal_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_proposal('job-1')
            current_gateway_mock.assert_called_once_with('hermes-capture-proposal',{'id':'job-1'})

    def test_sandbox_bridge_reads_verified_queued_capture_from_temp_records(self):
        import json
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        from tools.management.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once, normalize_capture_delegation_request
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_job_identifier='2026-11-20_00-00-00-12345678'
            current_job_path=current_root_path/'.tmp'/'test'/'review-capture'/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_settings_value=normalize_capture_delegation_request('map-review',{'map':'ash-edge'})
            prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},lambda current_request_value:{'id':current_job_identifier})
            (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':current_settings_value}))
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'review-capture','command':['python','-m','tools.management.domains.hermes_agent.capture_worker','--job-dir',str(current_job_path)]}))
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            current_client_socket,current_server_socket=socket.socketpair()
            self.addCleanup(current_client_socket.close)
            with patch('tools.management.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value),patch('tools.management.common.management_environment.WORKFLOW_ROOT_DIRECTORY',current_root_path):
                current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_value.start()
                current_client_socket.sendall(b'capture-status {"service":"map-review","request_id":"request_123"}\n')
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_value.join(timeout=3)
            self.assertEqual(current_response_value['receipt']['job_id'],current_job_identifier)
            self.assertEqual(current_response_value['job'],{'status':'queued','result_available':False})
            self.assertNotIn(str(current_root_path),json.dumps(current_response_value))

    def test_sandbox_capture_map_check_only_reads_valid_map(self):
        import json
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_request_values=((b'capture-map-check {"map":"test-map"}\n',True),(b'capture-map-check {"map":"../bad"}\n',False),(b'capture-map-check {"map":"test-map","action":"capture"}\n',False),(b'capture-map-check {"map":"one","map":"two"}\n',False))
        for current_request_bytes,current_allowed_value in current_request_values:
            with self.subTest(request=current_request_bytes),patch('tools.management.common.map_asset_sources.load_review_map_menu',return_value=[{'id':'test-map'}]) as current_menu_mock,patch('tools.management.domains.map_review.capture.capture_map_review',side_effect=AssertionError('캡처 금지')) as current_capture_mock:
                current_client_socket,current_server_socket=socket.socketpair()
                current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                current_thread_value.start()
                with current_client_socket:
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread_value.join(timeout=3)
                self.assertFalse(current_thread_value.is_alive())
                self.assertIn('status' if current_allowed_value else 'error',current_response_value)
                self.assertEqual(current_menu_mock.call_count,int(current_allowed_value))
                current_capture_mock.assert_not_called()

    def test_sandbox_capture_map_client_sends_fixed_request(self):
        from tools.management.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('tools.management.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
            current_socket_value=current_socket_factory.return_value.__enter__.return_value
            current_socket_value.recv.return_value=b'{"status":"registered","map":"test-map"}\n'
            current_result_value=read_sandbox_management_status('capture-map-check','{"map":"test-map"}')
            self.assertEqual(current_result_value['status'],'registered')
            current_socket_value.sendall.assert_called_once_with(b'capture-map-check {"map":"test-map"}\n')
        with self.assertRaises(ValueError):read_sandbox_management_status('capture-map-check','{}\nrun shell')

    def test_sandbox_bridge_allows_only_capture_status_contract(self):
        import json
        import socket
        import threading
        from tools.management.domains.hermes_agent import management_bridge
        current_requests=((b'capture-status {"service":"map-review","request_id":"request_123"}\n',True),(b'capture-status {"service":"map-review","request_id":"request_123","action":"execute"}\n',False),(b'capture-status {"service":"map-review","service":"character-review","request_id":"request_123"}\n',False),(b'capture-execute {}\n',False))
        for current_request_bytes,current_allowed_value in current_requests:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('tools.management.domains.hermes_agent.capture_status.read_capture_delegation_status',return_value={'receipt':{'state':'not_found'},'job':None}) as current_status_mock:
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_value.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_value.join(timeout=3)
                    self.assertEqual(current_status_mock.call_count,int(current_allowed_value))
                    self.assertIn('receipt' if current_allowed_value else 'error',current_response_value)

    def test_discovery_links_status_but_keeps_capture_execution_restricted(self):
        from tools.management.domains.hermes_agent.capabilities import list_management_service_registration
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
            with patch('tools.management.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value):
                current_result_value=current_manager_value.execute_hermes_command('hermes-capture-status',current_payload_value)
                self.assertEqual(current_result_value['receipt']['state'],'not_found')
                self.assertIsNone(current_result_value['job'])
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{'request_id':'request_123','service':'unsupported'})
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{**current_payload_value,'extra':True})

    def test_mcp_uses_fixed_status_command_without_input_payload(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_status('request_123','map-review')
            current_gateway_mock.assert_called_once_with('hermes-capture-status',{'request_id':'request_123','service':'map-review'})
