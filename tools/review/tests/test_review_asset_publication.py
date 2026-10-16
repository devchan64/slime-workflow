"""격리 파일로 검수 이미지의 불변 주소와 원자적 게시를 검증한다."""
from pathlib import Path
import tempfile
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from tools.review.common.review_asset_publication import publish_review_image_asset


class ReviewAssetPublicationTests(unittest.TestCase):
    def test_published_image_through_review_static_http_methods(self):
        import ast
        import http.client
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        from types import SimpleNamespace
        from tools.review import serve
        current_source_tree = ast.parse(Path(serve.__file__).read_text())
        current_handler_class = next(current_source_node for current_source_node in ast.walk(current_source_tree) if isinstance(current_source_node, ast.ClassDef) and current_source_node.name == 'ReviewRequestHandler')
        current_handler_class.body = [current_method_node for current_method_node in current_handler_class.body if isinstance(current_method_node, ast.FunctionDef) and current_method_node.name in ('__init__', 'send_head', 'end_headers', 'list_directory')]
        current_compiled_tree = ast.fix_missing_locations(ast.Module(body=[current_handler_class], type_ignores=[]))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path / 'source.png'
            current_source_path.write_bytes(b'complete image payload')
            current_output_path = publish_review_image_asset(current_source_path, current_root_path / 'public', 'review-character')
            current_runtime_scope = {'SimpleHTTPRequestHandler': SimpleHTTPRequestHandler, 'review_root_directory': current_root_path,
                'resolve_review_request': serve.resolve_review_request, 'parsed_argument_values': SimpleNamespace(entry='preview.html')}
            exec(compile(current_compiled_tree, serve.__file__, 'exec'), current_runtime_scope)
            current_handler_type = current_runtime_scope['ReviewRequestHandler']
            with patch.object(current_handler_type, 'log_message'), ThreadingHTTPServer(('127.0.0.1', 0), current_handler_type) as current_http_server:
                current_server_thread = threading.Thread(target=current_http_server.serve_forever, daemon=True)
                current_server_thread.start()
                try:
                    current_http_client = http.client.HTTPConnection('127.0.0.1', current_http_server.server_port, timeout=5)
                    try:
                        current_http_client.request('GET', '/' + current_output_path.relative_to(current_root_path).as_posix())
                        current_http_response = current_http_client.getresponse()
                        self.assertEqual(current_http_response.status, 200)
                        self.assertEqual(current_http_response.read(), current_source_path.read_bytes())
                        self.assertEqual(current_http_response.getheader('Content-Type'), 'image/png')
                        self.assertEqual(current_http_response.getheader('X-Content-Type-Options'), 'nosniff')
                        self.assertEqual(current_http_response.getheader('Cross-Origin-Resource-Policy'), 'same-origin')
                    finally:
                        current_http_client.close()
                finally:
                    current_http_server.shutdown()
                    current_server_thread.join(timeout=5)

    def test_concurrent_publication_hides_incomplete_content(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_source_path = current_root_path / 'source.png'
            current_image_bytes = b'image-content' * 4096
            current_source_path.write_bytes(current_image_bytes)
            current_output_directory = current_root_path / 'public'
            current_write_barrier = threading.Barrier(3)
            current_finish_event = threading.Event()
            def write_incomplete_temporary_file(current_pending_path, current_pending_bytes):
                with current_pending_path.open('wb') as current_pending_handle:
                    current_pending_handle.write(current_pending_bytes[:100])
                    current_pending_handle.flush()
                    current_write_barrier.wait(timeout=5)
                    if not current_finish_event.wait(timeout=5):
                        raise TimeoutError('게시 검증 완료 신호 없음')
                    current_pending_handle.write(current_pending_bytes[100:])
                return len(current_pending_bytes)
            with patch.object(Path, 'write_bytes', write_incomplete_temporary_file), ThreadPoolExecutor(max_workers=2) as current_worker_pool:
                current_publish_futures = [current_worker_pool.submit(publish_review_image_asset, current_source_path, current_output_directory, 'review-character') for current_request_index in range(2)]
                try:
                    current_write_barrier.wait(timeout=5)
                    self.assertEqual(list(current_output_directory.glob('*.png')), [])
                    self.assertEqual(len(list(current_output_directory.glob('*.tmp'))), 2)
                finally:
                    current_finish_event.set()
                current_result_paths = [current_publish_future.result(timeout=5) for current_publish_future in current_publish_futures]
            self.assertEqual(current_result_paths[0], current_result_paths[1])
            self.assertEqual(current_result_paths[0].read_bytes(), current_image_bytes)
            self.assertEqual(list(current_output_directory.glob('*.tmp')), [])

    def test_republication_preserves_previous_version_and_skips_existing_write(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_source_path=current_root_path/'source.png'
            current_source_path.write_bytes(b'first image')
            current_first_path=publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            with patch.object(Path,'write_bytes',side_effect=AssertionError('기존 파일을 다시 쓰면 안 됩니다.')):
                self.assertEqual(publish_review_image_asset(current_source_path,current_root_path/'public','review-character'),current_first_path)
            current_source_path.write_bytes(b'next image')
            current_next_path=publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            self.assertNotEqual(current_first_path,current_next_path)
            self.assertEqual(current_first_path.read_bytes(),b'first image')
            self.assertEqual(current_next_path.read_bytes(),b'next image')

    def test_failed_publish_leaves_no_partial_final_or_temporary_file(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_source_path=current_root_path/'source.png'
            current_source_path.write_bytes(b'image')
            with patch.object(Path,'replace',side_effect=OSError('게시 실패')),self.assertRaises(OSError):
                publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            self.assertEqual(list((current_root_path/'public').iterdir()),[])
