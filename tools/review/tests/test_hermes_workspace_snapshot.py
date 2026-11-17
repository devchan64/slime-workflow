from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.review.domains.hermes_agent import workspace_snapshot as snapshot_module_value


class WorkspaceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary_root_path = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temporary_root_path)
        self.source_repository_path = self.temporary_root_path / 'source'
        self.source_repository_path.mkdir()
        self.snapshot_repository_path = self.temporary_root_path / 'sandbox'
        subprocess.run(['git', 'init', '-q', str(self.source_repository_path)], check=True)
        subprocess.run(['git', '-C', str(self.source_repository_path), 'config', 'user.email', 'test@localhost'], check=True)
        subprocess.run(['git', '-C', str(self.source_repository_path), 'config', 'user.name', 'Test'], check=True)
        (self.source_repository_path / 'tracked.txt').write_text('base\n')
        (self.source_repository_path / 'deleted.txt').write_text('remove\n')
        subprocess.run(['git', '-C', str(self.source_repository_path), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.source_repository_path), 'commit', '-qm', 'initial'], check=True)

    def test_snapshot_preserves_working_changes_and_independent_diff(self):
        (self.source_repository_path / 'tracked.txt').write_text('user change\n')
        (self.source_repository_path / 'deleted.txt').unlink()
        (self.source_repository_path / 'new.txt').write_text('new user file\n')
        snapshot_baseline_record = snapshot_module_value.copy_snapshot_source_files(self.source_repository_path, self.snapshot_repository_path)
        self.assertEqual(snapshot_baseline_record['file_count'], 2)
        self.assertEqual(snapshot_baseline_record['deleted_file_count'], 1)
        self.assertEqual((self.snapshot_repository_path / 'tracked.txt').read_text(), 'user change\n')
        self.assertEqual((self.snapshot_repository_path / 'new.txt').read_text(), 'new user file\n')
        self.assertFalse((self.snapshot_repository_path / 'deleted.txt').exists())
        (self.snapshot_repository_path / 'tracked.txt').write_text('agent change\n')
        (self.snapshot_repository_path / 'agent.txt').write_text('agent new\n')
        snapshot_change_bytes = snapshot_module_value.collect_snapshot_change_diff(self.snapshot_repository_path, snapshot_baseline_record['baseline_commit'])
        self.assertIn(b'-user change', snapshot_change_bytes)
        self.assertIn(b'+agent change', snapshot_change_bytes)
        self.assertIn(b'agent.txt', snapshot_change_bytes)
        self.assertEqual((self.source_repository_path / 'tracked.txt').read_text(), 'user change\n')

    def test_snapshot_rejects_symbolic_link(self):
        (self.source_repository_path / 'link.txt').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, '심볼릭 링크'):
            snapshot_module_value.copy_snapshot_source_files(self.source_repository_path, self.snapshot_repository_path)

    def test_snapshot_rejects_a_previously_copied_file_changed_later(self):
        snapshot_original_copy = snapshot_module_value.shutil.copy2
        def copy_and_modify_source(source_current_path, snapshot_current_path, **copy_keyword_values):
            if Path(source_current_path).name == 'tracked.txt':
                (self.source_repository_path / 'deleted.txt').write_text('changed after copy')
            return snapshot_original_copy(source_current_path, snapshot_current_path, **copy_keyword_values)
        with patch.object(snapshot_module_value.shutil, 'copy2', side_effect=copy_and_modify_source):
            with self.assertRaisesRegex(ValueError, '원본이 변경'):
                snapshot_module_value.copy_snapshot_source_files(self.source_repository_path, self.snapshot_repository_path)


if __name__ == '__main__':
    unittest.main()
