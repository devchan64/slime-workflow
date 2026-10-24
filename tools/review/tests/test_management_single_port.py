"""단일 포트 UI·기존 HTTP 경로의 계약 검증."""
import json
import tempfile
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from fastapi.testclient import TestClient
import gradio as gr
from tools.review.common.management_asgi import build_management_application


class ManagementSinglePortTests(unittest.TestCase):
    def test_mounted_queue_and_legacy_file(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path/'source.json'
            current_source_path.write_text('{}')
            (current_root_path/'test.txt').write_text('검수 파일')
            def build_test_interface(current_tool_name, current_review_port, current_source_path):
                with gr.Blocks() as current_interface_blocks:
                    current_input_box = gr.Textbox()
                    current_output_box = gr.Textbox()
                    gr.Button('확인').click(lambda current_input_text: current_input_text, current_input_box, current_output_box, api_name='echo')
                return current_interface_blocks, {'allowed_paths': []}
            with patch('tools.review.common.management_asgi.build_management_blocks', side_effect=build_test_interface), patch('gradio.Blocks.launch', side_effect=AssertionError('추가 서버 실행 금지')):
                current_app_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_source_path, 8770, [])
                with TestClient(current_app_value) as current_test_client:
                    self.assertEqual(current_test_client.get('/test.txt').text, '검수 파일')
                    self.assertEqual(current_test_client.get('/', follow_redirects=False).headers['location'], '/management/')
                    for current_tool_name in ('billboard-generator','pose-transfer-generator'):
                        current_route_prefix = '/management/frame/' + current_tool_name
                        self.assertEqual(current_test_client.get(current_route_prefix+'/').status_code, 200)
                        self.assertEqual(current_test_client.get(current_route_prefix+'/config').status_code, 200)
                        current_result_value = current_test_client.post(current_route_prefix+'/gradio_api/call/echo', json={'data': ['확인']})
                        self.assertEqual(current_result_value.status_code, 200)
                        current_event_identifier = current_result_value.json()['event_id']
                        current_stream_text = current_test_client.get(current_route_prefix+'/gradio_api/call/echo/'+current_event_identifier).text
                        self.assertIn('event: complete', current_stream_text)
                        self.assertEqual(json.loads(current_stream_text.split('data: ')[1].strip()), ['확인'])

    def test_missing_ui_fails_without_static_fallback(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            with patch('tools.review.common.management_asgi.build_management_blocks', side_effect=ValueError('실험용 초기화 실패')):
                current_app_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_root_path/'missing.json', 8770, [])
                with TestClient(current_app_value) as current_test_client:
                    self.assertEqual(current_test_client.get('/management/frame/billboard-generator/').status_code, 503)
                    self.assertNotEqual(current_test_client.get('/', follow_redirects=False).status_code, 307)
