import unittest
import numpy as np
from workflow.domains.joint_proportions.vace_pose_export import BODY18_FROM_HUMANML3D, prepare_pose_frames, validate_vace_frame_count

class PoseExportTest(unittest.TestCase):
    def test_mapping_and_16fps_timing(self):
        frames=np.zeros((21,22,3),float)
        for i in range(22): frames[:,i]=[i*.01,i*.02,0]
        frames[:,:,0] += np.arange(21)[:,None]*.01
        pose,src=prepare_pose_frames(frames,20)
        self.assertEqual(pose.shape,(17,18,3))
        np.testing.assert_allclose(src,[x*1.25 for x in range(17)])
        self.assertEqual(BODY18_FROM_HUMANML3D[4],21)
        self.assertEqual(BODY18_FROM_HUMANML3D[7],20)
        self.assertTrue((pose[:,[0,14,15,16,17],2]==0).all())
        self.assertTrue((pose[:,list(BODY18_FROM_HUMANML3D),2]==1).all())
        np.testing.assert_allclose(pose[1,4,0]-pose[0,4,0],pose[1,7,0]-pose[0,7,0])

    def test_incompatible_lengths_fail_without_splitting(self):
        for count in (5, 17, 125, 129):
            self.assertEqual(validate_vace_frame_count(count), count)
        for count in (4, 16, 128, 130, 257):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, '자르거나 분할하지 않습니다'):
                validate_vace_frame_count(count)

    def test_reject_bad_inputs(self):
        for data,fps in [(np.full((10,22,3),np.nan),20),(np.ones((10,21,3)),20),(np.ones((10,22,3)),0)]:
            with self.assertRaises(ValueError): prepare_pose_frames(data,fps)
