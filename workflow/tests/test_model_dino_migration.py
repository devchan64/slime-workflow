import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workflow.common.model_dino_migration import copy_dino_model
from workflow.domains.trellis_experiment.offline_loader import DINO_FILENAME, resolve_dino_weights


class DinoMigrationTest(unittest.TestCase):
    def test_retained_original_is_fallback_without_replacing_existing_data(self):
        from workflow.common.model_dino_retention import retain_dino_original
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / '.model'
            source = root / 'trellis-dinov2' / DINO_FILENAME
            active = root / 'models/trellis-dinov2' / DINO_FILENAME
            source.parent.mkdir(parents=True)
            active.parent.mkdir(parents=True)
            source.write_bytes(b'weights')
            active.write_bytes(b'weights')
            digest = hashlib.sha256(b'weights').hexdigest()
            retain_dino_original(root, digest)
            self.assertFalse(source.exists())
            self.assertEqual(resolve_dino_weights(root), active)
            active.unlink()
            retained = root.parent / '.local/model-catalog/retained/trellis-dinov2/original' / DINO_FILENAME
            self.assertEqual(resolve_dino_weights(root), retained)
            self.assertEqual(retained.read_bytes(), b'weights')
            with self.assertRaises(ValueError):
                retain_dino_original(root, digest)

    def test_verified_copy_is_selected_and_original_is_preserved(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'trellis-dinov2' / DINO_FILENAME
            source.parent.mkdir()
            source.write_bytes(b'weights')
            digest = hashlib.sha256(b'weights').hexdigest()
            self.assertEqual(resolve_dino_weights(root), source)
            with self.assertRaises(ValueError):
                copy_dino_model(root, '0' * 64)
            self.assertEqual(resolve_dino_weights(root), source)
            copy_dino_model(root, digest)
            target = root / 'models/trellis-dinov2' / DINO_FILENAME
            self.assertEqual(resolve_dino_weights(root), target)
            self.assertEqual(source.read_bytes(), target.read_bytes())
            with self.assertRaises(FileExistsError):
                copy_dino_model(root, digest)
