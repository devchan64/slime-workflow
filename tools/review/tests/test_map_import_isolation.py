"""맵 모듈 import와 실제 콘텐츠 조회 수명을 분리한다."""
import importlib
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

class MapImportIsolationTests(unittest.TestCase):
    def test_module_import_does_not_request_content(self):
        with patch.dict(os.environ, {'SLIME_CONTENT_STORAGE':'database'}), patch('tools.review.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('import 중 API 호출')) as current_request_mock:
            from tools.review.common import map_asset_sources
            importlib.reload(map_asset_sources)
            import tools.review.build_frontend_review
            current_request_mock.assert_not_called()

    def test_connection_error_explains_required_service(self):
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        with patch.dict(os.environ, {'SLIME_CONTENT_SERVICE_ORIGIN':'http://127.0.0.1:18083','SLIME_CONTENT_SERVICE_SECRET_FILE':''}), patch('tools.review.domains.map_assets.database_client.build_opener') as current_opener_mock:
            current_opener_mock.return_value.open.side_effect=URLError(ConnectionRefusedError(111,'Connection refused'))
            with self.assertRaisesRegex(RuntimeError,'18083.*콘텐츠 API를 먼저 실행'):
                execute_content_api_request('GET','/internal/v1/content/review-bundle')
