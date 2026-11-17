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
