"""폐기된 RGB 입력의 신규 생성·재개·UI 복원 차단을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generators.wan_fun.contracts import validate_fun_request
from generators.wan_fun.worker import execute_fun_inference
from workflow.domains.wan_fun.generation import FunControlGenerationManager


class FunRgbRetirementTests(unittest.TestCase):
    def test_retired_requests_fail_before_inference(self):
        for current_request_record in ({'input_mode': 'rgb-video'}, {'control_type': 'rgb'}, {'rgb_video': ''}, {'rgb_video_file': 'rgb-input.mp4'}):
            with self.subTest(request=current_request_record):
                with self.assertRaisesRegex(ValueError, '폐기'):
                    validate_fun_request(current_request_record)
                with self.assertRaisesRegex(ValueError, '폐기'):
                    execute_fun_inference(None, None, current_request_record, None)

    def test_saved_rgb_cannot_resume_or_restore(self):
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from types import SimpleNamespace
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_job_id='2026-11-18_00-00-00-12345678'
            current_job_directory = current_root/current_job_id
            current_job_directory.mkdir()
            current_request_record = {'input_mode': 'rgb-video', 'rgb_video_file': 'rgb-input.mp4'}
            (current_job_directory/'request.json').write_text(json.dumps(current_request_record))
            with self.assertRaisesRegex(ValueError, '폐기'):
                FunControlGenerationManager.validate_generation_resume(None, current_job_directory)
            current_app=build_management_application(SimpleHTTPRequestHandler,current_root,current_root/'source.json',8770,[])
            with patch('workflow.domains.hermes_agent.video_operations.make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=current_root)), TestClient(current_app) as client:
                response=client.get('/management/assistant/fun-input/'+current_job_id)
            self.assertEqual(response.status_code,422)
            self.assertIn('복원할 수 없습니다',response.json()['detail'])
