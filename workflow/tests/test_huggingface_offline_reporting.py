from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common import model_huggingface_download
from workflow.common.model_download_progress import format_model_download_status
from workflow.common.model_download_records import list_model_download_records, track_model_download


class OfflineReportingTests(unittest.TestCase):
    def test_local_only_scope_forces_hub_download_option_and_restores_it(self):
        calls = []
        with TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_download(repo_id, *, local_dir=None, local_files_only=False, tqdm_class=None):
                calls.append(local_files_only)
                return str(local_dir)
            with patch.object(model_huggingface_download, 'track_model_download',
                              lambda name: track_model_download(name, root/'records')), \
                 patch('huggingface_hub.snapshot_download', fake_download):
                with model_huggingface_download.local_only_huggingface_downloads():
                    model_huggingface_download.tracked_snapshot_download('test', local_dir=str(root), local_files_only=False)
                model_huggingface_download.tracked_snapshot_download('test', local_dir=str(root))
        self.assertEqual(calls, [True, False])

    def test_unverified_local_directory_is_reported_as_needing_validation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_download(repo_id, *, local_dir=None, dry_run=False, tqdm_class=None):
                if dry_run:
                    raise OSError('unavailable')
                return str(local_dir)
            with patch.object(model_huggingface_download, 'track_model_download',
                              lambda name: track_model_download(name, root/'records')), \
                 patch('huggingface_hub.snapshot_download', fake_download):
                result = model_huggingface_download.tracked_snapshot_download('mispeech/Dasheng-AudioGen', local_dir=str(root/'model'))
            self.assertEqual(result, str(root/'model'))
            record = list_model_download_records(root/'records')[0]
            self.assertEqual(record['status'], 'completed')
            self.assertEqual(record['stage'], '파일 완전성 확인 필요')
            self.assertIn('리비전', record['integrity_warning'])
            self.assertIn('공급처 파일 목록을 확인하지 못했습니다', format_model_download_status([record], 'sfx-dasheng-audiogen'))


if __name__ == '__main__':
    unittest.main()
