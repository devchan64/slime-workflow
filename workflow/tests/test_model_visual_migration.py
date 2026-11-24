from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workflow.common.model_visual_migration import copy_visual_model, copy_published_model
from workflow.domains.image.flux_visual_review import resolve_visual_model
from workflow.domains.trellis_experiment.offline_loader import TRELLIS_ID, TRELLIS_REVISION, resolve_trellis_model


class VisualMigrationTest(unittest.TestCase):
    def test_retained_original_is_used_as_fallback(self):
        from workflow.common.model_visual_retention import retain_visual_original
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / '.model'
            source = root / 'flux-report-vision'
            source.mkdir(parents=True)
            (source / 'config.json').write_text('{}')
            (source / 'model.safetensors').write_bytes(b'weights')
            copy_visual_model(root)
            retain_visual_original(root)
            self.assertFalse(source.exists())
            active = root / 'models/flux-report-vision'
            self.assertEqual(resolve_visual_model(root), active)
            (active / 'model.safetensors').unlink()
            retained = root.parent / '.local/model-catalog/retained/flux-report-vision/original'
            self.assertEqual(resolve_visual_model(root), retained)
            self.assertEqual((retained / 'model.safetensors').read_bytes(), b'weights')

    def test_copy_publishes_matching_files_and_preserves_original(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'flux-report-vision'
            source.mkdir()
            (source / 'config.json').write_text('{}')
            (source / 'model.safetensors').write_bytes(b'weights')
            result = copy_visual_model(root)
            self.assertEqual(result['files'], 2)
            self.assertTrue((source / 'model.safetensors').exists())
            self.assertEqual(resolve_visual_model(root), root / 'models/flux-report-vision')
            with self.assertRaises(FileExistsError):
                copy_visual_model(root)

    def test_link_in_source_is_not_followed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'flux-report-vision'
            source.mkdir()
            (source / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                copy_visual_model(root)
            self.assertFalse((root / 'models/flux-report-vision').exists())

    def test_trellis_copy_switches_only_after_publication(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'trellis-image-large'
            source.mkdir()
            (source / 'pipeline.json').write_text('{}')
            (source / 'verified-manifest.json').write_text('{}')
            self.assertEqual(resolve_trellis_model(root), source)
            copy_published_model(root, 'trellis-image-large', TRELLIS_ID, TRELLIS_REVISION,
                                 ('pipeline.json', 'verified-manifest.json'))
            self.assertEqual(resolve_trellis_model(root), root / 'models/trellis-image-large')
            self.assertTrue((source / 'pipeline.json').exists())

    def test_trellis_retention_requires_identical_files_and_keeps_fallback(self):
        from workflow.common.model_visual_retention import retain_published_original
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / '.model'
            source = root / 'trellis-image-large'
            source.mkdir(parents=True)
            (source / 'pipeline.json').write_text('{}')
            (source / 'verified-manifest.json').write_text('{}')
            copy_published_model(root, 'trellis-image-large', TRELLIS_ID, TRELLIS_REVISION,
                                 ('pipeline.json', 'verified-manifest.json'))
            active = root / 'models/trellis-image-large'
            (active / 'pipeline.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):
                retain_published_original(root, 'trellis-image-large')
            self.assertTrue(source.is_dir())
            (active / 'pipeline.json').write_text('{}')
            retain_published_original(root, 'trellis-image-large')
            self.assertEqual(resolve_trellis_model(root), active)
            (active / '.catalog-migration.json').unlink()
            self.assertEqual(resolve_trellis_model(root), root.parent / '.local/model-catalog/retained/trellis-image-large/original')
