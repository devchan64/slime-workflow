"""MakeHuman 방향 전달의 회전·본 길이·실패 계약 검증."""
from pathlib import Path
import unittest
import numpy as np
from generators.hy_motion.makehuman_retarget import calculate_direction_rotation, retarget_makehuman_motion, SOURCE_BONE_SEGMENTS, SOURCE_TO_BLENDER

class MakeHumanRetargetTests(unittest.TestCase):
    def test_opposite_direction_rotation(self):
        current_rotation_matrix = calculate_direction_rotation(np.array([1., 0, 0]), np.array([-1., 0, 0]))
        np.testing.assert_allclose(current_rotation_matrix @ np.array([1., 0, 0]), [-1, 0, 0])
        self.assertAlmostEqual(np.linalg.det(current_rotation_matrix), 1)
        with self.assertRaises(ValueError):
            calculate_direction_rotation(np.zeros(3), np.ones(3))

    def test_motion_preserves_rig_lengths(self):
        current_asset_path = Path(__file__).resolve().parents[3] / 'assets/animation-models/vnccs-makehuman-base-v1/rig.npz'
        with np.load(current_asset_path, allow_pickle=False) as current_rig_archive:
            current_bone_names = current_rig_archive['bone_names'].tolist()
            current_rest_heads = current_rig_archive['rest_heads']
            current_rest_tails = current_rig_archive['rest_tails']
            current_parent_indices = current_rig_archive['parent_indices']
        current_joint_frames = np.random.default_rng(42).normal(size=(2, 52, 3))
        current_root_rotations = np.repeat(np.eye(3)[None], 2, axis=0)
        current_frame_rotations, current_frame_positions, current_quality_record = retarget_makehuman_motion(current_joint_frames, current_root_rotations, current_bone_names, current_parent_indices, current_rest_heads, current_rest_tails)
        self.assertLess(current_quality_record['max_direction_error_degrees'], 1e-4)
        for current_bone_index, current_parent_index in enumerate(current_parent_indices):
            np.testing.assert_allclose(np.linalg.det(current_frame_rotations[:, current_bone_index]), 1, atol=1e-6)
            if current_parent_index >= 0:
                np.testing.assert_allclose(np.linalg.norm(current_frame_positions[:, current_bone_index] - current_frame_positions[:, current_parent_index], axis=-1), np.linalg.norm(current_rest_heads[current_bone_index] - current_rest_heads[current_parent_index]), atol=1e-6)
        current_joint_frames[0, 0] = np.nan
        with self.assertRaises(ValueError):
            retarget_makehuman_motion(current_joint_frames, current_root_rotations, current_bone_names, current_parent_indices, current_rest_heads, current_rest_tails)
