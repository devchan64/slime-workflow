import unittest
import numpy as np
from workflow.domains.joint_proportions.humanml3d import adjust_humanml3d_proportions


def motion():
    p=np.zeros((2,22,3),dtype=float)
    for i,x in ((1,-.2),(2,.2)): p[:,i]=[x,1,0]
    for i,x in ((4,-.2),(5,.2)): p[:,i]=[x,.6,0]
    for i,x in ((7,-.2),(8,.2)): p[:,i]=[x,.2,0]
    for i,x in ((10,-.2),(11,.2)): p[:,i]=[x,.2,.2]
    for i,x in ((16,-.4),(17,.4)): p[:,i]=[x,2,0]
    for i,x in ((18,-.7),(19,.7)): p[:,i]=[x,1.8,0]
    for i,x in ((20,-1),(21,1)): p[:,i]=[x,1.6,0]
    p[1]+=np.array([2,0,1]);return p


def reference():
    return {'schema':'body18-reference-ratios-v4','ratios':{'shoulder_width':.7,'hip_width':.4,'upper_arm':.5,'forearm':.4,'thigh':.6,'shin':.5}}


class JointProportionsTest(unittest.TestCase):
    def test_lengths_motion_anchors_and_immutability(self):
        a=motion(); old=a.copy();b,meta=adjust_humanml3d_proportions(a,reference())
        np.testing.assert_array_equal(a,old)
        np.testing.assert_allclose(b[:,0],a[:,0])
        np.testing.assert_allclose(b[:,[1,2]].mean(1),a[:,[1,2]].mean(1))
        np.testing.assert_allclose(np.linalg.norm(b[:,18]-b[:,16],axis=1),.5)
        np.testing.assert_allclose(b[:,10]-b[:,7],a[:,10]-a[:,7])
        np.testing.assert_allclose(b[1]-b[0],np.broadcast_to([2,0,1],(22,3)),atol=1e-12)
        self.assertIn('weapon',meta['not_applied'])

    def test_invalid_input_and_missing_or_invalid_ratio_rejected(self):
        for value in (np.zeros((1,21,3)),np.full((1,22,3),np.nan),np.zeros((0,22,3))):
            with self.assertRaises(ValueError):adjust_humanml3d_proportions(value,reference())
        bad=reference();bad['ratios']['shin']=float('nan')
        with self.assertRaises(ValueError):adjust_humanml3d_proportions(motion(),bad)
        degenerate=motion();degenerate[:,4]=degenerate[:,1]
        with self.assertRaises(ValueError):adjust_humanml3d_proportions(degenerate,reference())
