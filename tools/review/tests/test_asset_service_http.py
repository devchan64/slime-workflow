"""명시적으로 전달된 격리 API에 공용 게이트웨이·CLI HTTP를 연결한다."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import threading
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_cli
from tools.review.domains.map_assets.resize import handle_map_resize_request
from tools.review.domains.map_assets.database_client import execute_content_api_request


@unittest.skipUnless(os.environ.get('ASSET_HTTP_ISOLATED_TEST') == '1', '격리 API 실행기가 필요합니다.')
class AssetServiceHttpTests(unittest.TestCase):
    def test_gateway_envelope_cli_and_authentication(current_test_case):
        current_gateway_service = ManagementCommandGateway({'map-assets':handle_map_resize_request})

        class IsolatedGatewayHandler(BaseHTTPRequestHandler):
            def do_POST(current_http_handler):
                current_gateway_service.handle(current_http_handler)

            def log_message(current_http_handler, current_log_format, *current_log_arguments):
                pass

        current_http_server = ThreadingHTTPServer(('127.0.0.1',0),IsolatedGatewayHandler)
        current_server_thread = threading.Thread(target=current_http_server.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            current_server_origin = 'http://127.0.0.1:'+str(current_http_server.server_port)
            current_request_record = Request(current_server_origin+'/management/command',
                data=json.dumps({'service':'map-assets','command':'database-status','payload':{}}).encode(),
                headers={'Origin':current_server_origin,'Content-Type':'application/json'})
            with urlopen(current_request_record,timeout=10) as current_http_response:
                current_envelope_result=json.load(current_http_response)
            current_test_case.assertTrue(current_envelope_result['pending'])
            current_output_buffer=io.StringIO()
            with tempfile.TemporaryDirectory() as current_directory_name, contextlib.redirect_stdout(current_output_buffer):
                current_payload_path=Path(current_directory_name)/'payload.json'
                current_payload_path.write_text('{}')
                execute_gateway_cli(['command','map-assets','--server-url',current_server_origin,'database-status','--payload-file',str(current_payload_path)])
            current_test_case.assertEqual(json.loads(current_output_buffer.getvalue()),current_envelope_result)
            current_test_case.assertIn('types',execute_content_api_request('GET','/internal/v1/content/types'))
            with patch.dict(os.environ,{'SLIME_CONTENT_SERVICE_SECRET_FILE':os.environ['ASSET_HTTP_WRONG_TOKEN_FILE']}):
                with current_test_case.assertRaisesRegex(ValueError,'401'):
                    execute_content_api_request('GET','/internal/v1/content/status')
        finally:
            current_http_server.shutdown()
            current_http_server.server_close()
            current_server_thread.join(timeout=5)
