"""로컬 회전 소유권의 수학 계약. 실제 피부 품질 판정과 구분한다."""
import unittest
import numpy as np
from generators.hy_motion.shoulder_rotation_ownership import (
    calculate_shoulder_rotations, build_segment_reference, validate_owned_rotation,
)


class ShoulderOwnershipTests(unittest.TestCase):
    def test_world_audit_rejects_parent_rotation_error(self):
        from generators.hy_motion.body_rotation_ownership import measure_body_rotation_errors
        current_calibration_record = {'owners': [{'source_joint': 'Pelvis', 'source_index': 0, 'owner_bone': 'root', 'aligned_bind_rotation': np.eye(3)}]}
        current_global_rotations = np.tile(np.eye(3), (22, 1, 1))
        current_audit_records = [{'bone': 'root', 'world_rotation': np.eye(3)}]
        self.assertEqual(measure_body_rotation_errors(current_global_rotations, current_calibration_record, current_audit_records)[0]['world_matrix_error'], 0.)
        current_audit_records[0]['world_rotation'] = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        with self.assertRaisesRegex(ValueError, 'FK 목표'):
            measure_body_rotation_errors(current_global_rotations, current_calibration_record, current_audit_records)

    def test_aligned_reference_reconstructs_world_rotation(self):
        current_source_rotations = np.tile(np.eye(3), (22, 1, 1))
        current_source_rotations[13] = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
        current_bind_delta = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        current_parent_aligned = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])
        current_child_aligned = np.eye(3)
        current_calibration_record = {'profile_id': 'hymotion-anny-arm-aligned-v2', 'owners': [{'source_index': 13, 'owner_bone': 'clavicle.L', 'axis_transform': np.eye(3), 'parent_aligned_inverse': current_parent_aligned.T, 'effective_rest_inverse': current_bind_delta.T, 'aligned_bind_rotation': current_child_aligned}], 'rest_intermediates': ['shoulder01.L']}
        from generators.hy_motion.shoulder_rotation_ownership import SOURCE_TARGET_BASIS
        current_local_output = calculate_shoulder_rotations(current_source_rotations, current_calibration_record)['clavicle.L']
        np.testing.assert_allclose(current_parent_aligned @ current_bind_delta @ current_local_output, SOURCE_TARGET_BASIS @ current_source_rotations[13] @ SOURCE_TARGET_BASIS.T @ current_child_aligned, atol=1e-10)

    def test_identity_preserves_rest(self):
        current_calibration_record = {'owners': [{'source_index': 13, 'owner_bone': 'clavicle.L', 'axis_transform': np.eye(3)}], 'rest_intermediates': ['shoulder01.L']}
        current_rotation_values = calculate_shoulder_rotations(np.tile(np.eye(3), (22, 1, 1)), current_calibration_record)
        for current_rotation_matrix in current_rotation_values.values():
            np.testing.assert_allclose(current_rotation_matrix, np.eye(3), atol=1e-5)

    def test_rotation_has_one_owner(self):
        current_axis_matrix = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        current_source_rotations = np.tile(np.eye(3), (22, 1, 1))
        current_source_rotations[13] = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
        current_calibration_record = {'owners': [{'source_index': 13, 'owner_bone': 'clavicle.L', 'axis_transform': current_axis_matrix}, {'source_index': 16, 'owner_bone': 'upperarm01.L', 'axis_transform': np.eye(3)}], 'rest_intermediates': ['shoulder01.L', 'upperarm02.L']}
        current_rotation_values = calculate_shoulder_rotations(current_source_rotations, current_calibration_record)
        np.testing.assert_allclose(current_rotation_values['clavicle.L'], current_axis_matrix @ current_source_rotations[13] @ current_axis_matrix.T)
        for current_bone_name in ('upperarm01.L', 'shoulder01.L', 'upperarm02.L'):
            np.testing.assert_allclose(current_rotation_values[current_bone_name], np.eye(3))

    def test_reject_invalid_rotations(self):
        for current_rotation_matrix in (np.diag([-1., 1., 1.]), np.zeros((3, 3)), np.full((3, 3), np.nan)):
            with self.assertRaises(ValueError):
                validate_owned_rotation(current_rotation_matrix)

    def test_reject_degenerate_reference(self):
        with self.assertRaises(ValueError):
            build_segment_reference([1., 0., 0.], [2., 0., 0.])

    def test_reference_is_right_handed(self):
        current_reference_matrix = build_segment_reference([1., 2., 0.], [0., 0., 1.])
        np.testing.assert_allclose(current_reference_matrix.T @ current_reference_matrix, np.eye(3), atol=1e-10)
        self.assertAlmostEqual(np.linalg.det(current_reference_matrix), 1.)


if __name__ == '__main__':
    unittest.main()
