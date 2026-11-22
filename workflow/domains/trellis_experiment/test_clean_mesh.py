import tempfile
import unittest
from pathlib import Path

import trimesh

from clean_mesh import clean


class CleaningTest(unittest.TestCase):
    def test_removes_distant_tiny_piece_and_rejects_strict_extent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = trimesh.creation.icosphere(subdivisions=2, radius=1)
            fragment = trimesh.creation.icosphere(subdivisions=1, radius=0.01)
            fragment.apply_translation([2, 0, 0])
            source = root / 'input.ply'
            trimesh.util.concatenate([body, fragment]).export(source)
            original = source.read_bytes()
            result = clean(source, root / 'result', max_component_faces=0.3, max_extent_change=0.01)
            self.assertEqual(result['removed_components'], 1)
            self.assertEqual(result['status'], 'failed')
            self.assertFalse(result['checks']['extent'])
            self.assertTrue(result['checks']['roundtrip'])
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                clean(source, root / 'result')

    def test_preserves_large_or_nearby_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = trimesh.creation.icosphere(subdivisions=2)
            large = trimesh.creation.icosphere(subdivisions=1, radius=0.3)
            large.apply_translation([3, 0, 0])
            near = trimesh.creation.icosphere(subdivisions=1, radius=0.01)
            near.apply_translation([1.011, 0, 0])
            source = root / 'input.ply'
            trimesh.util.concatenate([body, large, near]).export(source)
            result = clean(source, root / 'result', max_component_faces=0.3, min_distance=0.01)
            self.assertEqual(result['removed_components'], 0)
            self.assertEqual(result['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
