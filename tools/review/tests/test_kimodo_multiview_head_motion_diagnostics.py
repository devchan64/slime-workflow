"""카메라별 머리 방향 변화 진단을 검증한다."""
import unittest
import numpy as np
from generators.kimodo.multiview_head_motion_diagnostics import calculate_head_motion_diagnostics


class KimodoHeadMotionDiagnosticsTests(unittest.TestCase):
    def test_head_turn_changes_yaw_without_claiming_visibility(self):
        current_angle=np.deg2rad(30)
        current_rotation=np.array([[np.cos(current_angle),0,np.sin(current_angle)],[0,1,0],[-np.sin(current_angle),0,np.cos(current_angle)]])
        current_offsets=np.array([[0,0,1],[0,0,0],[0,0,0],[-1,0,0],[1,0,0]],dtype=float)
        current_report=calculate_head_motion_diagnostics(np.array([np.eye(3),current_rotation]),current_offsets,{'front':{'rotation_matrix':np.eye(3).tolist()}})
        self.assertAlmostEqual(current_report['views'][0]['relative_span_degrees'],30)
        self.assertEqual(current_report['frames'],2)
        self.assertTrue(any('가림' in current_item for current_item in current_report['limitations']))
        with self.assertRaisesRegex(ValueError,'회전행렬'):
            calculate_head_motion_diagnostics(np.zeros((1,3,3)),current_offsets,{'front':{'rotation_matrix':np.eye(3).tolist()}})
        current_offsets[0]=0
        with self.assertRaisesRegex(ValueError,'귀 중점'):
            calculate_head_motion_diagnostics(np.array([np.eye(3)]),current_offsets,{'front':{'rotation_matrix':np.eye(3).tolist()}})


if __name__=='__main__':
    unittest.main()
