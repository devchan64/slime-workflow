import unittest
import numpy as np
from workflow.domains.joint_proportions.vace_pose_export import BODY18_FROM_HUMANML3D, prepare_pose_frames, split_vace_segments

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

    def test_segments_never_drop_frames_and_obey_vace(self):
        for count in range(5,1000):
            chunks=split_vace_segments(count)
            for start,end in chunks:
                self.assertTrue(0 <= start < end <= count)
                self.assertTrue(5 <= end-start <= 129 and (end-start-1)%4==0)
            self.assertEqual(set().union(*(set(range(a,b)) for a,b in chunks)),set(range(count)))
        self.assertEqual(split_vace_segments(128),[(0,125),(123,128)])

    def test_reject_bad_inputs(self):
        for data,fps in [(np.full((10,22,3),np.nan),20),(np.ones((10,21,3)),20),(np.ones((10,22,3)),0)]:
            with self.assertRaises(ValueError): prepare_pose_frames(data,fps)
