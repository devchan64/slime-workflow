import json
from pathlib import Path
import tempfile
import unittest

from workflow.common.model_restore_history import read_restore_record, write_restore_record


class RestoreHistoryTests(unittest.TestCase):
    def test_records_only_completed_snapshot_observation_without_local_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            result = {'model': 'example', 'snapshot_id': 'a' * 32, 'files': 2, 'bytes': 10,
                      'verification': 'snapshot_manifest_sha256', 'timestamp_mismatches': [],
                      'partial_files': ['cache/file.partial'], 'path': '/private/temporary'}
            written = write_restore_record(result, directory=directory)
            self.assertEqual(read_restore_record('example', directory=directory), written)
            self.assertEqual(written['partial_files'], 1)
            self.assertNotIn('path', written)
            self.assertNotIn('cache/file.partial', json.dumps(written))
            with self.assertRaises(ValueError):
                write_restore_record({**result, 'model': '../outside'}, directory=directory)
            with self.assertRaises(ValueError):
                write_restore_record({**result, 'verification': 'unverified'}, directory=directory)

    def test_rejects_corrupt_record_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example.json'
            path.write_text('{bad')
            self.assertIsNone(read_restore_record('example', directory=directory))
            path.unlink()
            path.symlink_to('/etc/passwd')
            self.assertIsNone(read_restore_record('example', directory=directory))
