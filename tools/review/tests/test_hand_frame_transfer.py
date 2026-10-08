"""손 기준점의 회전 전달·좌우 반사·입력 계약을 검증한다."""
import unittest
import numpy as np
from pathlib import Path
import tempfile
from generators.hy_motion.hand_frame_transfer import build_hand_frame,transfer_hand_rotation,load_hand_calibration


class HandFrameTransferTests(unittest.TestCase):
    def test_profile_load_and_duplicate_rejection(self):
        current_profile_path=Path(__file__).resolve().parents[3]/'generators/hy_motion/config/anny-hand-landmarks.yaml'
        self.assertFalse(load_hand_calibration(current_profile_path)['anatomical_joint_limits_verified'])
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_duplicate_path=Path(current_temporary_directory)/'invalid.yaml'
            current_duplicate_path.write_text(current_profile_path.read_text()+'\nschema_version: 1\n')
            with self.assertRaises(ValueError):
                load_hand_calibration(current_duplicate_path)

    def test_hand_basis_is_proper_for_both_sides(self):
        for current_side_sign in (-1,1):
            current_hand_frame=build_hand_frame([[0,0,0],[0,1,0],[current_side_sign,1,0],[-current_side_sign,1,0]])
            np.testing.assert_allclose(current_hand_frame.T@current_hand_frame,np.eye(3))
            self.assertAlmostEqual(np.linalg.det(current_hand_frame),1)

    def test_transfer_aligns_landmark_frames(self):
        source_reference_frame=np.eye(3)
        target_reference_frame=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        target_bone_rotation=np.array([[1,0,0],[0,0,-1],[0,1,0]])
        source_global_rotation=target_reference_frame
        current_result_rotation=transfer_hand_rotation(source_global_rotation,source_reference_frame,target_reference_frame,target_bone_rotation)
        np.testing.assert_allclose(current_result_rotation@target_bone_rotation.T@target_reference_frame,source_global_rotation@source_reference_frame)

    def test_degenerate_landmarks_fail(self):
        with self.assertRaises(ValueError):
            build_hand_frame(np.zeros((4,3)))
        with self.assertRaises(ValueError):
            build_hand_frame(np.full((4,3),np.nan))

    def test_reflection_is_not_rotation(self):
        with self.assertRaises(ValueError):
            transfer_hand_rotation(np.diag([-1,1,1]),np.eye(3),np.eye(3),np.eye(3))
