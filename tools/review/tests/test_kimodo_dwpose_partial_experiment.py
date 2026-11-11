"""미검출 관절을 합성하지 않는 부분 보정의 회귀 검사."""
import unittest
from collections import namedtuple
import numpy as np
from generators.kimodo.dwpose_export import adjust_detected_pose_frames
from generators.kimodo.dwpose_partial_experiment import adjust_partial_detected_frames
from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS


class KimodoPartialPoseExperimentTests(unittest.TestCase):
    def test_complete_frames_match_existing_and_missing_chain_is_omitted(self):
        current_point_type=namedtuple('Point','x y score id')
        current_body_type=namedtuple('Body','keypoints')
        current_pose_type=namedtuple('Pose','body left_hand right_hand face')
        current_points=[current_point_type(float(i),float(i+1),1.,i) for i in range(18)]
        for current_index,current_xy in {0:(5,0),1:(5,2),2:(4,2),5:(6,2),8:(4,6),11:(6,6)}.items():current_points[current_index]=current_point_type(*current_xy,1.,current_index)
        current_pose=current_pose_type(current_body_type(current_points),[current_point_type(8,5,1,0)],None,None)
        current_gains={current_group:1. for current_group in REFERENCE_SEGMENT_GROUPS}
        current_ratio={'schema':'body18-reference-ratios-v4','body_axis':{'vertical_nose_shoulder_to_torso':.5}}
        current_original=adjust_detected_pose_frames([[current_pose]],(20,20),current_gains,85,current_ratio)
        current_partial,current_record=adjust_partial_detected_frames([[current_pose]],(20,20),current_gains,85,current_ratio)
        for current_a,current_b in zip(current_original[0][0].body.keypoints,current_partial[0][0].body.keypoints):np.testing.assert_allclose([current_a.x,current_a.y],[current_b.x,current_b.y])
        self.assertEqual(current_record['incomplete_frames'],[])
        current_missing_points=current_points.copy();current_missing_points[6]=None
        current_missing_pose=current_pose._replace(body=current_body_type(current_missing_points))
        current_output,current_record=adjust_partial_detected_frames([[current_missing_pose]],(20,20),current_gains,85,current_ratio)
        self.assertIsNone(current_output[0][0].body.keypoints[6])
        self.assertIsNone(current_output[0][0].body.keypoints[7])
        self.assertIsNone(current_output[0][0].left_hand)
        self.assertEqual(current_record['incomplete_frames'][0]['missing_joints'],[6,7])
        self.assertIsNotNone(current_output[0][0].body.keypoints[3])


if __name__=='__main__':
    unittest.main()
