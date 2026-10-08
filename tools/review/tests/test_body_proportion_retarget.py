"""체형 비율 실험용 IK의 길이·목표·입력 오류 검증."""
import unittest
import sys
from pathlib import Path
try:
    import bpy
    from mathutils import Vector
except ImportError as current_import_error:
    raise unittest.SkipTest('Blender Python이 필요합니다.') from current_import_error
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from generators.momask.body_proportion_retarget import build_body_coordinate, solve_two_segment, calculate_body_ratios, map_proportional_wrist


class BodyProportionRetargetTests(unittest.TestCase):
    def test_proportional_wrist_matches_experiment_formula(self):
        source_body_points = [(1,0,0),(-1,0,0),(0,0,4)]
        target_body_points = [(2,0,0),(-2,0,0),(0,0,3)]
        current_ratio_vector = calculate_body_ratios(source_body_points,target_body_points)
        self.assertEqual(current_ratio_vector,Vector((2,1,.75)))
        current_wrist_target = map_proportional_wrist(source_body_points,target_body_points,(1.5,.2,1),0,current_ratio_vector)
        self.assertLess((current_wrist_target-Vector((3,.2,.75))).length,1e-6)

    def test_proportional_input_rejects_invalid_ratio(self):
        with self.assertRaises(ValueError):
            map_proportional_wrist([(1,0,0),(-1,0,0),(0,0,4)],[(1,0,0),(-1,0,0),(0,0,4)],(1,0,0),0,(0,1,1))

    def test_reachable_target_preserves_lengths(self):
        current_shoulder_point, current_elbow_point, current_wrist_point = map(Vector, [(0,0,0),(1,0,0),(1,1,0)])
        desired_wrist_point = Vector((.5,1.5,0))
        desired_elbow_point, reachable_wrist_point, current_clamp_error = solve_two_segment(current_shoulder_point,current_elbow_point,current_wrist_point,desired_wrist_point)
        self.assertAlmostEqual((desired_elbow_point-current_shoulder_point).length,1,places=5)
        self.assertAlmostEqual((reachable_wrist_point-desired_elbow_point).length,1,places=5)
        self.assertLess(current_clamp_error,1e-6)

    def test_unreachable_target_records_clamp(self):
        current_result_values = solve_two_segment(*map(Vector,[(0,0,0),(1,0,0),(1,1,0),(0,4,0)]))
        self.assertAlmostEqual(current_result_values[1].length,2,places=5)
        self.assertGreater(current_result_values[2],1.99)

    def test_body_coordinate_is_orthonormal(self):
        current_body_basis = build_body_coordinate((1,0,0),(-1,0,0),(0,0,2))
        self.assertAlmostEqual(current_body_basis.determinant(),1,places=5)
        self.assertEqual(current_body_basis @ Vector((1,0,0)),Vector((1,0,0)))

    def test_invalid_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            build_body_coordinate((0,0,0),(0,0,0),(0,0,1))
        with self.assertRaises(ValueError):
            solve_two_segment(*map(Vector,[(0,0,0),(1,0,0),(1,1,0),(float('nan'),0,0)]))
