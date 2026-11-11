"""방향 가중치와 영상 검출의 차이를 보존한다."""
import copy
import unittest
import numpy as np
from generators.kimodo.multiview_visibility_disagreement import compare_direction_detector_evidence,calculate_local_white_fraction


class KimodoVisibilityDisagreementTests(unittest.TestCase):
    def test_white_background_measurement_does_not_assert_occlusion(self):
        current_image=np.full((12,12,3),255,dtype=np.uint8)
        self.assertEqual(calculate_local_white_fraction(current_image,[5,5]),1.)
        current_image[3:8,3:8]=0
        self.assertEqual(calculate_local_white_fraction(current_image,[5,5]),0.)
        with self.assertRaisesRegex(ValueError,'범위'):
            calculate_local_white_fraction(current_image,[0,0])

    def test_records_high_score_with_zero_weight_and_rejects_misalignment(self):
        current_points=[[0.,0.,.9,current_index] for current_index in range(18)]
        current_points[17]=[3.,4.,.9,17]
        current_raw=[[[[current_points]]]]
        current_weights={'direction':'front','frames':[{'frame':0,'weights':[0. if current_index==17 else 1. for current_index in range(18)]}]}
        current_direct={'directions':{'front':{'source_frames':[0],'body_points_832x480':[[[0.,0.,1.] for _ in range(18)]]}}}
        current_result=compare_direction_detector_evidence(current_weights,current_raw,current_direct,'front')
        self.assertEqual(len(current_result['rows']),1)
        self.assertEqual(current_result['rows'][0]['joint'],17)
        self.assertEqual(current_result['rows'][0]['projected_distance_px'],5.)
        current_wrong=copy.deepcopy(current_direct);current_wrong['directions']['front']['source_frames']=[1]
        with self.assertRaisesRegex(ValueError,'프레임 순서'):
            compare_direction_detector_evidence(current_weights,current_raw,current_wrong,'front')
        with self.assertRaisesRegex(ValueError,'방향'):
            compare_direction_detector_evidence(current_weights,current_raw,current_direct,'left')


if __name__=='__main__':
    unittest.main()
