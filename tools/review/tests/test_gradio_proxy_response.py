import unittest
from email.message import Message

from tools.review.serve import write_proxy_response_body, build_gradio_proxy_headers


class ClosedBrowserOutput:
    def write(self, response_body_bytes):
        raise BrokenPipeError('browser closed the connection')


class GradioProxyResponseTest(unittest.TestCase):
    def test_public_origin_survives_internal_gradio_proxy(self):
        from fastapi import Request
        from gradio.route_utils import get_root_url
        incoming_headers = Message()
        incoming_headers['Host'] = '127.0.0.1:8770'
        incoming_headers['X-Forwarded-Host'] = 'untrusted.example'
        incoming_headers['Cookie'] = 'session=test'
        headers = build_gradio_proxy_headers(incoming_headers)
        request = Request({'type': 'http', 'scheme': 'http', 'path': '/config',
                           'query_string': b'', 'server': ('127.0.0.1', 8875),
                           'headers': [(name.lower().encode(), value.encode()) for name, value in headers.items()]})
        self.assertEqual(headers['Host'], '127.0.0.1:8770')
        self.assertEqual(headers['Cookie'], 'session=test')
        self.assertEqual(get_root_url(request, '/config', '/management/frame/tile-map-generator/'),
                         'http://127.0.0.1:8770/management/frame/tile-map-generator')

    def test_ignores_closed_browser_connection(self):
        self.assertFalse(write_proxy_response_body(ClosedBrowserOutput(), b'payload'))

class GradioStartupFailureTests(unittest.TestCase):
    def test_startup_failure_is_handled_without_static_asset_fallback(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock
        from urllib.parse import urlsplit
        from tools.review import serve
        current_source_tree=ast.parse(Path(serve.__file__).read_text())
        current_proxy_method=next(current_node for current_node in ast.walk(current_source_tree) if isinstance(current_node,ast.FunctionDef) and current_node.name=='proxy_gradio_request')
        current_compiled_module=ast.fix_missing_locations(ast.Module(body=[current_proxy_method],type_ignores=[]))
        current_route_resolver=Mock(side_effect=ValueError('Gradio 시작 실패: gradio.log 확인'))
        current_trace_callback=Mock()
        current_runtime_scope={'urlsplit':urlsplit,'resolve_gradio_proxy_port':current_route_resolver,'emit_server_trace':current_trace_callback}
        exec(compile(current_compiled_module,serve.__file__,'exec'),current_runtime_scope)
        current_http_handler=SimpleNamespace(path='/management/frame/pose-transfer-generator/',send_error=Mock())
        self.assertTrue(current_runtime_scope['proxy_gradio_request'](current_http_handler))
        current_http_handler.send_error.assert_called_once_with(503,'Management UI unavailable',explain='관리 화면을 시작하지 못했습니다. Gradio 시작 실패: gradio.log 확인')
        self.assertIn('gradio.log',current_trace_callback.call_args.args[1])
        current_route_resolver.side_effect=None
        current_route_resolver.return_value=None
        current_http_handler.send_error.reset_mock()
        self.assertFalse(current_runtime_scope['proxy_gradio_request'](current_http_handler))
        current_http_handler.send_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()


class StandaloneReviewRoutingTests(unittest.TestCase):
    def test_root_uses_static_entry_only_without_manager_source(self):
        import ast
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock
        from tools.review import serve
        current_source_tree = ast.parse(Path(serve.__file__).read_text())
        current_resolver_node = next(current_node for current_node in ast.walk(current_source_tree)
            if isinstance(current_node, ast.FunctionDef) and current_node.name == 'resolve_gradio_proxy_port')
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_manager_path = Path(current_directory_name) / 'manager-source.json'
            current_start_callback = Mock()
            current_runtime_scope = {'manager_source_path': current_manager_path,
                'parsed_argument_values': SimpleNamespace(port=8798),
                'static_review_route_identifiers': set(),
                'ensure_management_menu_server': current_start_callback}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[current_resolver_node], type_ignores=[])), serve.__file__, 'exec'), current_runtime_scope)
            current_route_resolver = current_runtime_scope['resolve_gradio_proxy_port']
            self.assertIsNone(current_route_resolver('/'))
            self.assertIsNone(current_route_resolver('/assets/image.png'))
            current_start_callback.assert_not_called()
            current_manager_path.write_text('{}')
            self.assertEqual(current_route_resolver('/'), (8898, '/'))
            current_start_callback.assert_called_once_with(8798, current_manager_path)
