"""회전 채널의 열 우선 계약과 엄격한 오류 처리 검증."""
import unittest
import numpy as np
from generators.hy_motion.rotation_channels import decode_local_rotations, reconstruct_rotation_channels


class HyMotionRotationTests(unittest.TestCase):
    def test_column_layout_matches_known_rotation(self):
        current_expected_matrix=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        current_rotation_values=np.tile(current_expected_matrix[:,:2].reshape(6),(1,22,1))
        np.testing.assert_allclose(decode_local_rotations(current_rotation_values)[0,0],current_expected_matrix)

    def test_identity_chain_matches_positions(self):
        current_rest_points=np.arange(66).reshape(22,3)/100
        current_parent_indices=np.arange(-1,21)
        current_rotation_values=np.tile(np.eye(3)[:,:2].reshape(6),(2,22,1))
        current_translation_values=np.zeros((2,3))
        current_expected_points=np.tile(current_rest_points,(2,1,1))
        current_local_rotations,current_global_rotations,current_maximum_error=reconstruct_rotation_channels(current_rotation_values,current_rest_points,current_parent_indices,current_translation_values,current_expected_points)
        self.assertLess(current_maximum_error,1e-10)
        with self.assertRaisesRegex(ValueError,'불일치'):
            reconstruct_rotation_channels(current_rotation_values,current_rest_points,current_parent_indices,current_translation_values,current_expected_points+1)

    def test_invalid_rotation_is_rejected(self):
        for current_rotation_values in (np.zeros((1,22,6)),np.full((1,22,6),np.nan),np.zeros((1,52,6))):
            with self.assertRaises(ValueError):
                decode_local_rotations(current_rotation_values)
