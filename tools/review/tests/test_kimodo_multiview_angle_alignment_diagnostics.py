"""8방향 각도 정합과 제외 관측 검증을 확인한다."""
import unittest
from generators.kimodo.multiview_angle_alignment_diagnostics import fit_circular_angle_alignment,diagnose_multiview_angle_alignment


class KimodoAngleAlignmentDiagnosticsTests(unittest.TestCase):
    def test_circular_alignment_and_leave_one_out(self):
        current_angles=[0,45,90,135,180,225,270,315]
        current_views=[{'observation':current_index+1,'fitted_yaw_degrees':(current_angle+10)%360} for current_index,current_angle in enumerate(current_angles)]
        current_motion={'views':[{'direction':f'view_{current_index}','first_yaw_degrees':current_angle} for current_index,current_angle in enumerate(current_angles)]}
        current_mapping={f'view_{current_index}':current_index+1 for current_index in range(8)}
        current_result=diagnose_multiview_angle_alignment({'views':current_views},current_motion,current_mapping)
        self.assertEqual(current_result['fit']['sign'],1)
        self.assertAlmostEqual(current_result['fit']['offset_degrees'],10)
        self.assertAlmostEqual(current_result['heldout_mae_degrees'],0)
        current_mirrored=fit_circular_angle_alignment(current_angles,[(-current_angle+15)%360 for current_angle in current_angles])
        self.assertEqual(current_mirrored['sign'],-1)
        self.assertAlmostEqual(current_mirrored['offset_degrees'],15)
        current_mapping['view_0']=2
        with self.assertRaisesRegex(ValueError,'일대일'):
            diagnose_multiview_angle_alignment({'views':current_views},current_motion,current_mapping)
        with self.assertRaisesRegex(ValueError,'3개 이상'):
            fit_circular_angle_alignment([1,2],[3,4])


if __name__=='__main__':
    unittest.main()
