"""방향 가중치 원형 보간과 입력 거절을 확인한다."""
import unittest
from generators.kimodo.multiview_direction_weight_diagnostics import interpolate_direction_joint_weights


class KimodoDirectionWeightDiagnosticsTests(unittest.TestCase):
    def test_circular_interpolation_and_exact_anchor(self):
        current_views=[{'observation':current_index+1,'fitted_yaw_degrees':45*current_index} for current_index in range(8)]
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':current_index/7,'reason':'검수'} for current_joint in range(18)]} for current_index in range(8)]}
        current_result=interpolate_direction_joint_weights(current_views,current_weights,[0,22.5,337.5,-22.5,360],0)
        current_frames=current_result['frames']
        self.assertEqual(current_frames[0]['weights'][0],0)
        self.assertAlmostEqual(current_frames[1]['weights'][0],1/14)
        self.assertAlmostEqual(current_frames[2]['weights'][0],.5)
        self.assertAlmostEqual(current_frames[3]['weights'][0],.5)
        self.assertEqual(current_frames[4]['weights'][0],0)
        self.assertEqual(current_frames[2]['left_observation'],8)
        self.assertEqual(current_frames[2]['right_observation'],1)
        current_views[1]['fitted_yaw_degrees']=360
        with self.assertRaisesRegex(ValueError,'같은 방향'):
            interpolate_direction_joint_weights(current_views,current_weights,[0],0)


if __name__=='__main__':
    unittest.main()
