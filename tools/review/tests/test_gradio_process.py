"""Gradio UI 프로세스 소스 변경 감지 계약을 검증한다."""
from pathlib import Path
import tempfile
import unittest

from tools.review.common.gradio_process import create_gradio_source_fingerprint


class GradioProcessTests(unittest.TestCase):
    def test_source_fingerprint_changes_when_tracked_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_directory_path=Path(temporary_directory_name)
            application_file_path=temporary_directory_path/'app.py'
            application_source_path=temporary_directory_path/'source.json'
            application_file_path.write_text('first')
            application_source_path.write_text('{}')
            first_fingerprint_value=create_gradio_source_fingerprint(application_source_path,application_file_path)
            application_file_path.write_text('second version')
            second_fingerprint_value=create_gradio_source_fingerprint(application_source_path,application_file_path)
        self.assertNotEqual(first_fingerprint_value,second_fingerprint_value)
