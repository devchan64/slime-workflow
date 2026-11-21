"""변형 본 외 보조 그룹이 리깅 가중치 검사를 오염하지 않는지 검증한다."""
import unittest
from types import SimpleNamespace as Record
from generators.momask.skin_surface import inspect_skin_rig


class SkinRigInspectionTests(unittest.TestCase):
    def inspect_weights(self, vertex_groups):
        rig = Record(data=Record(bones=[Record(name='joint', use_deform=True, parent=None),
                                       Record(name='helper', use_deform=False, parent=None)]))
        body = Record(vertex_groups=[Record(index=0, name='joint'), Record(index=1, name='helper')],
                      data=Record(vertices=[Record(groups=[Record(group=index, weight=weight)
                                                          for index, weight in values])
                                            for values in vertex_groups]))
        return inspect_skin_rig(body, rig)

    def test_non_deforming_group_does_not_change_normalization(self):
        result = self.inspect_weights([[(0, 1.0), (1, 0.8)]])
        self.assertEqual(result['non_normalized_vertices'], 0)
        self.assertEqual(result['weight_max'], 1.0)

    def test_helper_weights_cannot_mask_missing_skin_weights(self):
        result = self.inspect_weights([[(1, 1.0)], [(0, 0.5)]])
        self.assertEqual(result['unweighted_vertices'], 1)
        self.assertEqual(result['non_normalized_vertices'], 2)
        self.assertTrue(result['quality_warnings'])

    def test_invalid_weights_fail(self):
        with self.assertRaises(ValueError):
            self.inspect_weights([[(0, float('nan'))]])
        with self.assertRaises(ValueError):
            self.inspect_weights([])
