"""메시 카메라와 직접 투영의 좌표 계약 검증."""
import unittest
import numpy as np
from generators.kimodo.soma_pose import project_recorded_camera_points


class SomaCameraProjectionTests(unittest.TestCase):
    def test_center_and_image_edges(self):
        current_camera_record = {'rotation_matrix':np.eye(3).tolist(),'center_position':[1,2,3],'half_height':2,'width':832,'height':480}
        current_world_points = np.array([[1,2,3],[1,4,3],[1,0,3],[1+832/240,2,3]])
        np.testing.assert_allclose(project_recorded_camera_points(current_world_points,current_camera_record),[[416,240],[416,0],[416,480],[832,240]])

    def test_rotation_and_depth_invariance(self):
        current_camera_record = {'rotation_matrix':[[0,0,-1],[0,1,0],[1,0,0]],'center_position':[0,0,0],'half_height':1,'width':832,'height':480}
        np.testing.assert_allclose(project_recorded_camera_points([[0,0,1],[10,0,1]],current_camera_record),[[176,240],[176,240]])
        current_camera_record['half_height']=0
        with self.assertRaises(ValueError):
            project_recorded_camera_points([[0,0,0]],current_camera_record)
