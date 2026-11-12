"""골반 중심 최종 포즈 배율 검증."""
import unittest
import numpy as np
from generators.kimodo.direct_pose_export import scale_pose_about_pelvis

class PelvisScaleTests(unittest.TestCase):
    def test_preserve_moving_pelvis_and_scale_distances(self):
        current_input_points = np.arange(108,dtype=float).reshape(3,18,2)
        current_input_points[1] += [70,120]
        current_output_points = scale_pose_about_pelvis(current_input_points,85)
        np.testing.assert_allclose(current_output_points[:,[8,11]].mean(1),current_input_points[:,[8,11]].mean(1))
        np.testing.assert_allclose(current_output_points[:,0]-current_output_points[:,10],.85*(current_input_points[:,0]-current_input_points[:,10]))
        np.testing.assert_allclose(scale_pose_about_pelvis(current_input_points,100),current_input_points)
        with self.assertRaises(ValueError):
            scale_pose_about_pelvis(current_input_points,float('nan'))
