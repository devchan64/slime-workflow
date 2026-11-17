import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class FakeHermesMcpServer:
    def __init__(self, *server_argument_values, **server_keyword_values):
        pass
    def tool(self, **tool_keyword_values):
        return lambda current_tool_callback: current_tool_callback


fake_mcp_module = types.ModuleType('mcp')
fake_mcp_server = types.ModuleType('mcp.server')
fake_mcp_internal = types.ModuleType('mcp.server.mcpserver')
fake_mcp_exceptions = types.ModuleType('mcp.server.mcpserver.exceptions')
fake_mcp_types = types.ModuleType('mcp.types')
fake_mcp_server.MCPServer = FakeHermesMcpServer
fake_mcp_exceptions.ToolError = ValueError
fake_mcp_types.ToolAnnotations = lambda **annotation_keyword_values: annotation_keyword_values
hermes_module_path = Path(__file__).resolve().parents[1] / 'domains/hermes_agent/mcp_server.py'
hermes_module_spec = importlib.util.spec_from_file_location('hermes_mcp_test_module', hermes_module_path)
hermes_module_value = importlib.util.module_from_spec(hermes_module_spec)
with patch.dict(sys.modules, {'mcp':fake_mcp_module, 'mcp.server':fake_mcp_server, 'mcp.server.mcpserver':fake_mcp_internal, 'mcp.server.mcpserver.exceptions':fake_mcp_exceptions, 'mcp.types':fake_mcp_types}):
    hermes_module_spec.loader.exec_module(hermes_module_value)


class HermesMcpTests(unittest.TestCase):
    def test_submit_forwards_same_request_identifier_to_gateway(self):
        hermes_response_file = io.BytesIO(b'{"id":"job-id","status":"queued"}')
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = hermes_response_file
            hermes_result_record = hermes_module_value.submit_hermes_coding_task('same-request-1234', '작업')
            hermes_request_object = hermes_opener_mock.return_value.open.call_args.args[0]
        self.assertEqual(hermes_result_record['id'], 'job-id')
        self.assertEqual(json.loads(hermes_request_object.data), {'service':'hermes-agent', 'command':'hermes-submit', 'payload':{'request_id':'same-request-1234', 'prompt':'작업'}})
        self.assertEqual(hermes_request_object.full_url, 'http://127.0.0.1:8771/management/command')

    def test_gpu_queue_status_uses_read_only_loopback_endpoint(self):
        hermes_response_file = io.BytesIO(b'{"jobs":[],"gpu_status":{"status":"unavailable","processes":[]}}')
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = hermes_response_file
            hermes_status_record = hermes_module_value.read_hermes_gpu_queue_status()
            hermes_request_object = hermes_opener_mock.return_value.open.call_args.args[0]
        self.assertEqual(hermes_request_object.get_method(), 'GET')
        self.assertEqual(hermes_request_object.full_url, 'http://127.0.0.1:8771/management/gpu-queue')
        self.assertEqual(hermes_status_record['gpu_status']['status'], 'unavailable')
        self.assertIn('queried_at', hermes_status_record)

    def test_gpu_queue_status_rejects_non_loopback_and_invalid_response(self):
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://example.com:8771'}), self.assertRaises(ValueError):
            hermes_module_value.read_hermes_gpu_queue_status()
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:8771'}), patch.object(hermes_module_value.urllib.request, 'build_opener') as hermes_opener_mock:
            hermes_opener_mock.return_value.open.return_value = io.BytesIO(b'{"jobs":{}}')
            with self.assertRaisesRegex(ValueError, '형식'):
                hermes_module_value.read_hermes_gpu_queue_status()

    def test_capability_catalog_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'records':[]}) as current_gateway_mock:
            hermes_module_value.list_hermes_management_capabilities()
        current_gateway_mock.assert_called_once_with('hermes-capabilities', {})

    def test_delegation_history_uses_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'records':[]}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.list_hermes_delegation_receipts()['records'], [])
        current_gateway_mock.assert_called_once_with('hermes-delegation-history', {})

    def test_delegated_job_status_uses_receipt_command(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'receipt':{'state':'unknown'}}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_kimodo_job_status('request_123456')['receipt']['state'], 'unknown')
        current_gateway_mock.assert_called_once_with('hermes-delegation-job-status', {'request_id':'request_123456'})

    def test_cancel_forwards_confirmed_request_and_job(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'cancel_requested':True}) as current_gateway_mock:
            hermes_module_value.cancel_hermes_kimodo_delegation('request_123456', 'job-1')
        current_gateway_mock.assert_called_once_with('hermes-delegation-cancel', {'request_id':'request_123456', 'job_id':'job-1'})

    def test_delegation_receipt_is_read_without_submission(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'state':'unknown'}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_delegation_status('request_123456')['state'], 'unknown')
        current_gateway_mock.assert_called_once_with('hermes-delegation-status', {'request_id':'request_123456'})

    def test_kimodo_proposal_is_read_through_shared_gateway(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'proposal':{}}) as current_gateway_mock:
            hermes_module_value.read_hermes_kimodo_proposal('job-1')
        current_gateway_mock.assert_called_once_with('hermes-kimodo-proposal', {'id':'job-1'})

    def test_kimodo_delegation_uses_shared_gateway_without_waiting(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}) as current_gateway_mock:
            current_result_value = hermes_module_value.delegate_hermes_kimodo_generation('request_123456', {'action':'generate'})
        self.assertEqual(current_result_value['state'], 'accepted')
        current_gateway_mock.assert_called_once_with('hermes-delegate-kimodo', {'request_id':'request_123456', 'request':{'action':'generate'}})

    def test_management_status_uses_shared_gateway_command(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'model': {'status':'unavailable'}}) as current_gateway_mock:
            self.assertEqual(hermes_module_value.read_hermes_management_status()['model']['status'], 'unavailable')
            current_gateway_mock.assert_called_once_with('hermes-management-status', {})

    def test_session_tools_use_shared_gateway_commands(self):
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'id':'a' * 32}) as hermes_gateway_mock:
            hermes_module_value.create_hermes_session('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-create', {'session_id':'a' * 32})
            hermes_module_value.read_hermes_session('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-read', {'session_id':'a' * 32})
            hermes_module_value.submit_hermes_session_message('a' * 32, 'request-1234', '질문')
            hermes_gateway_mock.assert_called_with('hermes-session-submit', {'session_id':'a' * 32, 'request_id':'request-1234', 'prompt':'질문'})
            hermes_module_value.read_hermes_session_view('a' * 32)
            hermes_gateway_mock.assert_called_with('hermes-session-view', {'session_id':'a' * 32})
            hermes_module_value.list_hermes_sessions()
            hermes_gateway_mock.assert_called_with('hermes-session-list', {})

    def test_non_loopback_gateway_is_rejected(self):
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://example.com:8771'}), self.assertRaises(ValueError):
            hermes_module_value.list_hermes_coding_tasks()

    def test_gateway_redirect_is_rejected(self):
        with self.assertRaises(ValueError):
            hermes_module_value.RejectHermesGatewayRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com/')

    def test_submit_forwards_selected_verification_modules(self):
        hermes_module_values = ['tools.review.tests.test_hermes_service']
        with patch.object(hermes_module_value, 'call_hermes_management_gateway', return_value={'id':'job-id'}) as hermes_gateway_mock:
            hermes_module_value.submit_hermes_coding_task('request-1234', '테스트', hermes_module_values)
            hermes_gateway_mock.assert_called_once_with('hermes-submit', {'request_id':'request-1234', 'prompt':'테스트', 'verification_modules':hermes_module_values})


if __name__ == '__main__':
    unittest.main()
