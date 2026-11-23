import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generators.wan21_video_assets import inspect_files, prepare_files
from generators.wan21_t2v import assets as t2v
from generators.wan21_i2v import assets as i2v
from generators.wan21_i2v import attack_lora
from workflow.common.model_prepare_worker import MODEL_PREPARATION_PROFILES


class Wan21AssetsTest(unittest.TestCase):
    def test_generators_have_separate_pinned_models_and_profiles(self):
        self.assertNotEqual(t2v.DIRECTORY, i2v.DIRECTORY)
        for profile, module in [('wan21-t2v-assets', t2v), ('wan21-i2v-assets', i2v), ('wan21-i2v-attack-lora', attack_lora)]:
            self.assertIn(profile, MODEL_PREPARATION_PROFILES)
            for relative, repo, revision, remote, size, digest in module.FILES:
                self.assertFalse(Path(relative).is_absolute())
                self.assertNotIn('..', Path(relative).parts)
                self.assertEqual(len(revision), 40)
                self.assertEqual(len(digest), 64)
                self.assertGreater(size, 0)
                self.assertTrue(repo and remote)

    def test_inspection_rejects_corruption_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b'model'
            entry = ('model', 'repo/name', 'a'*40, 'model', len(data), hashlib.sha256(data).hexdigest())
            path = root / 'model'
            self.assertFalse(inspect_files(root, [entry]))
            path.write_bytes(data)
            self.assertTrue(inspect_files(root, [entry]))
            path.write_bytes(b'other')
            self.assertFalse(inspect_files(root, [entry]))
            path.unlink()
            target = root / 'target'
            target.write_bytes(data)
            path.symlink_to(target)
            self.assertFalse(inspect_files(root, [entry]))

    def test_kxsr_file_is_checked_against_known_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'kxsr.safetensors'
            path.write_bytes(b'fixture')
            self.assertFalse(t2v.inspect_boss_lora(path))
            with patch.object(t2v,'BOSS_SHA256',hashlib.sha256(b'fixture').hexdigest()):
                self.assertTrue(t2v.inspect_boss_lora(path))
                path.unlink()
                target=Path(directory)/'target';target.write_bytes(b'fixture');path.symlink_to(target)
                self.assertFalse(t2v.inspect_boss_lora(path))

    def test_prepare_uses_pinned_url_and_rechecks_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b'model'
            digest = hashlib.sha256(data).hexdigest()
            entry = ('base/model', 'repo/name', 'a'*40, 'remote/model', len(data), digest)
            def download(url, path, expected_digest, label, expected_total_bytes):
                self.assertEqual(url, 'https://huggingface.co/repo/name/resolve/' + 'a'*40 + '/remote/model')
                self.assertEqual((expected_digest, label, expected_total_bytes), (digest, 'profile/base/model', len(data)))
                path.parent.mkdir(parents=True)
                path.write_bytes(data)
            with patch('workflow.common.model_http_download.download_verified_http', side_effect=download):
                prepare_files(root, [entry], 'profile')
            self.assertTrue(inspect_files(root, [entry]))


if __name__ == '__main__': unittest.main()
