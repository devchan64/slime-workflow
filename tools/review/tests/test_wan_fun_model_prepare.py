"""Wan Fun 모델 준비 명령과 상태 표시 계약."""
import unittest
from unittest.mock import Mock

from tools.review.common.management_gateway import resolve_management_command
from tools.review.ui.gradio.wan_fun_app import build_fun_interface


class FunModelPrepareTests(unittest.TestCase):
    def test_prepare_uses_shared_job_route(self):
        self.assertEqual(resolve_management_command('wan22-fun-control', 'prepare', {'action': 'prepare'}),
                         ('POST', '/wan22-fun-control/jobs'))
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-fun-control', 'prepare', {'action': 'generate'})

    def test_queued_prepare_disables_duplicate_and_reports_errors(self):
        current_command_mock = Mock(side_effect=lambda current_name, current_payload: {
            'model-status': {'ready': False, 'message': '모델 준비 필요'},
            'history': {'records': [{'request': {'action': 'prepare'}, 'status': {'status': 'queued'}}]},
        }[current_name])
        current_interface = build_fun_interface('http://localhost', current_command_mock)
        current_refresh_callback = next(current_function.fn for current_function in current_interface.fns.values()
                                        if current_function.fn and current_function.fn.__name__ == 'refresh_fun_model_controls')
        current_message_value, current_button_update = current_refresh_callback()
        self.assertIn('모델 준비 대기 중', current_message_value)
        self.assertFalse(current_button_update['interactive'])
        current_command_mock.side_effect = OSError('연결 실패')
        current_message_value, current_button_update = current_refresh_callback()
        self.assertIn('연결 실패', current_message_value)
        self.assertFalse(current_button_update['interactive'])

    def test_completed_single_file_keeps_recovered_byte_count(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.review.common import model_huggingface_download
        from tools.review.common.model_download_records import list_model_download_records, track_model_download
        with TemporaryDirectory() as current_temporary_root:
            current_root_path = Path(current_temporary_root)
            current_probe_value = SimpleNamespace(filename='vae.bin', file_size=100, is_cached=False,
                                                  will_download=True, commit_hash='a'*40,
                                                  local_path=str(current_root_path/'vae.bin'))
            def fake_hub_download(repo_id, filename, *, local_dir=None, revision=None, dry_run=False, tqdm_class=None):
                return current_probe_value if dry_run else str(current_root_path/'vae.bin')
            def fake_partial_recovery(*current_args, resume_report_callback=None, **current_kwargs):
                resume_report_callback(40)
                return True
            with patch.object(model_huggingface_download, 'track_model_download', lambda current_name: track_model_download(current_name, current_root_path/'records')), \
                    patch('huggingface_hub.hf_hub_download', fake_hub_download), \
                    patch('tools.review.common.model_huggingface_recovery.recover_huggingface_partial', fake_partial_recovery):
                model_huggingface_download.tracked_hf_hub_download('Comfy-Org/Wan-2.1', 'vae.bin', revision='a'*40, local_dir=current_root_path)
            current_result_record = list_model_download_records(current_root_path/'records')[0]
            self.assertEqual((current_result_record['status'], current_result_record['resumed_bytes']), ('completed', 40))
