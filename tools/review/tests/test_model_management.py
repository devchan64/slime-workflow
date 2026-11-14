import unittest

from tools.review.ui.gradio.model_management_app import read_model_job_status, build_model_management_interface


class ModelManagementTest(unittest.TestCase):
    def test_models_are_displayed_in_name_order(self):
        from tools.review.ui.gradio.model_management_app import MODEL_PREPARATION_SERVICES, MODEL_JOB_SERVICES, MODEL_OBSERVATION_SERVICES
        current_model_names = [current_name for current_name, _ in (*MODEL_PREPARATION_SERVICES, *MODEL_JOB_SERVICES, *MODEL_OBSERVATION_SERVICES)]
        current_interface_config = build_model_management_interface().config
        current_display_names = [current_component['props']['value'][4:] for current_component in current_interface_config['components']
                                 if current_component.get('type') == 'markdown' and current_component.get('props', {}).get('value', '').startswith('### ')
                                 and current_component['props']['value'][4:] in current_model_names]
        self.assertEqual(current_display_names, sorted(current_model_names, key=str.casefold))

    def test_model_file_inventory_excludes_partial_cache_and_symlinks(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.common.model_file_inventory import list_model_inventory_files
        from tools.review.ui.gradio.model_management_app import format_model_inventory_files
        with TemporaryDirectory() as current_directory_name:
            current_workspace_path = Path(current_directory_name)
            current_model_path = current_workspace_path/'.model'/'sample'
            current_model_path.mkdir(parents=True)
            (current_model_path/'z.safetensors').write_bytes(b'12345')
            (current_model_path/'a.json').write_bytes(b'{}')
            (current_model_path/'incomplete.partial').write_bytes(b'x')
            (current_model_path/'incomplete.partial.verified').write_bytes(b'x')
            (current_model_path/'.cache').mkdir()
            (current_model_path/'.cache'/'private').write_bytes(b'x')
            (current_model_path/'link').symlink_to(current_model_path/'a.json')
            current_outside_path = current_workspace_path/'outside'
            current_outside_path.write_bytes(b'secret')
            current_inventory_value = list_model_inventory_files({'test': [current_model_path, current_outside_path]}, current_workspace_path)['test']
            self.assertEqual([current_file['path'] for current_file in current_inventory_value['files']], ['sample/a.json', 'sample/z.safetensors'])
            self.assertEqual(current_inventory_value['count'], 2)
            self.assertFalse(current_inventory_value['incomplete'])
            current_display_text = format_model_inventory_files(current_inventory_value)
            self.assertIn('저장된 파일 2개', current_display_text)
            self.assertIn('sample/z.safetensors', current_display_text)
            self.assertIn('해시 검증 결과는 아닙니다', current_display_text)

    def test_retired_qwen_2512_is_not_in_model_management(self):
        from tools.review.ui.gradio.model_management_app import MODEL_PREPARATION_SERVICES, MODEL_JOB_SERVICES
        self.assertNotIn('qwen-2512', [current_service for _, current_service in (*MODEL_PREPARATION_SERVICES, *MODEL_JOB_SERVICES)])

    def test_running_preparation_explains_disabled_download(self):
        import gradio as gr
        from tools.review.common.gradio_model_download import build_model_download_controls
        with gr.Blocks() as current_interface_blocks:
            build_model_download_controls(current_interface_blocks, lambda *_: {
                'message': '모델 다운로드 중', 'preparation_status': 'running', 'ready': False})
        current_refresh_function = next(current_function.fn for current_function in current_interface_blocks.fns.values()
                                        if current_function.fn and current_function.fn.__name__ == 'refresh_model_download_status')
        current_message_value, _, current_button_update, _ = current_refresh_function()
        self.assertIn('중복 요청', current_message_value)
        self.assertFalse(current_button_update['interactive'])

    def test_running_prepare_is_selected_over_newer_generation(self):
        def execute_test_command(service_name_value, command_name_value, payload_record_value):
            return {'records': [
                {'id': 'generation', 'request': {'action': 'generate'}, 'status': {'status': 'running'}},
                {'id': 'preparation', 'request': {'action': 'prepare'}, 'status': {'status': 'running'}},
            ]}
        self.assertIn('진행 중 · 작업 ID `preparation`', read_model_job_status('service', execute_test_command))

    def test_gateway_failure_is_visible(self):
        def execute_test_command(service_name_value, command_name_value, payload_record_value):
            raise OSError('연결 실패')
        self.assertIn('연결 실패', read_model_job_status('service', execute_test_command))

    def test_interface_builds(self):
        self.assertTrue(build_model_management_interface().config['components'])

class SharedModelDownloadTest(unittest.TestCase):
    def test_shared_record_reports_progress_and_failure(self):
        import tempfile
        from pathlib import Path
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            with self.assertRaisesRegex(RuntimeError, '실패'):
                with track_model_download('test-model', current_directory_path) as current_download_record:
                    current_download_record.update(bytes=40, total_bytes=100, resumed_bytes=20)
                    self.assertEqual(list_model_download_records(current_directory_path)[0]['bytes'], 40)
                    raise RuntimeError('실패')
            current_record_value = list_model_download_records(current_directory_path)[0]
            self.assertEqual(current_record_value['status'], 'failed')
            self.assertEqual(current_record_value['resumed_bytes'], 20)

    def test_status_command_rejects_extra_fields(self):
        from tools.review.common.management_gateway import resolve_management_command
        self.assertEqual(resolve_management_command('model-downloads', 'download-status', {}), ('GET', '/model-downloads/status'))
        self.assertEqual(resolve_management_command('model-downloads', 'download-inventory', {}), ('GET', '/model-downloads/inventory'))
        with self.assertRaises(ValueError):
            resolve_management_command('model-downloads', 'download-status', {'unexpected': True})
        with self.assertRaises(ValueError):
            resolve_management_command('model-downloads', 'download-inventory', {'path': '/tmp'})

class HuggingFaceDownloadRecordTest(unittest.TestCase):
    def test_file_progress_and_resume_are_recorded(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            def fake_hub_download(*current_argument_values, **current_keyword_values):
                with current_keyword_values['tqdm_class'](total=100, initial=40, unit='B', disable=True) as current_progress_bar:
                    current_progress_bar.update(60)
                return 'prepared'
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_directory_path)), patch('huggingface_hub.hf_hub_download', fake_hub_download):
                self.assertEqual(model_huggingface_download.tracked_hf_hub_download('repo', 'weights'), 'prepared')
            current_record_value = list_model_download_records(current_directory_path)[0]
            self.assertEqual((current_record_value['status'], current_record_value['bytes'], current_record_value['total_bytes'], current_record_value['resumed_bytes']), ('completed', 100, 100, 40))

    def test_snapshot_bytes_do_not_claim_resume_count(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            def fake_snapshot_download(*current_argument_values, **current_keyword_values):
                with current_keyword_values['tqdm_class'](desc='Reconstructing', total=100, unit='B', disable=True) as current_progress_bar:
                    current_progress_bar.update(75)
                return 'prepared'
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_directory_path)), patch('huggingface_hub.snapshot_download', fake_snapshot_download):
                model_huggingface_download.tracked_snapshot_download('repo')
            current_record_value = list_model_download_records(current_directory_path)[0]
            self.assertEqual(current_record_value['bytes'], 75)
            self.assertIsNone(current_record_value['resumed_bytes'])

class HttpDownloadResumeIntegrationTest(unittest.TestCase):
    def test_interrupted_transfer_resumes_and_verifies(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import tempfile
        from threading import Thread
        from unittest.mock import patch
        from tools.review.common import model_http_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        current_content_bytes = b'abcdefgh' * 400000
        current_range_values = []
        class DownloadTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_header = self.headers.get('Range')
                current_range_values.append(current_range_header)
                current_range_start = int(current_range_header[6:-1]) if current_range_header else 0
                self.send_response(206 if current_range_header else 200)
                self.send_header('Content-Length', str(len(current_content_bytes)-current_range_start))
                if current_range_header:
                    self.send_header('Content-Range', f'bytes {current_range_start}-{len(current_content_bytes)-1}/{len(current_content_bytes)}')
                self.end_headers()
                if len(current_range_values) == 1:
                    self.wfile.write(current_content_bytes[:1200000])
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.wfile.write(current_content_bytes[current_range_start:])
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), DownloadTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_directory_path = Path(current_directory_name)
                current_target_path = current_directory_path/'model.bin'
                current_digest_value = hashlib.sha256(current_content_bytes).hexdigest()
                current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/model'
                with patch.object(model_http_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_directory_path/'records')):
                    with self.assertRaises((ValueError, OSError)):
                        model_http_download.download_verified_http(current_download_url, current_target_path, current_digest_value, 'test-model')
                    self.assertGreater(current_target_path.with_suffix('.bin.partial').stat().st_size, 0)
                    model_http_download.download_verified_http(current_download_url, current_target_path, current_digest_value, 'test-model')
                self.assertEqual(current_target_path.read_bytes(), current_content_bytes)
                self.assertTrue(current_range_values[1].startswith('bytes='))
                self.assertGreater(list_model_download_records(current_directory_path/'records')[0]['resumed_bytes'], 0)
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class SnapshotTotalProgressTest(unittest.TestCase):
    def test_snapshot_uses_cached_and_total_sizes_for_progress(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            def fake_snapshot_download(repo_id, *, dry_run=False, tqdm_class=None):
                if dry_run:
                    return [SimpleNamespace(file_size=40, is_cached=True, will_download=False), SimpleNamespace(file_size=60, is_cached=False, will_download=True)]
                with tqdm_class(desc='Reconstructing', total=60, unit='B', disable=True) as current_progress_bar:
                    current_progress_bar.update(30)
                    current_progress_bar.publish_download_progress(True)
                    current_record_value = list_model_download_records(current_directory_path)[0]
                    self.assertEqual((current_record_value['bytes'], current_record_value['total_bytes']), (70, 100))
                return 'ready'
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_directory_path)), patch('huggingface_hub.snapshot_download', fake_snapshot_download):
                self.assertEqual(model_huggingface_download.tracked_snapshot_download('repo'), 'ready')
            current_record_value = list_model_download_records(current_directory_path)[0]
            self.assertEqual((current_record_value['bytes'], current_record_value['total_bytes'], current_record_value['status']), (100, 100, 'completed'))

    def test_metadata_failure_does_not_block_download(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            def fake_snapshot_download(repo_id, *, dry_run=False, tqdm_class=None):
                if dry_run:
                    raise OSError('metadata unavailable')
                return 'ready'
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, Path(current_directory_name))), patch('huggingface_hub.snapshot_download', fake_snapshot_download):
                self.assertEqual(model_huggingface_download.tracked_snapshot_download('repo'), 'ready')

class ExistingPartialVerificationTest(unittest.TestCase):
    def test_existing_fragment_is_compared_and_resumed(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import tempfile
        from threading import Thread
        from unittest.mock import patch
        from tools.review.common import model_http_download
        from tools.review.common.model_download_records import ModelDownloadRecord, track_model_download
        current_content_bytes = b'abcdefgh' * 300000
        current_range_values = []
        class RangeTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value = int(current_start_text)
                current_end_value = int(current_end_text) if current_end_text else len(current_content_bytes)-1
                current_response_bytes = current_content_bytes[current_start_value:current_end_value+1]
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(len(current_response_bytes)))
                self.end_headers()
                self.wfile.write(current_response_bytes)
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1',0), RangeTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path = Path(current_directory_name)
                current_original_path = current_root_path/'old.incomplete'
                current_original_path.write_bytes(current_content_bytes[:1200000])
                current_target_path = current_root_path/'model.bin'
                current_partial_path = current_target_path.with_suffix('.bin.partial')
                current_record_value = ModelDownloadRecord('test-model', current_root_path/'records')
                current_record_value.update()
                current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/file'
                current_wrong_bytes = b'x' * 1200000
                current_original_path.write_bytes(current_wrong_bytes)
                with self.assertRaisesRegex(ValueError, '일치하지 않습니다'):
                    model_http_download.import_verified_http_prefix(current_download_url, current_original_path, current_root_path/'wrong.partial', len(current_content_bytes), current_record_value)
                self.assertFalse((current_root_path/'wrong.partial').exists())
                self.assertEqual(current_original_path.read_bytes(), current_wrong_bytes)
                current_original_path.write_bytes(current_content_bytes[:1200000])
                self.assertEqual(model_http_download.import_verified_http_prefix(current_download_url, current_original_path, current_partial_path, len(current_content_bytes), current_record_value), 1200000)
                with patch.object(model_http_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_root_path/'records')):
                    model_http_download.download_verified_http(current_download_url, current_target_path, hashlib.sha256(current_content_bytes).hexdigest(), 'test-model')
                self.assertEqual(current_target_path.read_bytes(), current_content_bytes)
                self.assertEqual(current_original_path.read_bytes(), current_content_bytes[:1200000])
                self.assertEqual(current_range_values, ['bytes=0-1199999', 'bytes=0-1199999', 'bytes=1200000-'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class HuggingFaceExistingPartialTest(unittest.TestCase):
    def test_legacy_fragment_is_verified_and_restored_during_snapshot(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import tempfile
        from threading import Thread
        from types import SimpleNamespace
        from unittest.mock import patch
        from huggingface_hub._local_folder import get_local_download_paths
        from tools.review.common import model_huggingface_download, model_huggingface_recovery, model_http_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        current_content_bytes = b'abcdefgh' * 300000
        current_expected_hash = hashlib.sha256(current_content_bytes).hexdigest()
        current_range_values = []
        class RangeTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value = int(current_start_text)
                current_end_value = int(current_end_text) if current_end_text else len(current_content_bytes)-1
                current_response_bytes = current_content_bytes[current_start_value:current_end_value+1]
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(len(current_response_bytes)))
                self.end_headers()
                self.wfile.write(current_response_bytes)
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1',0), RangeTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path = Path(current_directory_name)
                current_model_root = current_root_path/'model'
                current_local_paths = get_local_download_paths(current_model_root, 'weights.bin')
                current_old_path = current_local_paths.incomplete_path(current_expected_hash).with_name(current_local_paths.incomplete_path(current_expected_hash).stem + '.12345678.incomplete')
                current_old_path.write_bytes(current_content_bytes[:1200000])
                current_probe_record = SimpleNamespace(filename='weights.bin', file_size=len(current_content_bytes), is_cached=False, will_download=True, commit_hash='a'*40, local_path=str(current_local_paths.file_path))
                def fake_snapshot_download(repo_id, *, local_dir=None, revision=None, dry_run=False, tqdm_class=None, endpoint=None):
                    if dry_run:
                        return [current_probe_record]
                    self.assertEqual(current_local_paths.file_path.read_bytes(), current_content_bytes)
                    return str(current_model_root)
                current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/file'
                current_record_factory = lambda current_name: track_model_download(current_name, current_root_path/'records')
                with patch.object(model_huggingface_download, 'track_model_download', current_record_factory), patch.object(model_huggingface_recovery, 'track_model_download', current_record_factory), patch.object(model_http_download, 'track_model_download', current_record_factory), patch('huggingface_hub.snapshot_download', fake_snapshot_download), patch('huggingface_hub.hf_hub_url', return_value=current_download_url), patch('huggingface_hub.get_hf_file_metadata', return_value=SimpleNamespace(etag=current_expected_hash, size=len(current_content_bytes))):
                    model_huggingface_download.tracked_snapshot_download('local/model', revision='a'*40, local_dir=current_model_root)
                self.assertEqual(current_range_values, ['bytes=0-1199999', 'bytes=1200000-'])
                self.assertEqual(current_old_path.read_bytes(), current_content_bytes[:1200000])
                self.assertTrue(any(current_record.get('resumed_bytes') == 1200000 and current_record['status'] == 'completed' for current_record in list_model_download_records(current_root_path/'records')))
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class HuggingFaceRecoveryRetryTest(unittest.TestCase):
    def test_recovery_interrupted_and_retried_without_losing_original(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import tempfile
        from threading import Thread
        from types import SimpleNamespace
        from unittest.mock import patch
        from huggingface_hub._local_folder import get_local_download_paths
        from tools.review.common import model_huggingface_recovery, model_http_download
        from tools.review.common.model_download_records import track_model_download
        current_content_bytes = b'abcdefgh' * 600000
        current_expected_hash = hashlib.sha256(current_content_bytes).hexdigest()
        current_range_values = []
        class InterruptTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value = int(current_start_text)
                current_end_value = int(current_end_text) if current_end_text else len(current_content_bytes)-1
                current_response_bytes = current_content_bytes[current_start_value:current_end_value+1]
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(len(current_response_bytes)))
                self.end_headers()
                if len(current_range_values) == 2:
                    self.wfile.write(current_response_bytes[:1200000])
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.wfile.write(current_response_bytes)
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), InterruptTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path = Path(current_directory_name)
                current_model_root = current_root_path/'model'
                current_local_paths = get_local_download_paths(current_model_root, 'weights.bin')
                current_old_path = current_local_paths.incomplete_path(current_expected_hash).with_name(current_local_paths.incomplete_path(current_expected_hash).stem + '.12345678.incomplete')
                current_old_path.write_bytes(current_content_bytes[:1200000])
                current_probe_record = SimpleNamespace(filename='weights.bin', file_size=len(current_content_bytes), local_path=str(current_local_paths.file_path))
                current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/file'
                current_record_factory = lambda current_name: track_model_download(current_name, current_root_path/'records')
                with patch.object(model_huggingface_recovery, 'track_model_download', current_record_factory), patch.object(model_http_download, 'track_model_download', current_record_factory), patch('huggingface_hub.hf_hub_url', return_value=current_download_url), patch('huggingface_hub.get_hf_file_metadata', return_value=SimpleNamespace(etag=current_expected_hash, size=len(current_content_bytes))):
                    with self.assertRaises((ValueError, OSError)):
                        model_huggingface_recovery.recover_huggingface_partial('local/model', 'a'*40, current_model_root, current_probe_record)
                    current_partial_path = current_local_paths.file_path.with_suffix('.bin.partial')
                    current_partial_size = current_partial_path.stat().st_size
                    self.assertGreater(current_partial_size, 1200000)
                    self.assertTrue(model_huggingface_recovery.recover_huggingface_partial('local/model', 'a'*40, current_model_root, current_probe_record))
                self.assertEqual(current_local_paths.file_path.read_bytes(), current_content_bytes)
                self.assertEqual(current_old_path.read_bytes(), current_content_bytes[:1200000])
                self.assertEqual(current_range_values[2:], [f'bytes={current_partial_size}-'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class CurrentDownloadStatusTest(unittest.TestCase):
    def test_retains_active_and_only_latest_result_per_model(self):
        import json
        import os
        from pathlib import Path
        import tempfile
        from tools.review.common.model_download_records import list_model_download_records
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_records = [
                ('old.json', {'model': 'A', 'status': 'failed', 'updated_at': '2026-01-01T00:00:00Z'}),
                ('new.json', {'model': 'A', 'status': 'completed', 'updated_at': '2026-01-02T00:00:00Z'}),
                ('active1.json', {'model': 'A', 'status': 'running', 'pid': os.getpid(), 'updated_at': '2026-01-03T00:00:00Z'}),
                ('active2.json', {'model': 'A', 'status': 'running', 'pid': os.getpid(), 'updated_at': '2026-01-04T00:00:00Z'}),
            ]
            for current_file_name, current_record_value in current_records:
                (current_root_path/current_file_name).write_text(json.dumps(current_record_value))
            current_result_values = list_model_download_records(current_root_path)
            self.assertEqual([current_value['status'] for current_value in current_result_values], ['running', 'running', 'completed'])
            self.assertFalse((current_root_path/'old.json').exists())
            self.assertTrue((current_root_path/'active1.json').exists())
            self.assertTrue((current_root_path/'active2.json').exists())

    def test_recent_results_are_bounded_without_limiting_active(self):
        import json
        import os
        from pathlib import Path
        import tempfile
        from tools.review.common.model_download_records import MODEL_DOWNLOAD_RECENT_LIMIT, list_model_download_records
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            for current_index_value in range(35):
                (current_root_path/f'active{current_index_value}.json').write_text(json.dumps({'model': f'active{current_index_value}', 'status': 'running', 'pid': os.getpid(), 'updated_at': f'{current_index_value:02}'}))
            for current_index_value in range(25):
                (current_root_path/f'done{current_index_value}.json').write_text(json.dumps({'model': f'done{current_index_value}', 'status': 'completed', 'updated_at': f'{current_index_value:02}'}))
            current_result_values = list_model_download_records(current_root_path)
            self.assertEqual(sum(current_record_value['status'] == 'running' for current_record_value in current_result_values), 35)
            self.assertEqual(sum(current_record_value['status'] == 'completed' for current_record_value in current_result_values), MODEL_DOWNLOAD_RECENT_LIMIT)
            self.assertEqual(len(list(current_root_path.glob('done*.json'))), MODEL_DOWNLOAD_RECENT_LIMIT)

    def test_each_model_shows_own_progress_and_recent_result(self):
        from tools.review.common.gradio_model_download import format_model_download_status
        current_status_values = [
            {'model': 'Qwen/Qwen-Image-2.1', 'status': 'running', 'stage': '다운로드', 'bytes': 50, 'total_bytes': 100},
            {'model': 'nvidia/Kimodo', 'status': 'failed', 'stage': '다운로드', 'bytes': 0, 'total_bytes': None},
            {'model': 'Qwen/Qwen-Image-2.1/shard', 'status': 'completed', 'stage': '검증', 'bytes': 100, 'total_bytes': 100},
            {'model': 'Qwen/Qwen-Image-2.1/old', 'status': 'failed', 'stage': '다운로드', 'bytes': 0, 'total_bytes': None},
        ]
        current_status_text = format_model_download_status(current_status_values, 'prop-generator')
        self.assertIn('Qwen/Qwen-Image-2.1 · 진행 중', current_status_text)
        self.assertIn('50.0%', current_status_text)
        self.assertIn('Qwen/Qwen-Image-2.1/shard · 완료', current_status_text)
        self.assertNotIn('nvidia/Kimodo', current_status_text)
        self.assertNotIn('Qwen/Qwen-Image-2.1/old', current_status_text)

    def test_existing_partial_verification_is_distinct_from_download(self):
        from tools.review.common.gradio_model_download import format_model_download_status
        current_status_values = [{'model': 'Qwen/Qwen-Image-2.1/shard', 'status': 'running',
                                  'stage': '기존 부분 파일 검증', 'bytes': 40, 'total_bytes': 200,
                                  'existing_bytes': 100, 'resumed_bytes': 20}]
        current_status_text = format_model_download_status(current_status_values, 'prop-generator')
        self.assertIn('기존 부분 100바이트 보존', current_status_text)
        self.assertIn('검증 40.0% (40 / 100바이트)', current_status_text)
        self.assertIn('시작 시 검증 지점 20바이트', current_status_text)

class DetachedModelPreparationTest(unittest.TestCase):
    def test_worker_survives_launcher_exit_and_remains_singleton(self):
        import json
        import subprocess
        import sys
        import tempfile
        import time
        from pathlib import Path
        from tools.review.common.model_prepare_process import inspect_detached_preparation
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_worker_path = current_root_path/'worker.py'
            current_worker_path.write_text("""import argparse,json,os,time\np=argparse.ArgumentParser();p.add_argument('--status-path');p.add_argument('--lock-fd',type=int);a=p.parse_args()\nwith os.fdopen(a.lock_fd,'a'):\n open(a.status_path,'w').write(json.dumps({'status':'running'}))\n while not os.path.exists(os.path.join(os.path.dirname(a.status_path),'release')): time.sleep(.05)\n open(a.status_path,'w').write(json.dumps({'status':'completed'}))\n""")
            current_launcher_code = "from pathlib import Path;import sys;from tools.review.common.model_prepare_process import start_detached_preparation;print(start_detached_preparation(Path(sys.argv[1]),[sys.executable,sys.argv[2]],Path.cwd()))"
            subprocess.run([sys.executable, '-c', current_launcher_code, str(current_root_path), str(current_worker_path)], check=True, capture_output=True, text=True)
            try:
                current_deadline_value = time.monotonic()+10
                while not (current_root_path/'status.json').exists() and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
                self.assertEqual(inspect_detached_preparation(current_root_path), 'running')
                self.assertEqual(json.loads((current_root_path/'status.json').read_text())['status'], 'running')
            finally:
                (current_root_path/'release').touch()
                current_deadline_value = time.monotonic()+10
                while inspect_detached_preparation(current_root_path) == 'running' and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
            self.assertEqual(inspect_detached_preparation(current_root_path), 'completed')

class VerificationCheckpointIntegrationTest(unittest.TestCase):
    def test_http_interruption_resumes_from_verified_checkpoint(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import tempfile
        from threading import Thread
        from tools.review.common.model_download_records import ModelDownloadRecord
        from tools.review.common.model_http_download import import_verified_http_prefix
        current_content_bytes = b'abcdefgh' * (5 * 1024 * 1024)
        current_prefix_bytes = 36 * 1024 * 1024
        current_range_values = []
        class CheckpointTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value, current_end_value = int(current_start_text), int(current_end_text)
                current_response_bytes = current_content_bytes[current_start_value:current_end_value+1]
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(len(current_response_bytes)))
                self.end_headers()
                if len(current_range_values) == 1:
                    self.wfile.write(current_response_bytes[:20*1024*1024])
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.wfile.write(current_response_bytes)
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), CheckpointTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path = Path(current_directory_name)
                current_source_path = current_root_path/'source.incomplete'
                current_source_path.write_bytes(current_content_bytes[:current_prefix_bytes])
                current_target_path = current_root_path/'model.partial'
                current_record_value = ModelDownloadRecord('test-model', current_root_path/'records')
                current_record_value.update()
                current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/file'
                current_identity_value = hashlib.sha256(current_content_bytes).hexdigest()
                with self.assertRaises((ValueError, OSError)):
                    import_verified_http_prefix(current_download_url, current_source_path, current_target_path, len(current_content_bytes), current_record_value, expected_identity_value=current_identity_value)
                self.assertFalse(current_target_path.exists())
                current_checkpoint_data = current_target_path.with_name(current_target_path.name+'.checkpoint.bin')
                with current_checkpoint_data.open('r+b') as current_checkpoint_stream:
                    current_original_byte = current_checkpoint_stream.read(1)
                    current_checkpoint_stream.seek(0)
                    current_checkpoint_stream.write(b'X')
                with self.assertRaisesRegex(ValueError, '변경|해시'):
                    import_verified_http_prefix(current_download_url, current_source_path, current_target_path, len(current_content_bytes), current_record_value, expected_identity_value=current_identity_value)
                with current_checkpoint_data.open('r+b') as current_checkpoint_stream:
                    current_checkpoint_stream.write(current_original_byte)
                self.assertEqual(import_verified_http_prefix(current_download_url, current_source_path, current_target_path, len(current_content_bytes), current_record_value, expected_identity_value=current_identity_value), current_prefix_bytes)
                self.assertEqual(current_target_path.read_bytes(), current_content_bytes[:current_prefix_bytes])
                self.assertEqual(current_source_path.read_bytes(), current_content_bytes[:current_prefix_bytes])
                self.assertEqual(current_range_values, [f'bytes=0-{current_prefix_bytes-1}', f'bytes={16*1024*1024}-{current_prefix_bytes-1}'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class VerificationCommitCrashTest(unittest.TestCase):
    def test_killed_after_link_or_replace_recovers_without_rechecking_prefix(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import os
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        from threading import Thread
        from types import SimpleNamespace
        from unittest.mock import patch
        from huggingface_hub._local_folder import get_local_download_paths
        from tools.review.common import model_huggingface_recovery, model_http_download
        from tools.review.common.model_download_records import track_model_download
        current_content_bytes = b'abcdefgh' * 300000
        current_expected_hash = hashlib.sha256(current_content_bytes).hexdigest()
        current_range_values = []
        class CrashTestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value = int(current_start_text)
                current_end_value = int(current_end_text) if current_end_text else len(current_content_bytes)-1
                current_response_bytes = current_content_bytes[current_start_value:current_end_value+1]
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(len(current_response_bytes)))
                self.end_headers()
                self.wfile.write(current_response_bytes)
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1', 0), CrashTestHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 HTTP 통합 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        current_child_script = '''
import os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.review.common import model_huggingface_recovery, model_http_download
from tools.review.common.model_download_records import track_model_download
root=Path(sys.argv[1]); url=sys.argv[2]; digest=sys.argv[3]; size=int(sys.argv[4]); mode=sys.argv[5]
record=SimpleNamespace(filename='weights.bin',file_size=size,local_path=str(root/'model/weights.bin'))
factory=lambda name: track_model_download(name,root/'records')
real_link=os.link; real_replace=os.replace
def interrupt_link(src,dst,*args,**kwargs):
 result=real_link(src,dst,*args,**kwargs)
 if mode=='link' and str(dst).endswith('weights.bin.partial'): os._exit(73)
 return result
def interrupt_replace(src,dst,*args,**kwargs):
 result=real_replace(src,dst,*args,**kwargs)
 if mode=='replace' and str(src).endswith('weights.bin.partial.verified') and str(dst).endswith('weights.bin.partial'): os._exit(74)
 if mode=='publish' and str(src).endswith('weights.bin.partial') and str(dst).endswith('/weights.bin'): os._exit(75)
 return result
with patch.object(model_huggingface_recovery,'track_model_download',factory),patch.object(model_http_download,'track_model_download',factory),patch('huggingface_hub.hf_hub_url',return_value=url),patch('huggingface_hub.get_hf_file_metadata',return_value=SimpleNamespace(etag=digest,size=size)),patch('os.link',side_effect=interrupt_link),patch('os.replace',side_effect=interrupt_replace):
 model_huggingface_recovery.recover_huggingface_partial('local/model','a'*40,root/'model',record)
'''
        try:
            for current_mode_value in ('link', 'replace', 'publish'):
                with self.subTest(mode=current_mode_value), tempfile.TemporaryDirectory() as current_directory_name:
                    current_root_path = Path(current_directory_name)
                    current_model_root = current_root_path/'model'
                    current_local_paths = get_local_download_paths(current_model_root, 'weights.bin')
                    current_old_path = current_local_paths.incomplete_path(current_expected_hash)
                    if current_mode_value == 'link':
                        current_old_path.write_bytes(current_content_bytes[:1200000])
                    else:
                        current_local_paths.file_path.with_suffix('.bin.partial').write_bytes(current_content_bytes[:1200000])
                    current_download_url = f'http://127.0.0.1:{current_server_value.server_port}/file'
                    current_range_values.clear()
                    current_child_result = subprocess.run([sys.executable, '-c', current_child_script, str(current_root_path), current_download_url, current_expected_hash, str(len(current_content_bytes)), current_mode_value], cwd=Path.cwd(), capture_output=True, timeout=30)
                    self.assertEqual(current_child_result.returncode, {'link': 73, 'replace': 74, 'publish': 75}[current_mode_value], current_child_result.stderr.decode(errors='replace'))
                    current_record_factory = lambda current_name: track_model_download(current_name, current_root_path/'records')
                    current_probe_record = SimpleNamespace(filename='weights.bin', file_size=len(current_content_bytes), local_path=str(current_local_paths.file_path))
                    with patch.object(model_huggingface_recovery, 'track_model_download', current_record_factory), patch.object(model_http_download, 'track_model_download', current_record_factory), patch('huggingface_hub.hf_hub_url', return_value=current_download_url), patch('huggingface_hub.get_hf_file_metadata', return_value=SimpleNamespace(etag=current_expected_hash, size=len(current_content_bytes))):
                        if current_mode_value == 'link':
                            current_partial_path = current_local_paths.file_path.with_suffix('.bin.partial')
                            with current_partial_path.open('r+b') as current_partial_stream:
                                current_partial_stream.write(b'X')
                            with self.assertRaisesRegex(ValueError, '해시'):
                                model_huggingface_recovery.recover_huggingface_partial('local/model', 'a'*40, current_model_root, current_probe_record)
                            with current_partial_path.open('r+b') as current_partial_stream:
                                current_partial_stream.write(current_content_bytes[:1])
                        if current_mode_value == 'publish':
                            self.assertFalse(model_huggingface_recovery.recover_huggingface_partial('local/model', 'a'*40, current_model_root, current_probe_record))
                        else:
                            self.assertTrue(model_huggingface_recovery.recover_huggingface_partial('local/model', 'a'*40, current_model_root, current_probe_record))
                    self.assertEqual(current_local_paths.file_path.read_bytes(), current_content_bytes)
                    self.assertEqual(current_range_values, ['bytes=0-1199999', 'bytes=1200000-'])
                    if current_mode_value == 'link':
                        self.assertEqual(current_old_path.read_bytes(), current_content_bytes[:1200000])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class GatewayRestartIsolationTest(unittest.TestCase):
    def test_gateway_exit_preserves_worker_and_status(self):
        import os
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        import time
        from tools.review.common.management_gateway import execute_management_command
        from tools.review.common.model_prepare_process import inspect_detached_preparation, start_detached_preparation
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_worker_path = current_root_path/'worker.py'
            current_worker_path.write_text("""import sys,time,types
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.review.common import model_prepare_worker
current_root_path = Path(sys.argv[sys.argv.index('--status-path')+1]).parent
current_test_module = types.ModuleType('isolated_model_preparer')
def prepare_test_model():
 (current_root_path/'ready').touch()
 while not (current_root_path/'release').exists(): time.sleep(.05)
current_test_module.prepare_test_model = prepare_test_model
sys.modules['isolated_model_preparer'] = current_test_module
model_prepare_worker.MODEL_PREPARATION_PROFILES['isolated'] = (('isolated_model_preparer','prepare_test_model'),)
sys.argv[1:1] = ['--profile','isolated']
model_prepare_worker.run_registered_model_preparation()
""")
            current_gateway_code = '''
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from tools.review.common.management_gateway import ManagementCommandGateway
from tools.review.common.management_transport import send_management_json_response
from tools.review.common.model_prepare_process import start_detached_preparation
from tools.review.gateway_server import create_gateway_request_handler
root=Path(sys.argv[1]);worker=sys.argv[2]
def handle_request(handler):
 return send_management_json_response(handler,200,start_detached_preparation(root,[sys.executable,worker],Path.cwd()))
gateway=ManagementCommandGateway({'prop-generator':handle_request})
server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(gateway.handle))
server.emit_gateway_trace=lambda *args: None
print(server.server_port,flush=True)
server.serve_forever()
'''
            current_gateway_process = subprocess.Popen([sys.executable, '-c', current_gateway_code, str(current_root_path), str(current_worker_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                current_port_line = current_gateway_process.stdout.readline().strip()
                if not current_port_line:
                    current_error_text = current_gateway_process.stderr.read()
                    if 'Operation not permitted' in current_error_text:
                        self.skipTest('로컬 소켓 권한이 없어 실제 게이트웨이 검사를 생략합니다.')
                    self.fail('격리 게이트웨이 시작 실패: '+current_error_text)
                current_gateway_address = f'http://127.0.0.1:{int(current_port_line)}'
                current_response_value = execute_management_command('prop-generator', 'prepare', {'action': 'prepare'}, current_gateway_address)
                self.assertEqual(current_response_value['preparation_status'], 'running')
                current_deadline_value = time.monotonic()+10
                while not (current_root_path/'ready').exists() and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
                self.assertTrue((current_root_path/'ready').exists(), (current_root_path/'worker.log').read_text(errors='replace'))
                self.assertEqual(inspect_detached_preparation(current_root_path), 'running')
                current_gateway_process.terminate()
                current_gateway_process.wait(timeout=10)
                self.assertEqual(inspect_detached_preparation(current_root_path), 'running')
                self.assertEqual(start_detached_preparation(current_root_path, [sys.executable, str(current_worker_path)], Path.cwd()), {'preparation_status': 'running'})
            finally:
                (current_root_path/'release').touch()
                current_deadline_value = time.monotonic()+10
                while inspect_detached_preparation(current_root_path) == 'running' and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
                if current_gateway_process.poll() is None:
                    current_gateway_process.terminate()
                    current_gateway_process.wait(timeout=10)
                current_gateway_process.stdout.close()
                current_gateway_process.stderr.close()
            self.assertEqual(inspect_detached_preparation(current_root_path), 'completed')

class WriterPreparationLifecycleTest(unittest.TestCase):
    def test_gateway_close_preserves_preparation_but_not_other_writer_jobs(self):
        from unittest.mock import MagicMock, patch
        from generators.writer_agent.management import WriterAgentManager
        current_manager_value = WriterAgentManager()
        current_process_value = MagicMock()
        current_process_value.poll.return_value = None
        current_process_value.pid = 12345
        current_manager_value.worker_process_handle = current_process_value
        with patch('generators.writer_agent.management.os.killpg') as current_signal_mock:
            current_manager_value.worker_prepare_flag = True
            current_manager_value.close_writer_worker()
            current_signal_mock.assert_not_called()
            current_manager_value.worker_prepare_flag = False
            current_manager_value.close_writer_worker()
            current_signal_mock.assert_called_once()

    def test_writer_preparation_records_completion_without_gateway_monitor(self):
        import contextlib
        import json
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        from generators.writer_agent import prepare
        from generators.writer_agent.documents import read_yaml_document
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_arguments = SimpleNamespace(run_dir=current_root_path/'job', status_path=current_root_path/'status.json', lock_fd=None)
            with patch.object(prepare, 'RUNTIME_INSTALL_ROOT', current_root_path/'runtime'), patch.object(prepare, 'lock_gpu_runtime', return_value=contextlib.nullcontext()), patch.object(prepare, 'CURRENT_LOG_PATH', None):
                prepare.execute_writer_preparation(current_arguments, lambda: None)
            self.assertEqual(read_yaml_document(current_arguments.run_dir/'status.yaml')['stage'], 'completed')
            self.assertEqual(json.loads(current_arguments.status_path.read_text())['status'], 'completed')

class HttpResumeSafetyTest(unittest.TestCase):
    def test_server_ignoring_range_keeps_existing_partial(self):
        from email.message import Message
        from io import BytesIO
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from tools.review.common import model_http_download
        from tools.review.common.model_download_records import track_model_download
        class FullResponse(BytesIO):
            status = 200
            headers = Message()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_target_path = current_root_path/'model.bin'
            current_partial_path = current_target_path.with_suffix('.bin.partial')
            current_partial_path.write_bytes(b'preserved')
            with patch.object(model_http_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_root_path/'records')), patch('urllib.request.urlopen', return_value=FullResponse(b'full content')):
                with self.assertRaisesRegex(ValueError, '보존'):
                    model_http_download.download_verified_http('https://example.invalid/file', current_target_path, '0'*64, 'test')
            self.assertEqual(current_partial_path.read_bytes(), b'preserved')
            self.assertFalse(current_target_path.exists())

class CommonPreparationProfileTest(unittest.TestCase):
    def test_registered_profiles_share_one_worker_and_reject_unknown(self):
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.common.model_prepare_process import start_registered_preparation
        current_root_path = Path('/tmp/isolated-profile')
        with patch('tools.review.common.model_prepare_process.start_detached_preparation', return_value={'preparation_status': 'running'}) as current_start_mock:
            for current_profile_name in ('qwen-21', 'kimodo', 'wan-animate2'):
                self.assertEqual(start_registered_preparation(current_root_path, current_profile_name), {'preparation_status': 'running'})
                current_command_values = current_start_mock.call_args.args[1]
                self.assertEqual(current_command_values[1:3], ['-m', 'tools.review.common.model_prepare_worker'])
                self.assertEqual(current_command_values[-1], current_profile_name)
            with self.assertRaises(ValueError):
                start_registered_preparation(current_root_path, '../unknown')

    def test_legacy_vace_partial_uses_common_downloader(self):
        import hashlib
        from email.message import Message
        from io import BytesIO
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from tools.review.common import model_http_download
        from tools.review.common.model_download_records import track_model_download
        current_content_bytes = b'known-model-data'
        class PartialResponse(BytesIO):
            status = 206
            def __init__(self):
                super().__init__(current_content_bytes[5:])
                self.headers = Message()
                self.headers['Content-Range'] = f'bytes 5-{len(current_content_bytes)-1}/{len(current_content_bytes)}'
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_target_path = current_root_path/'model.gguf'
            current_legacy_path = current_target_path.with_suffix('.partial')
            current_legacy_path.write_bytes(current_content_bytes[:5])
            with patch.object(model_http_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_root_path/'records')), patch('urllib.request.urlopen', return_value=PartialResponse()):
                model_http_download.download_verified_http('https://example.invalid/model', current_target_path, hashlib.sha256(current_content_bytes).hexdigest(), 'vace-test', current_partial_path=current_legacy_path, expected_total_bytes=len(current_content_bytes))
            self.assertEqual(current_target_path.read_bytes(), current_content_bytes)
            self.assertFalse(current_legacy_path.exists())

class SingleFileSharedRecoveryTest(unittest.TestCase):
    def test_single_file_uses_same_recovery_path(self):
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_local_root = current_root_path/'model'
            current_probe_value = SimpleNamespace(filename='weights.bin', file_size=100, is_cached=False, will_download=True, commit_hash='a'*40, local_path=str(current_local_root/'weights.bin'))
            def fake_hub_download(repo_id, filename, *, local_dir=None, revision=None, dry_run=False, tqdm_class=None):
                if dry_run:
                    return current_probe_value
                return str(current_local_root/'weights.bin')
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name,current_root_path/'records')), patch('huggingface_hub.hf_hub_download', fake_hub_download), patch('tools.review.common.model_huggingface_recovery.recover_huggingface_partial', return_value=True) as current_recovery_mock:
                model_huggingface_download.tracked_hf_hub_download('repo', 'weights.bin', revision='a'*40, local_dir=current_local_root)
            current_recovery_mock.assert_called_once()
            current_record_value = list_model_download_records(current_root_path/'records')[0]
            self.assertEqual((current_record_value['bytes'],current_record_value['total_bytes'],current_record_value['status']), (100,100,'completed'))

    def test_curl_transport_uses_common_status_and_integrity(self):
        import hashlib
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from tools.review.common import model_http_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_target_path=current_root_path/'model.gguf'
            current_target_path.write_bytes(b'abc')
            def fake_curl_command(current_command_values, **current_options):
                self.assertIn('--continue-at', current_command_values)
                with current_target_path.open('ab') as current_file_stream:
                    current_file_stream.write(b'def')
            with patch.object(model_http_download, 'track_model_download', lambda current_name: track_model_download(current_name,current_root_path/'records')), patch('subprocess.run', side_effect=fake_curl_command):
                model_http_download.download_verified_curl('https://example.invalid/model',current_target_path,hashlib.sha256(b'abcdef').hexdigest(),6,'ollama-test')
            current_record_value=list_model_download_records(current_root_path/'records')[0]
            self.assertEqual((current_record_value['status'],current_record_value['bytes'],current_record_value['resumed_bytes']),('completed',6,3))

class CommonPreparationFailureTest(unittest.TestCase):
    def test_corrupt_recovery_does_not_fall_back_to_new_download(self):
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        from tools.review.common.model_huggingface_recovery import ModelRecoveryError
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_probe_record = SimpleNamespace(filename='weights.bin',file_size=100,is_cached=False,will_download=True,commit_hash='a'*40,local_path=str(current_root_path/'model/weights.bin'))
            current_actual_calls = []
            def fake_snapshot_download(repo_id, *, revision=None, local_dir=None, dry_run=False, tqdm_class=None):
                if dry_run:
                    return [current_probe_record]
                current_actual_calls.append('download')
                return str(local_dir)
            with patch.object(model_huggingface_download,'track_model_download',lambda current_name: track_model_download(current_name,current_root_path/'records')), patch('huggingface_hub.snapshot_download',fake_snapshot_download), patch('tools.review.common.model_huggingface_recovery.recover_huggingface_partial',side_effect=ModelRecoveryError('검증 지점 손상')):
                with self.assertRaisesRegex(ModelRecoveryError,'검증 지점 손상'):
                    model_huggingface_download.tracked_snapshot_download('repo',revision='a'*40,local_dir=current_root_path/'model')
            self.assertEqual(current_actual_calls, [])
            self.assertEqual(list_model_download_records(current_root_path/'records')[0]['status'],'failed')

    def test_worker_start_failure_is_not_reported_as_completed(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from tools.review.common.model_prepare_process import inspect_detached_preparation, start_detached_preparation
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            with patch('tools.review.common.model_prepare_process.subprocess.Popen',side_effect=OSError('start failed')):
                with self.assertRaises(OSError):
                    start_detached_preparation(current_root_path,['unavailable'],current_root_path)
            self.assertEqual(inspect_detached_preparation(current_root_path),'failed')

class VerificationProcessKillTest(unittest.TestCase):
    def test_process_killed_after_checkpoint_resumes_at_saved_offset(self):
        import hashlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        from threading import Thread
        from types import SimpleNamespace
        from unittest.mock import patch
        from huggingface_hub._local_folder import get_local_download_paths
        from tools.review.common import model_huggingface_recovery, model_http_download
        from tools.review.common.model_download_records import track_model_download
        current_content_bytes = b'abcdefgh' * (3 * 1024 * 1024)
        current_prefix_bytes = 20 * 1024 * 1024
        current_expected_hash = hashlib.sha256(current_content_bytes).hexdigest()
        current_range_values = []
        class CheckpointKillHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                current_range_text = self.headers['Range']
                current_range_values.append(current_range_text)
                current_start_text, current_end_text = current_range_text[6:].split('-')
                current_start_value = int(current_start_text)
                current_end_value = int(current_end_text) if current_end_text else len(current_content_bytes)-1
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {current_start_value}-{current_end_value}/{len(current_content_bytes)}')
                self.send_header('Content-Length', str(current_end_value-current_start_value+1))
                self.end_headers()
                try:
                    self.wfile.write(current_content_bytes[current_start_value:current_end_value+1])
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *current_arguments):
                pass
        try:
            current_server_value = ThreadingHTTPServer(('127.0.0.1',0), CheckpointKillHandler)
        except PermissionError:
            self.skipTest('로컬 소켓 권한이 없어 프로세스 중단 검사를 생략합니다.')
        current_server_thread = Thread(target=current_server_value.serve_forever, daemon=True)
        current_server_thread.start()
        current_child_script = '''
import json,os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.review.common import model_huggingface_recovery,model_http_download
from tools.review.common.model_download_records import track_model_download
root=Path(sys.argv[1]);url=sys.argv[2];digest=sys.argv[3];size=int(sys.argv[4])
record=SimpleNamespace(filename='weights.bin',file_size=size,local_path=str(root/'model/weights.bin'))
factory=lambda name: track_model_download(name,root/'records')
real_replace=os.replace
def kill_after_checkpoint(src,dst,*args,**kwargs):
 is_checkpoint=str(dst).endswith('.checkpoint.json')
 committed=json.loads(Path(src).read_text())['bytes'] if is_checkpoint else 0
 result=real_replace(src,dst,*args,**kwargs)
 if is_checkpoint and committed>=16*1024*1024: os._exit(76)
 return result
with patch.object(model_huggingface_recovery,'track_model_download',factory),patch.object(model_http_download,'track_model_download',factory),patch('huggingface_hub.hf_hub_url',return_value=url),patch('huggingface_hub.get_hf_file_metadata',return_value=SimpleNamespace(etag=digest,size=size)),patch('os.replace',side_effect=kill_after_checkpoint):
 model_huggingface_recovery.recover_huggingface_partial('local/model','a'*40,root/'model',record)
'''
        try:
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path=Path(current_directory_name)
                current_model_root=current_root_path/'model'
                current_local_paths=get_local_download_paths(current_model_root,'weights.bin')
                current_old_path=current_local_paths.incomplete_path(current_expected_hash)
                current_old_path.write_bytes(current_content_bytes[:current_prefix_bytes])
                current_download_url=f'http://127.0.0.1:{current_server_value.server_port}/file'
                current_child_result=subprocess.run([sys.executable,'-c',current_child_script,str(current_root_path),current_download_url,current_expected_hash,str(len(current_content_bytes))],cwd=Path.cwd(),capture_output=True,timeout=30)
                self.assertEqual(current_child_result.returncode,76,current_child_result.stderr.decode(errors='replace'))
                current_record_factory=lambda current_name:track_model_download(current_name,current_root_path/'records')
                current_probe_record=SimpleNamespace(filename='weights.bin',file_size=len(current_content_bytes),local_path=str(current_local_paths.file_path))
                with patch.object(model_huggingface_recovery,'track_model_download',current_record_factory),patch.object(model_http_download,'track_model_download',current_record_factory),patch('huggingface_hub.hf_hub_url',return_value=current_download_url),patch('huggingface_hub.get_hf_file_metadata',return_value=SimpleNamespace(etag=current_expected_hash,size=len(current_content_bytes))):
                    self.assertTrue(model_huggingface_recovery.recover_huggingface_partial('local/model','a'*40,current_model_root,current_probe_record))
                self.assertEqual(current_local_paths.file_path.read_bytes(),current_content_bytes)
                self.assertEqual(current_old_path.stat().st_size,current_prefix_bytes)
                self.assertEqual(current_range_values,[f'bytes=0-{current_prefix_bytes-1}',f'bytes={16*1024*1024}-{current_prefix_bytes-1}',f'bytes={current_prefix_bytes}-'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join()

class RegisteredPreparationServiceTest(unittest.TestCase):
    def test_all_direct_services_use_shared_profiles_after_manager_recreation(self):
        from unittest.mock import patch
        from tools.review.domains.image import prop_generation
        from tools.review.domains.kimodo import generation as kimodo_generation
        from tools.review.domains.wan_animate2 import generation as animate_generation
        current_service_specs = (
            (prop_generation, prop_generation.PropGenerationManager, 'qwen-21', 'start_prop_model_download', 'inspect_prop_model_status', 'validate_qwen_model_assets'),
            (kimodo_generation, kimodo_generation.KimodoGenerationManager, 'kimodo', 'start_model_preparation', 'inspect_model_preparation', 'inspect_kimodo_assets'),
            (animate_generation, animate_generation.AnimateTwoGenerationManager, 'wan-animate2', 'start_model_download', 'inspect_model_download', 'inspect_animate_assets'),
        )
        for current_module_value, current_manager_class, current_profile_name, current_start_name, current_inspect_name, current_asset_name in current_service_specs:
            with self.subTest(profile=current_profile_name):
                current_asset_result = {'ready': False, 'message': '미준비'}
                current_asset_effect = ValueError('미준비') if current_profile_name == 'qwen-21' else None
                with patch.object(current_module_value, 'inspect_registered_preparation', return_value='idle'), patch.object(current_module_value, current_asset_name, return_value=current_asset_result, side_effect=current_asset_effect), patch.object(current_module_value, 'start_registered_preparation', return_value={'preparation_status':'running'}) as current_start_mock:
                    self.assertEqual(getattr(current_manager_class(), current_start_name)(), {'preparation_status':'running'})
                    self.assertEqual(current_start_mock.call_args.args[1], current_profile_name)
                with patch.object(current_module_value, 'inspect_registered_preparation', return_value='running'), patch.object(current_module_value, current_asset_name, return_value=current_asset_result):
                    self.assertEqual(getattr(current_manager_class(), current_inspect_name)()['preparation_status'], 'running')

class WriterDetachedResumeTest(unittest.TestCase):
    def test_writer_preparation_updates_own_state_after_launcher_exit(self):
        import subprocess
        import sys
        import tempfile
        import time
        from pathlib import Path
        from generators.writer_agent.documents import read_yaml_document, save_yaml_document
        from generators.writer_agent.management import WriterAgentManager
        from tools.review.common.model_prepare_process import inspect_detached_preparation
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_job_root = current_root_path/'job'
            current_job_root.mkdir()
            save_yaml_document(current_job_root/'status.yaml', {'id':'isolated-job','mode':'prepare','stage':'preparing'})
            current_worker_path = current_root_path/'writer_worker.py'
            current_worker_path.write_text('''import argparse,contextlib,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from generators.writer_agent import prepare
p=argparse.ArgumentParser();p.add_argument('--status-path',type=Path);p.add_argument('--lock-fd',type=int);a=p.parse_args()
a.run_dir=Path(__file__).parent/'job'
prepare.RUNTIME_INSTALL_ROOT=Path(__file__).parent/'runtime'
prepare.lock_gpu_runtime=lambda: contextlib.nullcontext()
def prepare_test_assets():
 (Path(__file__).parent/'ready').touch()
 while not (Path(__file__).parent/'release').exists(): time.sleep(.05)
prepare.execute_writer_preparation(a,prepare_test_assets)
''')
            current_state_root = current_root_path/'shared-state'
            current_launcher_code = "from pathlib import Path;import sys;from tools.review.common.model_prepare_process import start_detached_preparation;print(start_detached_preparation(Path(sys.argv[1]),[sys.executable,sys.argv[2]],Path.cwd()))"
            subprocess.run([sys.executable,'-c',current_launcher_code,str(current_state_root),str(current_worker_path)],check=True,capture_output=True,text=True)
            try:
                current_deadline_value=time.monotonic()+10
                while not (current_root_path/'ready').exists() and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
                self.assertTrue((current_root_path/'ready').exists(), (current_state_root/'worker.log').read_text(errors='replace'))
                self.assertEqual(inspect_detached_preparation(current_state_root),'running')
                current_status_value=read_yaml_document(current_job_root/'status.yaml')
                self.assertEqual(WriterAgentManager().resolve_observed_status(current_status_value)['stage'],'preparing')
            finally:
                (current_root_path/'release').touch()
                current_deadline_value=time.monotonic()+10
                while inspect_detached_preparation(current_state_root)=='running' and time.monotonic()<current_deadline_value:
                    time.sleep(.05)
            self.assertEqual(inspect_detached_preparation(current_state_root),'completed')
            self.assertEqual(read_yaml_document(current_job_root/'status.yaml')['stage'],'completed')
