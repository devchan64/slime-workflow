"""폐기된 양끝 이미지 조건의 생성·재개 차단 검증."""
import json
import tempfile
import unittest
from pathlib import Path
from generators.wan_fun.contracts import validate_fun_request, reject_retired_rgb_input
from tools.review.domains.wan_fun.generation import FunControlGenerationManager


class FunEndpointRetirementTests(unittest.TestCase):
    def test_reject_endpoint_requests(self):
        for current_field_name in ('start_image', 'end_image', 'start_image_file', 'end_image_file', 'end_image_same_as_start'):
            current_request_record = {current_field_name: True if current_field_name == 'end_image_same_as_start' else 'image.png'}
            with self.subTest(field=current_field_name):
                with self.assertRaisesRegex(ValueError, '폐기'):
                    validate_fun_request(current_request_record)
        reject_retired_rgb_input({'end_image_same_as_start': False})

    def test_reject_endpoint_resume(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)
            (current_job_directory/'request.json').write_text(json.dumps({'end_image_file':'end-image.png'}))
            with self.assertRaisesRegex(ValueError, '폐기'):
                FunControlGenerationManager.validate_generation_resume(None, current_job_directory)
