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
    def test_legacy_hub_serves_current_navigation_without_rewriting_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary_directory_path:
            current_review_root = Path(temporary_directory_path)
            current_entry_path = current_review_root/'preview.html'
            current_entry_path.write_text('<iframe src="old.html"></iframe>')
            self.assertIn(b'<iframe', serve.read_review_document_content(current_review_root, current_entry_path))
            current_source_path = current_review_root/'manager-source.json'
            current_source_path.write_text('{"pages":[{"id":"walking</script>"}]}')
            current_response_content = serve.read_review_document_content(current_review_root, current_entry_path)
            self.assertNotIn(b'<iframe', current_response_content)
            self.assertIn(b'location.replace', current_response_content)
            self.assertIn(b'walking\\u003c/script>', current_response_content)
            self.assertIn('<iframe', current_entry_path.read_text())
            current_other_path = current_review_root/'anchors.html'
            current_other_path.write_text('original anchors')
            self.assertEqual(serve.read_review_document_content(current_review_root, current_other_path), b'original anchors')
            current_source_path.write_text('{"pages":[{}]}')
            with self.assertRaisesRegex(ValueError, '게시 목록'):
                serve.read_review_document_content(current_review_root, current_entry_path)

    def test_generator_settings_are_watched(self):
        parsed_argument_values = serve.parse_review_arguments([])
        watched_root_paths = serve.collect_review_watch_paths(parsed_argument_values)
        repository_root_path = Path(serve.__file__).resolve().parents[2]
        for generator_relative_path in ('generators/momask/config/standing-loops-v1.json', 'generators/terrain/config/tile_map.yaml'):
            self.assertTrue(any((repository_root_path/generator_relative_path).is_relative_to(current_root_path) for current_root_path in watched_root_paths))

    def test_map_validation_sources_are_watched(self):
        parsed_argument_values = serve.parse_review_arguments([])
        watched_root_paths = serve.collect_review_watch_paths(parsed_argument_values)
        repository_root_path = Path(serve.__file__).resolve().parents[2]
        for source_relative_path in ('domains/map_assets/placement.py', 'common/map_asset_http.py', 'common/map_tile_assets.py', 'common/sprite_display_properties.py', 'common/game_render_metrics.py'):
            current_source_path = repository_root_path/'tools/review'/source_relative_path
            self.assertTrue(current_source_path.is_file())
            self.assertTrue(any(current_source_path == current_root_path or current_source_path.is_relative_to(current_root_path) for current_root_path in watched_root_paths))

    def test_watch_detects_configuration_edit(self):
        with tempfile.TemporaryDirectory() as temporary_directory_path:
            configuration_file_path = Path(temporary_directory_path)/'prompt.json'
            configuration_file_path.write_text('{"prompt":"before"}')
            previous_watch_snapshot = serve.snapshot_review_watch_paths([Path(temporary_directory_path)])
            configuration_file_path.write_text('{"prompt":"updated prompt"}')
            self.assertNotEqual(previous_watch_snapshot, serve.snapshot_review_watch_paths([Path(temporary_directory_path)]))

    def test_asset_updates_do_not_restart_gui(self):
        with tempfile.TemporaryDirectory() as temporary_directory_path:
            temporary_root_path = Path(temporary_directory_path)
            frontend_repository_path = temporary_root_path/'slime-frontend'
            asset_repository_path = temporary_root_path/'slime-assets'
            (frontend_repository_path/'assets/terrain').mkdir(parents=True)
            (frontend_repository_path/'map-assets.lock.yaml').write_text('schema_version: 1\n')
            (asset_repository_path/'assets/tiles').mkdir(parents=True)
            (asset_repository_path/'asset-registry.yaml').write_text('schema_version: 1\n')
            parsed_argument_values = serve.parse_review_arguments(['--frontend-repo', str(frontend_repository_path)])
            watched_root_paths = serve.collect_review_watch_paths(parsed_argument_values)
            self.assertNotIn(frontend_repository_path/'map-assets.lock.yaml', watched_root_paths)
            self.assertNotIn(asset_repository_path/'asset-registry.yaml', watched_root_paths)
            self.assertNotIn(asset_repository_path/'assets/tiles', watched_root_paths)
            self.assertNotIn(frontend_repository_path/'assets', watched_root_paths)
            self.assertFalse(any('slime-assets' in current_root_path.parts for current_root_path in watched_root_paths))

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
