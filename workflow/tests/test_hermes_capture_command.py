import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common.management_gateway import resolve_management_command, identify_management_command
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.tests.test_hermes_mcp import hermes_module_value


class HermesCaptureCommandTests(unittest.TestCase):
    def test_capture_proposal_display_and_real_map_link(self):
        import os,subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'capture.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'CaptureProposal.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');const {CaptureProposalReview}=require(process.argv[1]);
            const session='a'.repeat(32);const render=(proposal,registration)=>server.renderToStaticMarkup(React.createElement(CaptureProposalReview,{session,value:{proposal,registration}}));
            const proposal={service:'map-review',settings:{map:'ash-edge',show_character:true,edges:false}};
            const registered=render(proposal,{status:'registered',map:'ash-edge'}),missing=render(proposal,{status:'not_registered',map:'ash-edge'});
            const retired=render({service:'character-review',settings:{width:768,ground:'grass'}},{status:'not_applicable'});
            if(!registered.includes('맵 ID') || !registered.includes('ash-edge') || !registered.includes('켜짐') || !registered.includes('꺼짐') || !registered.includes('/management/frame/map-review/') || !registered.includes('session='+session) || !registered.includes('캡처 실행은 지원하지 않습니다'))throw Error(registered);
            if(missing.includes('/management/frame/map-review/') || !missing.includes('등록 맵 목록에 없음'))throw Error(missing);
            if(!retired.includes('폐기') || !retired.includes('768') || !retired.includes('풀'))throw Error(retired);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_capture_proposal_requires_valid_single_block_and_completed_job(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
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
                with patch('workflow.common.map_asset_sources.load_review_map_menu',return_value=[{'id':'ash-edge'}]):
                    current_response=current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})
                self.assertEqual(current_response['proposal'],current_proposal_value)
                self.assertEqual(current_response['map_registration'],{'status':'registered','map':'ash-edge'})
                current_job_record['final_response_truncated']=True
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})
                current_job_record['final_response_truncated']=False
                current_job_record['status']['status']='running'
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-proposal',{'id':'job-1'})

    def test_capture_map_registration_distinguishes_missing_and_unavailable(self):
        from workflow.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
        current_proposal_record={'service':'map-review','settings':{'map':'test-map'}}
        for current_menu_records,current_expected_state in (([{'id':'test-map'}],'registered'),([{'id':'other'}],'not_registered'),([{'id':'test-map'},{'id':'test-map'}],'unavailable'),([{}],'unavailable')):
            with self.subTest(state=current_expected_state),patch('workflow.common.map_asset_sources.load_review_map_menu',return_value=current_menu_records),patch('workflow.domains.map_review.capture.capture_map_review',side_effect=AssertionError('캡처 금지')):
                self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':current_expected_state,'map':'test-map'})
        with patch('workflow.common.map_asset_sources.load_review_map_menu',side_effect=OSError('private path')):
            self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})
        self.assertEqual(inspect_capture_map_registration({'service':'character-review','settings':{}}),{'status':'not_applicable'})
        import yaml
        with patch('workflow.common.map_asset_sources.load_review_map_menu',side_effect=yaml.YAMLError('손상된 원본')):
            self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})

    def test_capture_map_registration_rejects_overlapping_scans(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from workflow.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
        current_entered_event=Event()
        current_release_event=Event()
        def hold_test_map_menu():
            current_entered_event.set()
            if not current_release_event.wait(5):raise RuntimeError('모의 조회 시간 초과')
            return [{'id':'test-map'}]
        current_proposal_record={'service':'map-review','settings':{'map':'test-map'}}
        with patch('workflow.common.map_asset_sources.load_review_map_menu',side_effect=hold_test_map_menu) as current_menu_mock,ThreadPoolExecutor(max_workers=1) as current_executor:
            current_first_result=current_executor.submit(inspect_capture_map_registration,current_proposal_record)
            try:
                self.assertTrue(current_entered_event.wait(5))
                self.assertEqual(inspect_capture_map_registration(current_proposal_record),{'status':'unavailable','map':'test-map'})
                self.assertEqual(current_menu_mock.call_count,1)
            finally:
                current_release_event.set()
            self.assertEqual(current_first_result.result(timeout=5)['status'],'registered')
            self.assertEqual(inspect_capture_map_registration(current_proposal_record)['status'],'registered')

    def test_mcp_capture_proposal_uses_fixed_command(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_proposal('job-1')
            current_gateway_mock.assert_called_once_with('hermes-capture-proposal',{'id':'job-1'})

    def test_sandbox_bridge_reads_verified_queued_capture_from_temp_records(self):
        import json
        import socket
        import threading
        from workflow.domains.hermes_agent import management_bridge
        from workflow.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once, normalize_capture_delegation_request
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_job_identifier='2026-11-20_00-00-00-12345678'
            current_job_path=current_root_path/'.tmp'/'test'/'review-capture'/current_job_identifier
            current_job_path.mkdir(parents=True)
            current_settings_value=normalize_capture_delegation_request('map-review',{'map':'ash-edge'})
            prepare_capture_delegation_once(current_store_value,'request_123','map-review',{'map':'ash-edge'},lambda current_request_value:{'id':current_job_identifier})
            (current_job_path/'request.json').write_text(json.dumps({'request_id':'request_123','service':'map-review','settings':current_settings_value}))
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'review-capture','command':['python','-m','workflow.domains.hermes_agent.capture_worker','--job-dir',str(current_job_path)]}))
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            current_client_socket,current_server_socket=socket.socketpair()
            self.addCleanup(current_client_socket.close)
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value),patch('workflow.common.management_environment.WORKFLOW_ROOT_DIRECTORY',current_root_path):
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
        from workflow.domains.hermes_agent import management_bridge
        current_request_values=((b'capture-map-check {"map":"test-map"}\n',True),(b'capture-map-check {"map":"../bad"}\n',False),(b'capture-map-check {"map":"test-map","action":"capture"}\n',False),(b'capture-map-check {"map":"one","map":"two"}\n',False))
        for current_request_bytes,current_allowed_value in current_request_values:
            with self.subTest(request=current_request_bytes),patch('workflow.common.map_asset_sources.load_review_map_menu',return_value=[{'id':'test-map'}]) as current_menu_mock,patch('workflow.domains.map_review.capture.capture_map_review',side_effect=AssertionError('캡처 금지')) as current_capture_mock:
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
        from workflow.domains.hermes_agent.management_status_client import read_sandbox_management_status
        with patch('workflow.domains.hermes_agent.management_status_client.socket.socket') as current_socket_factory:
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
        from workflow.domains.hermes_agent import management_bridge
        current_requests=((b'capture-status {"service":"map-review","request_id":"request_123"}\n',True),(b'capture-status {"service":"map-review","request_id":"request_123","action":"execute"}\n',False),(b'capture-status {"service":"map-review","service":"character-review","request_id":"request_123"}\n',False),(b'capture-execute {}\n',False))
        for current_request_bytes,current_allowed_value in current_requests:
            with self.subTest(request=current_request_bytes):
                current_client_socket,current_server_socket=socket.socketpair()
                self.addCleanup(current_client_socket.close)
                with patch('workflow.domains.hermes_agent.capture_status.read_capture_delegation_status',return_value={'receipt':{'state':'not_found'},'job':None}) as current_status_mock:
                    current_thread_value=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,))
                    current_thread_value.start()
                    current_client_socket.sendall(current_request_bytes)
                    current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                    current_thread_value.join(timeout=3)
                    self.assertEqual(current_status_mock.call_count,int(current_allowed_value))
                    self.assertIn('receipt' if current_allowed_value else 'error',current_response_value)

    def test_discovery_links_status_but_keeps_capture_execution_restricted(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
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
            with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store_value):
                current_result_value=current_manager_value.execute_hermes_command('hermes-capture-status',current_payload_value)
                self.assertEqual(current_result_value['receipt']['state'],'not_found')
                self.assertIsNone(current_result_value['job'])
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{'request_id':'request_123','service':'unsupported'})
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-capture-status',{**current_payload_value,'extra':True})

    def test_mcp_uses_fixed_status_command_without_input_payload(self):
        with patch.object(hermes_module_value,'call_hermes_management_gateway',return_value={}) as current_gateway_mock:
            hermes_module_value.read_hermes_capture_status('request_123','map-review')
            current_gateway_mock.assert_called_once_with('hermes-capture-status',{'request_id':'request_123','service':'map-review'})
