"""폐기된 RGB 입력의 신규 생성·재개·UI 복원 차단을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generators.wan_fun.contracts import validate_fun_request
from generators.wan_fun.worker import execute_fun_inference
from tools.review.domains.wan_fun.generation import FunControlGenerationManager
from tools.review.ui.gradio.wan_fun_app import restore_fun_inputs


class FunRgbRetirementTests(unittest.TestCase):
    def test_retired_requests_fail_before_inference(self):
        for current_request_record in ({'input_mode': 'rgb-video'}, {'control_type': 'rgb'}, {'rgb_video': ''}, {'rgb_video_file': 'rgb-input.mp4'}):
            with self.subTest(request=current_request_record):
                with self.assertRaisesRegex(ValueError, '폐기'):
                    validate_fun_request(current_request_record)
                with self.assertRaisesRegex(ValueError, '폐기'):
                    execute_fun_inference(None, None, current_request_record, None)

    def test_saved_rgb_cannot_resume_or_restore(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_directory = Path(current_temp_directory)/'job'
            current_job_directory.mkdir()
            current_request_record = {'input_mode': 'rgb-video', 'rgb_video_file': 'rgb-input.mp4'}
            (current_job_directory/'request.json').write_text(json.dumps(current_request_record))
            with self.assertRaisesRegex(ValueError, '폐기'):
                FunControlGenerationManager.validate_generation_resume(None, current_job_directory)
            with patch('tools.review.ui.gradio.wan_fun_app.FUN_JOB_STORAGE', Path(current_temp_directory)):
                with self.assertRaisesRegex(ValueError, '폐기'):
                    restore_fun_inputs({'id': 'job', 'request': current_request_record})
