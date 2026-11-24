import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common.model_backup_restore import restore_verified_backup


class LegacyAliasTest(unittest.TestCase):
    def test_flattened_installation_restores_either_prior_backup_layout(self):
        mappings = [
            ('hermes-coding', 'models/hermes-coding', 'hermes-agent'),
            ('qwen3-embedding-0.6b', 'models/qwen3-embedding-0.6b', 'writer-agent'),
            ('translategemma-4b', 'models/translategemma-4b', 'prompt-translation'),
            ('audio/heartmula', 'models/audio/heartmula', 'music/music-heartmula'),
            ('audio/dasheng-audiogen', 'models/audio/dasheng-audiogen', 'music/sfx-dasheng-audiogen'),
            ('flux-report-vision', 'models/flux-report-vision', 'flux-report-vision'),
        ]
        for flat, nested, legacy in mappings:
            for backup_path in (nested, legacy):
                with self.subTest(flat=flat, backup=backup_path), TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    source, backup = root / 'local', root / 'backup'
                    target = source / flat / 'weight'
                    target.parent.mkdir(parents=True)
                    old = backup / backup_path / 'weight'
                    old.parent.mkdir(parents=True)
                    old.write_bytes(b'known')
                    config = root / 'config.json'
                    config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
                    with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                        self.assertTrue(restore_verified_backup(target, hashlib.sha256(b'known').hexdigest()))
                    self.assertEqual(target.read_bytes(), b'known')

    def test_backup_link_cannot_escape_backup_root(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            target = source / 'models/flux-report-vision/weight'
            target.parent.mkdir(parents=True)
            (backup / 'models/flux-report-vision').mkdir(parents=True)
            external = root / 'external'
            external.write_bytes(b'known')
            link = backup / 'models/flux-report-vision/weight'
            link.symlink_to(external)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertFalse(restore_verified_backup(target, hashlib.sha256(b'known').hexdigest()))
                self.assertFalse(target.exists())
                link.unlink()
                inside = backup / 'inside'
                inside.write_bytes(b'known')
                link.symlink_to(inside)
                self.assertTrue(restore_verified_backup(target, hashlib.sha256(b'known').hexdigest()))
            self.assertEqual(target.read_bytes(), b'known')

    def test_git_blob_mismatch_and_unavailable_backup_leave_target_absent(self):
        from types import SimpleNamespace
        from workflow.common.model_huggingface_recovery import recover_huggingface_partial
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            target = source / 'models/flux-report-vision'
            target.mkdir(parents=True)
            legacy = backup / 'flux-report-vision'
            legacy.mkdir(parents=True)
            (legacy / 'config.json').write_bytes(b'wrong')
            config = root / 'backup.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            record = SimpleNamespace(filename='config.json', file_size=5, local_path=str(target / 'config.json'))
            metadata = SimpleNamespace(etag='a' * 40, size=5)
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), \
                    patch('huggingface_hub.get_hf_file_metadata', return_value=metadata):
                self.assertFalse(recover_huggingface_partial('example/model', 'revision', target, record))
                self.assertFalse((target / 'config.json').exists())
                config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(root / 'missing')}))
                self.assertFalse(recover_huggingface_partial('example/model', 'revision', target, record))
                self.assertFalse((target / 'config.json').exists())
            self.assertEqual((legacy / 'config.json').read_bytes(), b'wrong')

    def test_huggingface_git_blob_can_restore_small_file_from_backup(self):
        from types import SimpleNamespace
        from huggingface_hub._local_folder import read_download_metadata
        from workflow.common.model_huggingface_recovery import recover_huggingface_partial
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            target = source / 'models/flux-report-vision'
            target.mkdir(parents=True)
            legacy = backup / 'flux-report-vision'
            legacy.mkdir(parents=True)
            content = b'{"model_type":"example"}'
            (legacy / 'config.json').write_bytes(content)
            digest = hashlib.sha1(f'blob {len(content)}\0'.encode() + content, usedforsecurity=False).hexdigest()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            record = SimpleNamespace(filename='config.json', file_size=len(content), local_path=str(target / 'config.json'))
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), \
                    patch('huggingface_hub.get_hf_file_metadata', return_value=SimpleNamespace(etag=digest, size=len(content))), \
                    patch('workflow.common.model_huggingface_recovery.download_verified_http') as download:
                self.assertTrue(recover_huggingface_partial('example/model', 'revision', target, record))
            download.assert_not_called()
            self.assertEqual((target / 'config.json').read_bytes(), content)
            self.assertEqual(read_download_metadata(target, 'config.json').etag, digest)

    def test_git_blob_partial_is_preserved_for_normal_download(self):
        from types import SimpleNamespace
        from workflow.common.model_huggingface_recovery import recover_huggingface_partial
        with TemporaryDirectory() as temporary:
            target = Path(temporary)
            partial = target / 'config.json.partial'
            partial.write_bytes(b'partial')
            record = SimpleNamespace(filename='config.json', file_size=20, local_path=str(target / 'config.json'))
            with patch('huggingface_hub.get_hf_file_metadata', return_value=SimpleNamespace(etag='a' * 40, size=20)):
                self.assertFalse(recover_huggingface_partial('example/model', 'revision', target, record))
            self.assertEqual(partial.read_bytes(), b'partial')

    def test_planned_hermes_and_cache_paths_can_restore_legacy_files(self):
        for new, old in [('models/hermes-coding', 'hermes-agent'), ('cache/huggingface', 'huggingface'),
                         ('models/audio/heartmula', 'music/music-heartmula'),
                         ('models/audio/dasheng-audiogen', 'music/sfx-dasheng-audiogen')]:
            with self.subTest(new=new), TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, backup = root / 'local', root / 'backup'
                target = source / new / 'weights'
                target.parent.mkdir(parents=True)
                (backup / old).mkdir(parents=True)
                (backup / old / 'weights').write_bytes(b'known')
                config = root / 'config.json'
                config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
                with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                    self.assertTrue(restore_verified_backup(target, hashlib.sha256(b'known').hexdigest()))
                self.assertEqual(target.read_bytes(), b'known')

    def test_huggingface_recovery_uses_legacy_backup_for_relocated_installation(self):
        from types import SimpleNamespace
        from huggingface_hub._local_folder import read_download_metadata
        from workflow.common.model_huggingface_recovery import recover_huggingface_partial
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            target_root = source / 'models/flux-report-vision'
            target_root.mkdir(parents=True)
            legacy = backup / 'flux-report-vision'
            legacy.mkdir(parents=True)
            content = b'known model weights'
            (legacy / 'weights.bin').write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            file_record = SimpleNamespace(filename='weights.bin', file_size=len(content), local_path=str(target_root / 'weights.bin'))
            metadata = SimpleNamespace(etag=digest, size=len(content))
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), \
                    patch('huggingface_hub.get_hf_file_metadata', return_value=metadata), \
                    patch('workflow.common.model_huggingface_recovery.download_verified_http') as download:
                self.assertTrue(recover_huggingface_partial('example/model', 'fixed-revision', target_root, file_record))
            download.assert_not_called()
            self.assertEqual((target_root / 'weights.bin').read_bytes(), content)
            stored_metadata = read_download_metadata(target_root, 'weights.bin')
            self.assertEqual((stored_metadata.commit_hash, stored_metadata.etag), ('fixed-revision', digest))

    def test_huggingface_recovery_preserves_existing_and_rejects_bad_backup(self):
        from types import SimpleNamespace
        from workflow.common.model_huggingface_recovery import recover_huggingface_partial
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            target_root = source / 'models/flux-report-vision'
            target_root.mkdir(parents=True)
            legacy = backup / 'flux-report-vision'
            legacy.mkdir(parents=True)
            (legacy / 'weights.bin').write_bytes(b'not the expected weights')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            expected = b'different valid content'
            record = SimpleNamespace(filename='weights.bin', file_size=len(expected), local_path=str(target_root / 'weights.bin'))
            metadata = SimpleNamespace(etag=hashlib.sha256(expected).hexdigest(), size=len(expected))
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), patch('huggingface_hub.get_hf_file_metadata', return_value=metadata):
                self.assertFalse(recover_huggingface_partial('example/model', 'revision', target_root, record))
                self.assertFalse((target_root / 'weights.bin').exists())
                (target_root / 'weights.bin').write_bytes(b'existing user file')
                self.assertFalse(recover_huggingface_partial('example/model', 'revision', target_root, record))
                self.assertEqual((target_root / 'weights.bin').read_bytes(), b'existing user file')

    def test_old_backup_restores_new_location_only_when_hash_matches(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / 'models'
            backup = base / 'backup'
            target = source / 'models/flux-report-vision/model.bin'
            target.parent.mkdir(parents=True)
            (backup / 'flux-report-vision').mkdir(parents=True)
            (backup / 'flux-report-vision/model.bin').write_bytes(b'original')
            config = base / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertFalse(restore_verified_backup(target, '0' * 64))
                self.assertFalse(target.exists())
                self.assertTrue(restore_verified_backup(target, hashlib.sha256(b'original').hexdigest()))
                self.assertEqual(target.read_bytes(), b'original')
                self.assertFalse(restore_verified_backup(target, hashlib.sha256(b'original').hexdigest()))
