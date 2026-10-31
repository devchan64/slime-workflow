"""바닥 타일 생성 폐기와 기록 조회 계약을 검증한다."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.review.common.management_gateway import resolve_management_command
from tools.review.domains.tile.floor_generation import FloorGenerationManager
from tools.review.tests.test_image_generation import ImageGenerationTests


class FloorRetirementTests(unittest.TestCase):
    def test_gateway_rejects_execution_and_preserves_history(self):
        for current_command_name in ('generate', 'resume', 'prioritize'):
            with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('floor-tile', current_command_name, {})
        self.assertEqual(resolve_management_command('floor-tile', 'history', {}), ('GET', '/floor-tile-generator/history'))

    def test_direct_requests_do_not_launch_gpu(self):
        current_floor_service = FloorGenerationManager()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_floor_service.job_storage_root = Path(current_directory_name)
            current_job_directory = current_floor_service.job_storage_root / '2026-10-02_00-00-00-1234abcd'
            current_job_directory.mkdir()
            (current_job_directory / 'request.json').write_text('{}')
            for current_route_name, current_payload_record in (('jobs', {'action': 'generate'}), ('resume', {'id': current_job_directory.name})):
                current_http_handler = ImageGenerationTests().make_http_handler('/floor-tile-generator/' + current_route_name, 'POST')
                current_payload_bytes = json.dumps(current_payload_record).encode()
                current_http_handler.rfile = io.BytesIO(current_payload_bytes)
                current_http_handler.headers['Content-Length'] = str(len(current_payload_bytes))
                with patch('tools.review.domains.image.image_generation.launch_gpu_process') as current_launch_mock, patch('tools.review.domains.image.image_generation.resume_gpu_generation') as current_resume_mock:
                    current_floor_service.handle_image_request(current_http_handler)
                self.assertEqual(current_http_handler.status, 400)
                self.assertIn('폐기', json.loads(current_http_handler.wfile.getvalue())['error'])
                current_launch_mock.assert_not_called()
                current_resume_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
