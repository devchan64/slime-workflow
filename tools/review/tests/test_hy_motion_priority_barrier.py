"""손 우선 제한과 해결 불가능 상태의 원본 보존 계약."""
import unittest
from generators.hy_motion.priority_skin_barrier import resolve_priority_collision


class PriorityBarrierContractTests(unittest.TestCase):
    def test_safe_target_preserved(self):
        current_pose_state = {}
        def apply_test_fraction(current_bone_group, current_pose_fraction):
            current_pose_state.update(bones=current_bone_group, fraction=current_pose_fraction)
        current_result_record = resolve_priority_collision([('hand',)], apply_test_fraction, lambda: False, 8, 8)
        self.assertEqual(current_pose_state, {'bones': (), 'fraction': 1.0})
        self.assertFalse(current_result_record['unresolved'])

    def test_hand_before_arm(self):
        current_pose_state = {}
        def apply_test_fraction(current_bone_group, current_pose_fraction):
            current_pose_state.update(bones=current_bone_group, fraction=current_pose_fraction)
        def probe_test_collision():
            return not current_pose_state['bones'] or current_pose_state['fraction'] >= .6
        current_result_record = resolve_priority_collision([('hand',), ('hand', 'arm')], apply_test_fraction, probe_test_collision, 8, 8)
        self.assertEqual(current_result_record['limited_bones'], ['hand'])
        self.assertLess(current_result_record['fraction'], .6)
        self.assertGreater(current_result_record['fraction'], .59)

    def test_unresolved_preserves_target(self):
        current_pose_state = {}
        def apply_test_fraction(current_bone_group, current_pose_fraction):
            current_pose_state.update(bones=current_bone_group, fraction=current_pose_fraction)
        current_result_record = resolve_priority_collision([('hand',), ('hand', 'arm')], apply_test_fraction, lambda: True, 8, 8)
        self.assertTrue(current_result_record['unresolved'])
        self.assertEqual(current_pose_state, {'bones': (), 'fraction': 1.0})
