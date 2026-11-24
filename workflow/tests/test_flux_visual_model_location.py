import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workflow.domains.image.flux_visual_review import MODEL_ID, REVISION, resolve_visual_model


class VisualModelLocationTest(unittest.TestCase):
    def test_migration_requires_published_marker_and_model_files(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            new = root / 'models' / 'flux-report-vision'
            new.mkdir(parents=True)
            old = root / 'flux-report-vision'
            (new / 'config.json').write_text('{}')
            (new / 'model.safetensors').write_bytes(b'model')
            self.assertEqual(resolve_visual_model(root), old)
            marker = new / '.catalog-migration.json'
            marker.write_text(json.dumps({'schema_version': 1, 'model_id': MODEL_ID,
                                          'revision': REVISION, 'state': 'verified'}))
            self.assertEqual(resolve_visual_model(root), new)
            (new / 'model.safetensors').unlink()
            self.assertEqual(resolve_visual_model(root), old)

    def test_symlinked_storage_is_not_published(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            elsewhere = root / 'elsewhere'
            elsewhere.mkdir()
            (root / 'models').symlink_to(elsewhere, target_is_directory=True)
            self.assertEqual(resolve_visual_model(root), root / 'flux-report-vision')
