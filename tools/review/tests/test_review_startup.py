"""관리도구 통합 실행의 입력 조합과 생성 실패 전파를 확인한다."""
import argparse
import contextlib
import io
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from tools.review import serve


class ReviewStartupTests(unittest.TestCase):
    def test_generator_settings_are_watched(self):
        parsed_argument_values = serve.parse_review_arguments([])
        watched_root_paths = serve.collect_review_watch_paths(parsed_argument_values)
        repository_root_path = Path(serve.__file__).resolve().parents[2]
        for generator_relative_path in ('generators/momask/config/standing-loops-v1.json', 'generators/terrain/config/tile_map.yaml'):
            self.assertTrue(any((repository_root_path/generator_relative_path).is_relative_to(current_root_path) for current_root_path in watched_root_paths))

    def test_watch_detects_configuration_edit(self):
        with tempfile.TemporaryDirectory() as temporary_directory_path:
            configuration_file_path = Path(temporary_directory_path)/'prompt.json'
            configuration_file_path.write_text('{"prompt":"before"}')
            previous_watch_snapshot = serve.snapshot_review_watch_paths([Path(temporary_directory_path)])
            configuration_file_path.write_text('{"prompt":"updated prompt"}')
            self.assertNotEqual(previous_watch_snapshot, serve.snapshot_review_watch_paths([Path(temporary_directory_path)]))

    def test_default_repository_and_port(self):
        parsed_argument_values = serve.parse_review_arguments([])
        self.assertEqual(parsed_argument_values.frontend_repo, Path(serve.__file__).resolve().parents[3]/'slime-frontend')
        self.assertEqual(parsed_argument_values.port, 8770)
        self.assertEqual(parsed_argument_values.entry, 'preview.html')

    def test_live_reload_status_path_is_identified_without_query_string(self):
        self.assertTrue(serve.is_review_live_reload_request('/__review_live_reload__?cache=none'))
        self.assertFalse(serve.is_review_live_reload_request('/preview.html'))

    def test_live_reload_script_is_added_once_before_body_end(self):
        page_content = b'<html><body>review</body></html>'
        rendered_content = serve.inject_review_live_reload(page_content)
        self.assertEqual(rendered_content.count(b'id=\"review-live-reload\"'), 1)
        self.assertLess(rendered_content.index(b'id=\"review-live-reload\"'), rendered_content.index(b'</body>'))
        self.assertEqual(serve.inject_review_live_reload(rendered_content), rendered_content)

    def test_existing_review_options(self):
        parsed_argument_values = serve.parse_review_arguments(['--root', '.tmp/example', '--entry', 'anchors.html'])
        self.assertEqual(parsed_argument_values.entry, 'anchors.html')
        self.assertEqual(serve.prepare_review_directory(parsed_argument_values), Path('.tmp/example').resolve())

    def test_reject_invalid_option_combinations(self):
        for command_argument_values in (['--worldbuilding-only'], ['--worldbuilding-config', '/tmp/workspace.yaml'], ['--walking', '.tmp/walk'], ['--standing', '.tmp/stand'], ['--root', '.tmp/review', '--walking', '.tmp/walk', '--standing', '.tmp/stand'], ['--walking', '.tmp/walk', '--standing', '.tmp/stand', '--entry', 'anchors.html'], ['--root', '.tmp/review', '--port', '80']):
            with self.subTest(arguments=command_argument_values), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                serve.parse_review_arguments(command_argument_values)

    def test_generated_directory_is_served(self):
        parsed_argument_values = serve.parse_review_arguments(['--walking', '.tmp/walk', '--standing', '.tmp/stand'])
        with patch('tools.review.build_frame_manager.build_frame_manager', return_value=Path('/tmp/generated-review')) as build_manager_mock:
            self.assertEqual(serve.prepare_review_directory(parsed_argument_values), Path('/tmp/generated-review'))
            build_manager_mock.assert_called_once_with(parsed_argument_values)

    def test_default_manager_uses_latest_ui_bundle(self):
        parsed_argument_values = serve.parse_review_arguments(['--frontend-repo', '/tmp/slime-frontend'])
        with patch.object(serve, 'ensure_frontend_ui_review_bundle', return_value=Path('/tmp/slime-frontend/.tmp/2026-09-21_17-11-44/ui-review')) as find_bundle_mock, patch('tools.review.build_frontend_review.build_frontend_review', return_value=Path('/tmp/generated-review')) as build_review_mock:
            self.assertEqual(serve.prepare_review_directory(parsed_argument_values), Path('/tmp/generated-review'))
            find_bundle_mock.assert_called_once_with(Path('/tmp/slime-frontend'))
            build_review_mock.assert_called_once_with(Path('/tmp/slime-frontend'), ui_bundle_directory=Path('/tmp/slime-frontend/.tmp/2026-09-21_17-11-44/ui-review'))

    def test_generation_failure_stops_server(self):
        parsed_argument_values = serve.parse_review_arguments(['--walking', '.tmp/walk', '--standing', '.tmp/stand'])
        with patch('tools.review.build_frame_manager.build_frame_manager', side_effect=ValueError('검수 페이지 누락')), patch.object(serve, 'ThreadingHTTPServer') as review_server_mock:
            with self.assertRaisesRegex(ValueError, '검수 페이지 누락'):
                serve.run_review_server(parsed_argument_values)
            review_server_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
