"""피부 충돌 경계의 진행·거절·검사 실패 계약을 검증한다."""
import unittest
from generators.hy_motion.skin_collision_barrier import advance_collision_free


class SkinCollisionBarrierTests(unittest.TestCase):
    def test_first_detected_contact_stops_progress(self):
        current_pose_state = [0.0]
        current_result_record = advance_collision_free(lambda current_fraction_value: current_pose_state.__setitem__(0, current_fraction_value), lambda: .35 <= current_pose_state[0] <= .65, 10, 12)
        self.assertTrue(current_result_record['blocked'])
        self.assertLess(current_pose_state[0], .35)
        self.assertLess(.35 - current_pose_state[0], .1 / 4096)

    def test_free_target_is_reached(self):
        current_pose_state = [0.0]
        current_result_record = advance_collision_free(lambda current_fraction_value: current_pose_state.__setitem__(0, current_fraction_value), lambda: False, 4, 10)
        self.assertEqual(current_pose_state[0], 1)
        self.assertFalse(current_result_record['blocked'])

    def test_colliding_start_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '시작 자세'):
            advance_collision_free(lambda current_fraction_value: None, lambda: True, 4, 10)

    def test_invalid_parameters_are_rejected(self):
        for current_step_count, current_refinement_count in ((0, 10), (True, 10), (4, -1), (4, 25)):
            with self.assertRaises(ValueError):
                advance_collision_free(lambda current_fraction_value: None, lambda: False, current_step_count, current_refinement_count)

    def test_invalid_collision_result_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'bool'):
            advance_collision_free(lambda current_fraction_value: None, lambda: 0, 4, 10)

    def test_probe_error_restores_safe_pose(self):
        current_pose_state = [0.0]

        def probe_current_collision():
            if current_pose_state[0] > .5:
                raise RuntimeError('검사 실패')
            return False

        with self.assertRaisesRegex(RuntimeError, '검사 실패'):
            advance_collision_free(lambda current_fraction_value: current_pose_state.__setitem__(0, current_fraction_value), probe_current_collision, 4, 10)
        self.assertEqual(current_pose_state[0], .5)
