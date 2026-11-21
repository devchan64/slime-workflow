"""SOMA 깊이 샘플과 앵커의 카메라 좌표를 검증한다."""
import unittest
import numpy as np
from generators.kimodo.soma_render import measure_face_anchor_depth,convert_orthographic_render_depth


class KimodoFaceAnchorDepthTests(unittest.TestCase):
    def test_recovers_orthographic_depth_from_pyrender_output(self):
        current_near=.01;current_far=100.
        current_linear=np.array([0.,.01,1.,6.,99.])
        current_encoded=np.zeros_like(current_linear)
        current_encoded[1:]=current_near*current_far/(current_near+current_far-current_linear[1:])
        np.testing.assert_allclose(convert_orthographic_render_depth(current_encoded,current_near,current_far),current_linear,atol=1e-10)
        with self.assertRaisesRegex(ValueError,'근·원 평면'):
            convert_orthographic_render_depth(current_encoded,100.,.01)

    def test_camera_depth_and_unmeasured_background(self):
        current_camera={'rotation_matrix':np.eye(3).tolist(),'center_position':[0.,0.,0.],'width':20,'height':10,'half_height':5.}
        current_anchors=np.array([[0.,0.,1.],[2.,0.,0.],[40.,0.,0.],[0.,1.,0.],[0.,-1.,0.]])
        current_depth=np.zeros((10,20));current_depth[5,10]=4.5
        current_result=measure_face_anchor_depth(current_anchors,current_camera,current_depth)
        self.assertEqual([current_row['joint'] for current_row in current_result],[0,14,15,16,17])
        self.assertAlmostEqual(current_result[0]['anchor_depth'],5.)
        self.assertAlmostEqual(current_result[0]['depth_gap'],.5)
        self.assertIsNone(current_result[1]['surface_depth'])
        self.assertIsNone(current_result[2]['depth_gap'])
        with self.assertRaisesRegex(ValueError,'깊이 영상'):
            measure_face_anchor_depth(current_anchors,current_camera,np.zeros((2,2)))


if __name__=='__main__':
    unittest.main()
