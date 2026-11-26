import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generators.wan_vace.prepare import prepare_shared_vae


class VaceVaeBackupTests(unittest.TestCase):
    def test_vae_path_follows_move_and_rejects_conflict(self):
        from generators.wan_vace.contracts import vace_model_path, vace_model_records
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root/'.model/wan22-animate-components/split_files/vae'
            old.mkdir(parents=True)
            name = 'wan_2.1_vae.safetensors'
            self.assertEqual(vace_model_path('vae', root=root), old/name)
            new = root/'.model/wan-2.1-vae'
            old.rename(new)
            self.assertEqual(vace_model_path('vae', root=root), new/name)
            self.assertEqual(vace_model_records(root=root)['vae'][0], '.model/wan-2.1-vae/'+name)
            old.mkdir()
            with self.assertRaises(ValueError):
                vace_model_path('vae', root=root)

    def test_backup_precedes_hub_and_verifies_pinned_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'new'/'vae.safetensors'
            data = b'known vae data'
            digest = hashlib.sha256(data).hexdigest()
            def restore(path, expected, size):
                self.assertEqual((expected, size), (digest, len(data)))
                path.write_bytes(data)
                return True
            with patch('workflow.common.model_backup_restore.restore_verified_backup', side_effect=restore), \
                 patch('workflow.common.model_http_download.download_verified_http', side_effect=AssertionError('Hub contacted')):
                prepare_shared_vae(target, len(data), digest, 'repo', 'revision', 'vae')
            self.assertEqual(target.read_bytes(), data)

    def test_backup_miss_falls_back_and_checks_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'new'/'vae.safetensors'
            with patch('workflow.common.model_backup_restore.restore_verified_backup', return_value=False), \
                 patch('workflow.common.model_http_download.download_verified_http', side_effect=lambda *args, **kw: target.write_bytes(b'bad')) as hub:
                with self.assertRaisesRegex(ValueError, '불일치'):
                    prepare_shared_vae(target, 3, hashlib.sha256(b'good').hexdigest(), 'repo', 'revision', 'vae')
                hub.assert_called_once()
