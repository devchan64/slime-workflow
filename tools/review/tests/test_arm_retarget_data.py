"""리그 실측의 단위·부모 대응·변환 불변성과 실패 계약."""
import unittest
import numpy as np
from generators.hy_motion.arm_retarget_data import load_arm_contract, measure_arm_segments, validate_named_chain


class ArmRetargetDataTest(unittest.TestCase):
    def test_contract_has_no_invented_constraints(self):
        current_contract_record = load_arm_contract()
        self.assertIsNone(current_contract_record['policy']['anatomical_limits'])
        self.assertIsNone(current_contract_record['policy']['intermediate_bone_twist_distribution'])
        self.assertIs(current_contract_record['policy']['clinical_axes_verified'], False)

    def test_lengths_and_bend_are_rigid_invariant(self):
        current_reference_points = np.array([[0., 0., 0.], [1., 0., 0.], [1., 2., 0.]])
        current_basis_matrix = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        current_first_record = measure_arm_segments(current_reference_points)
        current_second_record = measure_arm_segments(current_reference_points @ current_basis_matrix.T + [2, 3, 4])
        self.assertEqual(current_first_record['lengths_m'], [1, 2])
        self.assertEqual(current_first_record['bend_degrees'], 90)
        self.assertEqual(current_first_record['lengths_m'], current_second_record['lengths_m'])
        self.assertEqual(current_first_record['bend_degrees'], current_second_record['bend_degrees'])

    def test_bad_points_fail(self):
        for current_bad_points in (np.zeros((3, 3)), np.zeros((2, 3)), np.full((3, 3), np.nan)):
            with self.assertRaises(ValueError):
                measure_arm_segments(current_bad_points)

    def test_intermediate_bones_cannot_be_skipped(self):
        validate_named_chain(['a', 'b', 'c'], [-1, 0, 1], ['a', 'b', 'c'])
        with self.assertRaises(ValueError):
            validate_named_chain(['a', 'b', 'c'], [-1, 0, 1], ['a', 'c'])
        with self.assertRaises(ValueError):
            validate_named_chain(['a', 'b', 'c'], [-1, 0, 1], ['a', 'missing'])
