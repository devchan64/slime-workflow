"""고정 화면 중심 최종 포즈 배율 검증."""
import unittest
import numpy as np
from generators.kimodo.direct_pose_export import scale_pose_about_camera

class PelvisScaleTests(unittest.TestCase):
    def test_preserve_moving_pelvis_and_scale_distances(self):
        current_input_points = np.arange(108,dtype=float).reshape(3,18,2)
        current_input_points[1] += [70,120]
        current_output_points = scale_pose_about_camera(current_input_points,85)
        np.testing.assert_allclose(current_output_points[:,[8,11]].mean(1),[416,240]+.85*(current_input_points[:,[8,11]].mean(1)-[416,240]))
        np.testing.assert_allclose(current_output_points[:,0]-current_output_points[:,10],.85*(current_input_points[:,0]-current_input_points[:,10]))
        np.testing.assert_allclose(scale_pose_about_camera(current_input_points,100),current_input_points)
        with self.assertRaises(ValueError):
            scale_pose_about_camera(current_input_points,float('nan'))

    def test_increase_all_margins_without_moving_pelvis(self):
        current_input_points = np.full((1,18,2),[416.,240.])
        current_input_points[0,0] = [416,50]
        current_input_points[0,4] = [200,240]
        current_input_points[0,7] = [620,240]
        current_input_points[0,10] = [400,430]
        current_input_points[0,8] = [390,240]
        current_input_points[0,11] = [442,240]
        current_output_points = scale_pose_about_camera(current_input_points,85)
        np.testing.assert_allclose(current_output_points[:,[8,11]].mean(1),[[416,240]])
        self.assertGreater(current_output_points[:,:,0].min(),current_input_points[:,:,0].min())
        self.assertLess(current_output_points[:,:,0].max(),current_input_points[:,:,0].max())
        self.assertGreater(current_output_points[:,:,1].min(),current_input_points[:,:,1].min())
        self.assertLess(current_output_points[:,:,1].max(),current_input_points[:,:,1].max())
