"""단일 포트 UI·기존 HTTP 경로의 계약 검증."""
import json
import tempfile
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from fastapi.testclient import TestClient
from workflow.common.management_asgi import build_management_application


class ManagementSinglePortTests(unittest.TestCase):
    def test_gui_health_exposes_only_its_own_launch_identity(self):
        import os
        with tempfile.TemporaryDirectory() as temporary_directory_name, \
                patch.dict(os.environ, {'SLIME_MANAGEMENT_STACK_TOKEN':'fixture-token'}):
            current_root_path = Path(temporary_directory_name)
            current_app_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_root_path / 'source.json', 8770, [])
            with TestClient(current_app_value) as current_test_client:
                current_response_value = current_test_client.get('/management/gui-health')
            self.assertEqual(current_response_value.status_code, 200)
            self.assertEqual(current_response_value.json()['role'], 'management-gui')
            self.assertEqual(current_response_value.json()['launch_token'], 'fixture-token')
            self.assertEqual(current_response_value.headers['cache-control'], 'no-store')

    def test_retired_sprite_editor_is_unavailable(self):
        from workflow.common.management_catalog import load_manager_page_records
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path / 'source.json'
            current_source_path.write_text(json.dumps({'pages': [{'id':'sprite-editor-v2','label':'기존 편집기','path':'/character-animation/sprite-editor-v2','category':'animation-tool','description':'과거 메뉴'}]}))
            self.assertNotIn('sprite-editor-v2', [current_page_record['id'] for current_page_record in load_manager_page_records(current_source_path)])
            self.assertFalse(any(current_command_name.startswith('sprite-v2-') for current_command_name in MANAGEMENT_SERVICE_COMMANDS['character-animation']))
            current_app_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_source_path, 8770, [])
            with TestClient(current_app_value) as current_test_client:
                for current_route_path in ('/management/frame/sprite-editor-v2/', '/character-animation/sprite-editor-v2'):
                    self.assertEqual(current_test_client.get(current_route_path).status_code, 410)

    def test_embedded_registered_review_returns_source_document(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path/'source.json'
            current_source_path.write_text('{}')
            current_review_path = current_root_path/'animation-1'/'anchors.html'
            current_review_path.parent.mkdir()
            current_review_path.write_text('<script id="anchor-review-data" type="application/json">{}</script>')
            current_app_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_source_path, 8770, {'/animation-1/anchors.html': 'animation-1'})
            with TestClient(current_app_value) as current_test_client:
                current_embedded_response = current_test_client.get('/animation-1/anchors.html?embedded=static')
                self.assertEqual(current_embedded_response.status_code, 200)
                self.assertIn('anchor-review-data', current_embedded_response.text)
                self.assertEqual(current_test_client.get('/animation-1/anchors.html', follow_redirects=False).headers['location'], '/management/?')

    def test_react_pages_share_port_with_legacy_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.json'
            source.write_text('{}')
            (root / 'test.txt').write_text('검수 파일')
            app = build_management_application(SimpleHTTPRequestHandler, root, source, 8770, [])
            with TestClient(app) as client:
                self.assertEqual(client.get('/test.txt').text, '검수 파일')
                self.assertEqual(client.get('/', follow_redirects=False).headers['location'], '/management/frame/hermes-agent/')
                for tool in ('billboard-generator', 'kimodo-generator'):
                    route = '/management/frame/' + tool
                    self.assertIn('/management/assistant/app.js', client.get(route + '/').text)
                    self.assertEqual(client.get(route + '/config').status_code, 404)
                    self.assertEqual(client.post(route + '/gradio_api/call/echo', json={}).status_code, 404)
                location = client.get('/management/?tool=kimodo-generator&job=example', follow_redirects=False).headers['location']
                self.assertEqual(location, '/management/frame/kimodo-generator/?job=example')

    def test_unknown_tool_returns_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = build_management_application(SimpleHTTPRequestHandler, root, root/'missing.json', 8770, [])
            with TestClient(app) as client:
                self.assertEqual(client.get('/management/?tool=missing').status_code, 404)
