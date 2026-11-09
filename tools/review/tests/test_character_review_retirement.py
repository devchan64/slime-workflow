"""캐릭터 표현 검수 페이지 폐기와 캡처 명령 유지 계약."""
import asyncio
import json
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

from tools.review.common.management_asgi import build_management_application
from tools.review.common.management_gateway import resolve_management_command
from tools.review.ui.gradio.management_menu_app import load_manager_page_records


class CharacterReviewRetirementTests(unittest.TestCase):
    def test_retired_page_and_preserved_capture(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path / 'menu.json'
            current_source_path.write_text(json.dumps({'pages': [{'id': 'character-review', 'label': '검수', 'path': '/management/frame/character-review/', 'category': 'character-render-review', 'description': '검수'}]}))
            self.assertNotIn('character-review', [current_page_record['id'] for current_page_record in load_manager_page_records(current_source_path)])
            with patch('tools.review.common.management_asgi.build_management_blocks') as current_builder_mock:
                current_application_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_source_path, 8770, [])
                async def check_retired_request(current_request_path, current_query_bytes=b''):
                    current_response_events = []
                    async def receive_request_event():
                        return {'type': 'http.request', 'body': b'', 'more_body': False}
                    async def collect_response_event(current_event_value):
                        current_response_events.append(current_event_value)
                    current_request_scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'GET', 'scheme': 'http', 'path': current_request_path, 'raw_path': current_request_path.encode(), 'query_string': current_query_bytes, 'headers': [], 'server': ('localhost', 8770), 'client': ('localhost', 1), 'root_path': ''}
                    await current_application_value(current_request_scope, receive_request_event, collect_response_event)
                    self.assertEqual(current_response_events[0]['status'], 410)
                for current_request_path in ('/management/frame/character-review/', '/management/frame/character-review/assets/test'):
                    asyncio.run(check_retired_request(current_request_path))
                asyncio.run(check_retired_request('/management/', b'tool=character-review&category=character-render-review'))
                current_builder_mock.assert_not_called()
        self.assertEqual(resolve_management_command('character-review', 'capture', {})[:2], ('POST', '/character-review/capture'))
