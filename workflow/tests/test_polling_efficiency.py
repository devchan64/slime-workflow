"""다운로드 조회 간격에 사용되는 실제 서비스 상태를 검증한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class PollingEfficiencyTests(unittest.TestCase):
    def test_download_activity_is_scoped_to_selected_model(self):
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            records={'records':[{'model':'HeartMuLa/model','status':'running','bytes':2,'total_bytes':10},
                                {'model':'black-forest-labs/flux-3-image-klein','status':'completed','bytes':10,'total_bytes':10}]}
            with patch('workflow.common.management_client.execute_remote_management_command',return_value=records),TestClient(app) as client:
                self.assertFalse(client.get('/management/assistant/model-downloads/flux-image').json()['active'])
                self.assertTrue(client.get('/management/assistant/model-downloads/music-heartmula').json()['active'])
                records['records'][1]['status']='running'
                self.assertTrue(client.get('/management/assistant/model-downloads/flux-image').json()['active'])
                records['records'][1]['status']='failed'
                self.assertFalse(client.get('/management/assistant/model-downloads/flux-image').json()['active'])
