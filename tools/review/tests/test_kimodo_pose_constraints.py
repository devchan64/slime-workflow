"""키프레임 입력의 경계와 손상 데이터 거절을 검증한다."""
import copy
import unittest
from generators.kimodo.pose_constraints import validate_pose_constraints


class KimodoPoseConstraintTests(unittest.TestCase):
    def test_valid_boundary_frames(self):
        current_constraint_records = [{'type': 'fullbody', 'frame_indices': [0, 299], 'local_joints_rot': [[[0.0]*3 for _ in range(77)] for _ in range(2)], 'root_positions': [[0.0, 1.0, 0.0]]*2}]
        self.assertEqual(validate_pose_constraints(current_constraint_records, 300), current_constraint_records)
        self.assertEqual(validate_pose_constraints([], 300), [])
        for current_field_name, current_invalid_value in [('frame_indices', [0, 300]), ('frame_indices', [0, 0]), ('frame_indices', [True, 299]), ('frame_indices', [299, 0]), ('root_positions', [[0, float('nan'), 0]]*2), ('local_joints_rot', [[[0]*3]*30]*2), ('type', 'unknown')]:
            current_invalid_record = copy.deepcopy(current_constraint_records)
            current_invalid_record[0][current_field_name] = current_invalid_value
            with self.subTest(field=current_field_name, value=current_invalid_value):
                with self.assertRaises(ValueError):
                    validate_pose_constraints(current_invalid_record, 300)
        current_unknown_record = copy.deepcopy(current_constraint_records)
        current_unknown_record[0]['extra'] = True
        with self.assertRaises(ValueError):
            validate_pose_constraints(current_unknown_record, 300)

    def test_invalid_container_values(self):
        for current_invalid_value in (None, {}, 'fullbody', [None], [{}, {}]):
            with self.assertRaises(ValueError):
                validate_pose_constraints(current_invalid_value, 300)
