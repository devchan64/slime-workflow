import unittest
import numpy as np
import trimesh
from inspect_repair_mesh import inspect


class IntersectionTest(unittest.TestCase):
    def test_crossing_and_separate_triangles(self):
        vertices = np.array([[-1, 0, 0], [1, 0, 0], [0, 1, 0],
                             [0, .3, -1], [0, .3, 1], [0, -.5, 0]], dtype=float)
        faces = np.array([[0, 1, 2], [3, 4, 5]])
        self.assertEqual(inspect(trimesh.Trimesh(vertices=vertices, faces=faces, process=False)), 2)
        vertices[3:, 2] += 3
        self.assertEqual(inspect(trimesh.Trimesh(vertices=vertices, faces=faces, process=False)), 0)


if __name__ == '__main__':
    unittest.main()
