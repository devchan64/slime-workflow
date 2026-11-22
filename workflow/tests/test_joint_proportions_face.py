import unittest
import numpy as np
from workflow.domains.joint_proportions.face_anchors import estimate_face_anchors
from workflow.domains.joint_proportions.vace_pose_export import prepare_pose_frames


class FaceEstimateTests(unittest.TestCase):
    def fixture(self):
        j = np.zeros((6, 22, 3))
        j[:, 12] = [0, 1.4, 0]; j[:, 15] = [0, 1.7, 0]
        j[:, 16] = [.25, 1.3, 0]; j[:, 17] = [-.25, 1.3, 0]
        j[:, 1] = [.15, .8, 0]; j[:, 2] = [-.15, .8, 0]
        j[:, 4] = [.15, .4, 0]; j[:, 5] = [-.15, .4, 0]
        return j

    def test_translation_rotation_and_explicit_estimate(self):
        j = self.fixture()
        face, info = estimate_face_anchors(j)
        delta = np.array([3., -2., 4.])
        moved, _ = estimate_face_anchors(j + delta)
        np.testing.assert_allclose(moved, face + delta, atol=1e-12)
        rotation = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])
        turned, _ = estimate_face_anchors(j @ rotation.T)
        np.testing.assert_allclose(turned, face @ rotation.T, atol=1e-12)
        self.assertIn('unobserved', info['orientation'])
        self.assertEqual(info['visibility'], 'not estimated')
        self.assertEqual(len(info['reference']['reference_sha256']), 64)

    def test_first_frame_matches_registered_reference(self):
        from generators.kimodo.reference_face_anchors import load_reference_face_template
        from generators.kimodo.multiview_face_anchor_experiment import calculate_body_alignment_basis
        j = self.fixture()
        face, _ = estimate_face_anchors(j)
        template, _ = load_reference_face_template()
        basis, center, size = calculate_body_alignment_basis(j[0, [17,16]], j[0, [2,1]].mean(axis=0))
        reference = np.asarray(template['face_joint_positions'])
        reference_center = np.asarray(template['body_joint_positions'])[[0,3]].mean(axis=0)
        np.testing.assert_allclose((face[0]-center) @ basis / size, reference-reference_center, atol=1e-10)

    def test_local_offset_rigid_and_rotation_covariant(self):
        j = self.fixture()
        original = j.copy()
        baseline, _ = estimate_face_anchors(j)
        shifted, info = estimate_face_anchors(j, local_offset=(0.1, -0.2, 0.05))
        np.testing.assert_array_equal(j, original)
        np.testing.assert_allclose(shifted[:, 1] - shifted[:, 2], baseline[:, 1] - baseline[:, 2])
        self.assertEqual(info['local_offset'], [0.1, -0.2, 0.05])
        rotation = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])
        rotated, _ = estimate_face_anchors(j @ rotation.T, local_offset=(0.1, -0.2, 0.05))
        np.testing.assert_allclose(rotated, shifted @ rotation.T, atol=1e-12)
        for bad in ((1, 2), (0, float('nan'), 0), (0, 1.1, 0)):
            with self.assertRaises(ValueError): estimate_face_anchors(j, local_offset=bad)

    def test_export_option_and_degenerate_head(self):
        j = self.fixture()
        body, _ = prepare_pose_frames(j, 16)
        face, _ = prepare_pose_frames(j, 16, include_face=True)
        self.assertTrue((body[:, [0,14,15,16,17],2] == 0).all())
        self.assertTrue((face[:, [0,14,15,16,17],2] == 1).all())
        j[:,15] = j[:,12]
        with self.assertRaises(ValueError): estimate_face_anchors(j)
