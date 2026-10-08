"""기준 자세 정렬과 원본 축 회전 보존의 계산 계약을 검증한다."""
import math
import unittest
import numpy as np
from generators.hy_motion.segment_rotation_transfer import transfer_segment_rotation, measure_segment_twist


class SegmentRotationTransferTests(unittest.TestCase):
    def test_identity_preserves_bind_rotation(self):
        current_bind_rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        np.testing.assert_allclose(transfer_segment_rotation(np.eye(3), [0, 1, 0], [0, 1, 0], current_bind_rotation), current_bind_rotation)

    def test_rest_alignment_maps_segment_direction(self):
        current_result_rotation = transfer_segment_rotation(np.eye(3), [1, 0, 0], [0, 1, 0], np.eye(3))
        np.testing.assert_allclose(current_result_rotation @ [0, 1, 0], [1, 0, 0], atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(current_result_rotation), 1)

    def test_source_axial_rotation_is_preserved(self):
        for current_twist_angle in (-math.pi, -.7, 0, .7, math.pi):
            current_source_rotation = np.array([[math.cos(current_twist_angle), -math.sin(current_twist_angle), 0], [math.sin(current_twist_angle), math.cos(current_twist_angle), 0], [0, 0, 1]])
            current_result_rotation = transfer_segment_rotation(current_source_rotation, [0, 0, 1], [0, 0, 1], np.eye(3))
            self.assertAlmostEqual(measure_segment_twist(np.eye(3), current_result_rotation, [0, 0, 1]), current_twist_angle)

    def test_non_axial_delta_is_rejected(self):
        with self.assertRaises(ValueError):
            measure_segment_twist(np.eye(3), np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]), [1, 0, 0])

    def test_invalid_reference_axes_are_rejected(self):
        for current_source_axis in ([0, 0, 0], [0, -1, 0], [np.nan, 0, 0], [1, 0]):
            with self.assertRaises(ValueError):
                transfer_segment_rotation(np.eye(3), current_source_axis, [0, 1, 0], np.eye(3))

    def test_reflection_is_rejected(self):
        with self.assertRaises(ValueError):
            transfer_segment_rotation(np.diag([-1, 1, 1]), [1, 0, 0], [1, 0, 0], np.eye(3))
