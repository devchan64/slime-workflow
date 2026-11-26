import json
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow.common.model_backup_sync import sync_snapshot
from workflow.common.model_snapshot_offline_restore import restore_snapshot_offline, list_snapshot_versions, _open_snapshot_file


class OfflineSnapshotRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'model-root'
        self.backup = self.root/'backup'
        self.model = self.source/'example'
        self.model.mkdir(parents=True)
        self.backup.mkdir()
        (self.model/'sub').mkdir()
        (self.model/'sub/config.json').write_bytes(b'{"format":"example"}')
        (self.model/'weights.bin').write_bytes(b'model weights')
        os.utime(self.model/'weights.bin', ns=(1700000000123456789, 1700000000123456789))
        self.roots = (self.source, self.backup, None)
        sync_snapshot('example', 'a'*32, roots=self.roots)
        self.model.rename(self.source/'original-saved')

    def test_restores_all_files_without_provider_access(self):
        with patch('socket.create_connection', side_effect=AssertionError('provider access')):
            result = restore_snapshot_offline('example', roots=self.roots)
        self.assertEqual(result['files'], 2)
        self.assertEqual((self.model/'sub/config.json').read_bytes(), b'{"format":"example"}')
        self.assertEqual((self.model/'weights.bin').read_bytes(), b'model weights')
        self.assertEqual((self.model/'weights.bin').stat().st_mtime_ns, 1700000000123456789)
        self.assertEqual(result['verification'], 'snapshot_manifest_sha256')
        self.assertEqual(result['timestamp_mismatches'], [])
        self.assertEqual(result['partial_files'], [])

    def test_reports_partial_downloads_without_treating_them_as_complete_models(self):
        self.model.mkdir()
        (self.model/'download.incomplete').write_bytes(b'partial download')
        sync_snapshot('example', 'b'*32, roots=self.roots)
        self.model.rename(self.source/'partial-saved')
        versions = list_snapshot_versions('example', roots=self.roots)
        self.assertEqual(next(version for version in versions if version['snapshot_id'] == 'b'*32)['partial_file_count'], 1)
        result = restore_snapshot_offline('example', snapshot_id='b'*32, roots=self.roots)
        self.assertEqual(result['partial_files'], ['download.incomplete'])
        self.assertIn('모델 준비 상태를 별도로 확인', result['note'])
        self.assertEqual((self.model/'download.incomplete').read_bytes(), b'partial download')

    def test_restores_explicit_older_snapshot(self):
        self.model.mkdir()
        (self.model/'weights.bin').write_bytes(b'newer weights')
        sync_snapshot('example', 'b'*32, roots=self.roots)
        self.model.rename(self.source/'newer-saved')
        result = restore_snapshot_offline('example', snapshot_id='a'*32, roots=self.roots)
        self.assertEqual(result['snapshot_id'], 'a'*32)
        self.assertEqual((self.model/'weights.bin').read_bytes(), b'model weights')

    def test_list_snapshots_excludes_pending_and_flags_invalid_manifest(self):
        parent = self.backup/'.model-backup-snapshots/example'
        (parent/('.pending-'+'c'*32)).mkdir()
        broken = parent/('b'*32)
        broken.mkdir()
        (broken/'.snapshot.json').write_text('{bad json')
        versions = list_snapshot_versions('example', roots=self.roots)
        self.assertEqual([(item['snapshot_id'], item['state']) for item in versions],
                         [('a'*32, 'declared'), ('b'*32, 'unavailable')])
        self.assertEqual(versions[0]['file_count'], 2)

    def test_rejects_pending_or_invalid_snapshot_id(self):
        for snapshot_id in ('../escape', '.pending-' + 'a'*32, 'A'*32, 'c'*32):
            with self.subTest(snapshot_id=snapshot_id), self.assertRaises(ValueError):
                restore_snapshot_offline('example', snapshot_id=snapshot_id, roots=self.roots)
        self.assertFalse(self.model.exists())

    def test_corruption_does_not_publish_partial_model(self):
        (self.backup/'.model-backup-snapshots/example'/('a'*32)/'weights.bin').write_bytes(b'x'*len(b'model weights'))
        with self.assertRaisesRegex(ValueError, '불일치'):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertFalse(self.model.exists())
        self.assertFalse(any(p.name.startswith('.snapshot-restore-') for p in self.source.iterdir()))

    def test_existing_directory_is_never_replaced(self):
        self.model.mkdir()
        (self.model/'keep').write_text('keep')
        with self.assertRaises(FileExistsError):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertEqual((self.model/'keep').read_text(), 'keep')

    def test_rejects_manifest_path_traversal(self):
        manifest = self.backup/'.model-backup-snapshots/example'/('a'*32)/'.snapshot.json'
        record = json.loads(manifest.read_text())
        record['files'][0]['path'] = '../escape'
        manifest.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertFalse(self.model.exists())
        self.assertFalse((self.root/'escape').exists())

    def test_rejects_unknown_or_missing_manifest_version_without_publishing(self):
        manifest = self.backup/'.model-backup-snapshots/example'/('a'*32)/'.snapshot.json'
        original = json.loads(manifest.read_text())
        for version in (None, 2, True, '1'):
            with self.subTest(version=version):
                record = dict(original)
                if version is None:
                    record.pop('version')
                else:
                    record['version'] = version
                manifest.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    restore_snapshot_offline('example', snapshot_id='a'*32, roots=self.roots)
                self.assertFalse(self.model.exists())

    def test_rejects_snapshot_symlink(self):
        weights = self.backup/'.model-backup-snapshots/example'/('a'*32)/'weights.bin'
        weights.unlink()
        weights.symlink_to(self.source/'original-saved/weights.bin')
        with self.assertRaises(ValueError):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertFalse(self.model.exists())

    def test_open_rejects_symlink_at_each_snapshot_component(self):
        snapshot = self.backup/'.model-backup-snapshots/example'/('a'*32)
        (snapshot/'link-to-dir').symlink_to(snapshot/'sub', target_is_directory=True)
        (snapshot/'link-to-file').symlink_to(snapshot/'weights.bin')
        for name in ('link-to-dir/config.json', 'link-to-file'):
            with self.subTest(name=name), self.assertRaises(OSError):
                _open_snapshot_file(snapshot, name)

    def test_rejects_wrong_snapshot_identity(self):
        manifest = self.backup/'.model-backup-snapshots/example'/('a'*32)/'.snapshot.json'
        record = json.loads(manifest.read_text())
        record['model'] = 'different-model'
        manifest.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertFalse(self.model.exists())

    def test_rejects_unlisted_snapshot_files(self):
        snapshot = self.backup/'.model-backup-snapshots/example'/('a'*32)
        (snapshot/'extra.bin').write_bytes(b'unlisted')
        with self.assertRaisesRegex(ValueError, '파일 목록'):
            restore_snapshot_offline('example', roots=self.roots)
        self.assertFalse(self.model.exists())

    def test_restored_qwen_ready_record_retains_file_timestamp(self):
        from workflow.common import hermes_model_download as hermes
        model = self.source/'qwen3.8-27b-iq4-xs'
        model.mkdir()
        weights = model/hermes.HERMES_MODEL_FILENAME
        weights.write_bytes(b'small qwen fixture')
        os.utime(weights, ns=(1700000000123456789, 1700000000123456789))
        digest = hashlib.sha256(weights.read_bytes()).hexdigest()
        (model/'ready.sha256').write_text(json.dumps({'sha256': digest, 'size': weights.stat().st_size,
                                                       'mtime_ns': weights.stat().st_mtime_ns}))
        sync_snapshot('catalog-hermes-coding', 'b'*32, roots=self.roots)
        model.rename(self.source/'qwen-saved')
        restore_snapshot_offline('catalog-hermes-coding', roots=self.roots)
        with patch.object(hermes, 'current_hermes_model_directory', return_value=model), \
             patch.object(hermes, 'HERMES_MODEL_SHA256', digest):
            self.assertTrue(hermes.inspect_hermes_model_files())
            hermes.verify_hermes_model_integrity()

    def test_restores_flattened_catalog_target_after_model_is_deleted(self):
        current = self.source/'translategemma-4b'
        current.mkdir()
        (current/'config.json').write_text('{"model_type":"test"}')
        sync_snapshot('catalog-translation-model', 'd'*32, roots=self.roots)
        current.rename(self.source/'translation-saved')
        self.assertFalse((self.source/'models').exists())
        result = restore_snapshot_offline('catalog-translation-model', roots=self.roots)
        self.assertEqual(Path(result['path']), current)
        self.assertEqual((current/'config.json').read_text(), '{"model_type":"test"}')
        self.assertFalse((self.source/'models').exists())
