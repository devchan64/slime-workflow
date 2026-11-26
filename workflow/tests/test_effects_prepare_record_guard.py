from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from generators.sound_effects.prepare_record_guard import guarded_refresh


class PrepareRecordGuardTests(unittest.TestCase):
    def test_failure_restores_existing_record_without_masking_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = root/'prepared.json'
            record.write_text('{"previous":true}')
            def fail():
                record.unlink()
                raise RuntimeError('prepare failed')
            with self.assertRaisesRegex(RuntimeError, 'prepare failed'):
                guarded_refresh(root, fail)
            self.assertEqual(record.read_text(), '{"previous":true}')
            self.assertFalse(list(root.glob('.prepared-backup-*')))

    def test_failure_does_not_replace_new_record(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = root/'prepared.json'
            record.write_text('old')
            def fail():
                record.unlink()
                record.write_text('new')
                raise RuntimeError('prepare failed')
            with self.assertRaises(RuntimeError):
                guarded_refresh(root, fail)
            self.assertEqual(record.read_text(), 'new')

    def test_success_keeps_new_record_and_no_prior_record_stays_absent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = root/'prepared.json'
            record.write_text('old')
            def success():
                record.write_text('new')
                return 'ok'
            self.assertEqual(guarded_refresh(root, success), 'ok')
            self.assertEqual(record.read_text(), 'new')
            record.unlink()
            def fail():
                raise RuntimeError('no record')
            with self.assertRaises(RuntimeError):
                guarded_refresh(root, fail)
            self.assertFalse(record.exists())

    def test_symlink_record_is_rejected_before_refresh(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'prepared.json').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                guarded_refresh(root, lambda: self.fail('must not run'))

    def test_symlink_parent_is_rejected_before_creating_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'actual'
            target.mkdir()
            (root/'link').symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                guarded_refresh(root/'link'/'model', lambda: self.fail('must not run'))
            self.assertFalse((target/'model').exists())

    def test_failed_restore_keeps_temporary_copy(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record = root/'prepared.json'
            record.write_text('old')
            def fail():
                record.unlink()
                raise RuntimeError('prepare failed')
            with patch('generators.sound_effects.prepare_record_guard.os.link', side_effect=OSError('restore failed')):
                with self.assertRaises(RuntimeError) as caught:
                    guarded_refresh(root, fail)
            self.assertTrue(any('자동 복원 실패' in note for note in caught.exception.__notes__))
            copies = list(root.glob('.prepared-backup-*'))
            self.assertEqual([path.read_text() for path in copies], ['old'])
            self.assertTrue(any(str(copies[0]) in note for note in caught.exception.__notes__))
