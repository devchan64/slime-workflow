"""격리 HTTP 게이트웨이 재시작 뒤 Hermes 기록과 중복 방지 확인."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

from tools.review.common.management_gateway import ManagementCommandGateway
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.service import HermesServiceManager
from tools.review.gateway_server import create_gateway_request_handler


class HermesGatewayRestartTests(unittest.TestCase):
    def test_restart_preserves_sessions_receipts_and_prevents_relaunch(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_root_path = Path(current_temp_root)
            current_store_path = current_root_path / 'delegations'
            current_store_value = HermesDelegationStore(current_store_path)
            current_request_value = {'action':'generate', 'prompt':'테스트'}
            current_store_value.execute_delegation_once('receipt_123456', {'service':'kimodo', 'request':current_request_value}, Mock(return_value={'id':'2026-11-18_00-00-00-12345678'}))
            with self.assertRaises(TimeoutError):
                current_store_value.execute_delegation_once('unknown_123456', {}, Mock(side_effect=TimeoutError()))
            current_session_identifier = 'a' * 32
            current_session_payload = {'session_id':current_session_identifier, 'request_id':'session_123456', 'prompt':'재시작 시험'}

            def start_test_gateway():
                current_service_value = HermesServiceManager(current_root_path / 'jobs', current_root_path / 'sessions')
                current_gateway_value = ManagementCommandGateway({'hermes-agent':current_service_value.handle_hermes_request})
                current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), create_gateway_request_handler(current_gateway_value.handle))
                current_server_value.emit_gateway_trace = lambda *current_values: None
                current_thread_value = threading.Thread(target=current_server_value.serve_forever, daemon=True)
                current_thread_value.start()
                return current_server_value, current_thread_value

            def request_test_command(current_server_value, current_command_name, current_payload_value):
                current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
                current_body_value = json.dumps({'service':'hermes-agent', 'command':current_command_name, 'payload':current_payload_value}, ensure_ascii=False).encode()
                current_request_object = Request(current_address_value + '/management/command', data=current_body_value, headers={'Content-Type':'application/json','Origin':current_address_value}, method='POST')
                with urlopen(current_request_object, timeout=5) as current_response_value:
                    return json.load(current_response_value)

            def stop_test_gateway(current_server_value, current_thread_value):
                current_server_value.shutdown()
                current_thread_value.join(timeout=5)
                current_server_value.server_close()
                self.assertFalse(current_thread_value.is_alive())

            with patch('tools.review.domains.hermes_agent.service.validate_hermes_runtime_ready'), patch('tools.review.domains.hermes_agent.service.launch_gpu_process') as current_launch_mock, patch('tools.review.domains.hermes_agent.delegation_store.HermesDelegationStore', side_effect=lambda: HermesDelegationStore(current_store_path)):
                current_server_value, current_thread_value = start_test_gateway()
                try:
                    current_address_value = f'http://127.0.0.1:{current_server_value.server_port}'
                    current_denied_body = json.dumps({'service':'hermes-agent','command':'hermes-session-create','payload':{'session_id':'b' * 32}}).encode()
                    current_denied_request = Request(current_address_value + '/management/command', data=current_denied_body, headers={'Content-Type':'application/json','Origin':'http://other.invalid'}, method='POST')
                    with self.assertRaises(HTTPError) as current_denied_error:
                        urlopen(current_denied_request, timeout=5)
                    self.assertEqual(current_denied_error.exception.code, 400)
                    self.assertFalse((current_root_path / 'sessions' / ('b' * 32 + '.json')).exists())
                    request_test_command(current_server_value, 'hermes-session-create', {'session_id':current_session_identifier})
                    current_first_result = request_test_command(current_server_value, 'hermes-session-submit', current_session_payload)
                    self.assertFalse(current_first_result['duplicate'])
                finally:
                    stop_test_gateway(current_server_value, current_thread_value)
                current_server_value, current_thread_value = start_test_gateway()
                try:
                    current_retry_result = request_test_command(current_server_value, 'hermes-session-submit', current_session_payload)
                    self.assertTrue(current_retry_result['duplicate'])
                    self.assertEqual(current_retry_result['job_id'], current_first_result['job_id'])
                    self.assertEqual(request_test_command(current_server_value, 'hermes-session-read', {'session_id':current_session_identifier})['messages'][0]['job_id'], current_first_result['job_id'])
                    current_receipt_value = request_test_command(current_server_value, 'hermes-delegate-kimodo', {'request_id':'receipt_123456', 'request':current_request_value})
                    self.assertTrue(current_receipt_value['duplicate'])
                    self.assertEqual(current_receipt_value['job_id'], '2026-11-18_00-00-00-12345678')
                    self.assertEqual(request_test_command(current_server_value, 'hermes-delegation-status', {'request_id':'unknown_123456'})['state'], 'unknown')
                    with self.assertRaises(HTTPError) as current_error_value:
                        request_test_command(current_server_value, 'hermes-session-submit', {**current_session_payload, 'prompt':'다른 지시'})
                    self.assertEqual(current_error_value.exception.code, 400)
                finally:
                    stop_test_gateway(current_server_value, current_thread_value)
            current_launch_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
