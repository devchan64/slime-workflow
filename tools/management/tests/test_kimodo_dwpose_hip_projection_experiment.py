"""3D 투영 골반 복원의 중심과 다리 벡터 보존을 확인한다."""
import unittest
from collections import namedtuple
import numpy as np
from generators.kimodo.dwpose_hip_projection_experiment import reconstruct_projected_hip_pair, reconstruct_projected_hip_frames


class KimodoHipProjectionExperimentTests(unittest.TestCase):
    def test_preserves_hip_center_and_leg_vectors(self):
        current_detected=np.zeros((18,2));current_detected[[2,5]]=[[4,1],[6,1]];current_detected[[8,11]]=[[4.9,6],[5.1,6]];current_detected[[9,10,12,13]]=[[4,8],[4,10],[6,8],[6,10]]
        current_reference=current_detected.copy();current_reference[[8,11]]=[[4,6],[6,6]]
        current_adjusted=reconstruct_projected_hip_pair(current_detected,current_reference)
        np.testing.assert_allclose(current_adjusted[[8,11]].mean(0),current_detected[[8,11]].mean(0))
        for current_hip,current_knee,current_ankle in ((8,9,10),(11,12,13)):
            np.testing.assert_allclose(current_adjusted[current_knee]-current_adjusted[current_hip],current_detected[current_knee]-current_detected[current_hip])
            np.testing.assert_allclose(current_adjusted[current_ankle]-current_adjusted[current_knee],current_detected[current_ankle]-current_detected[current_knee])
        self.assertGreater(np.linalg.norm(current_adjusted[8]-current_adjusted[11]),np.linalg.norm(current_detected[8]-current_detected[11]))
        current_keypoint_type=namedtuple('Keypoint','x y')
        current_body_type=namedtuple('Body','keypoints')
        current_pose_type=namedtuple('Pose','body other')
        current_points=[current_keypoint_type(*current_point) for current_point in current_detected]
        current_points[0]=None
        current_pose=current_pose_type(current_body_type(current_points),'보존')
        current_projected=np.column_stack([current_reference,np.ones(18)]).tolist()
        current_frames=reconstruct_projected_hip_frames([[current_pose]],[current_projected])
        self.assertIsNone(current_frames[0][0].body.keypoints[0])
        self.assertEqual(current_frames[0][0].other,'보존')
        np.testing.assert_allclose([current_frames[0][0].body.keypoints[8].x,current_frames[0][0].body.keypoints[8].y],current_adjusted[8])
        current_points[8]=None
        with self.assertRaisesRegex(ValueError,'골반'):
            reconstruct_projected_hip_frames([[current_pose]],[current_projected])
        current_reference[[2,5]]=current_reference[[8,11]].mean(0)
        with self.assertRaisesRegex(ValueError,'몸통'):
            reconstruct_projected_hip_pair(current_detected,current_reference)


if __name__=='__main__':
    unittest.main()
