"""Gradio UI 프로세스 소스 변경 감지 계약을 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.review.common.gradio_process import create_gradio_process_marker_path, create_gradio_source_fingerprint, read_gradio_process_marker, write_gradio_process_marker


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

    def test_process_marker_preserves_pid_and_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            marker_path_value=Path(temporary_directory_name)/'gradio-process.json'
            source_fingerprint_value=(('tile_map_app.py',123),)
            write_gradio_process_marker(marker_path_value,4321,source_fingerprint_value)
            marker_record_value=read_gradio_process_marker(marker_path_value)
        self.assertEqual(marker_record_value,{'pid':4321,'fingerprint':json.loads(json.dumps(source_fingerprint_value))})

    def test_process_marker_path_is_scoped_to_review_port_and_application(self):
        marker_path_value=create_gradio_process_marker_path(8770,'tile-map')
        self.assertEqual(marker_path_value.name,'gradio-8770-tile-map.json')
