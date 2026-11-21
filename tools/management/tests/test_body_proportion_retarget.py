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
from generators.momask.body_proportion_retarget import build_body_coordinate, solve_two_segment, calculate_body_ratios, map_proportional_wrist, solve_shoulder_reach, transport_elbow_reference


class BodyProportionRetargetTests(unittest.TestCase):
    def test_transported_plane_does_not_flip_elbow(self):
        current_shoulder_point=Vector((0,0,0))
        current_upper_vector=Vector((1,1,0)).normalized()
        current_lower_vector=Vector((-1,1,0)).normalized()
        desired_wrist_point=Vector((.5,1.2,.2))
        current_reference_elbow=transport_elbow_reference(current_shoulder_point,desired_wrist_point,current_upper_vector,current_lower_vector,1,1)
        desired_elbow_point,reachable_wrist_point,current_clamp_error=solve_two_segment(current_shoulder_point,current_upper_vector,current_upper_vector+current_lower_vector,desired_wrist_point,current_reference_elbow)
        current_actual_normal=desired_elbow_point.cross(reachable_wrist_point-desired_elbow_point).normalized()
        current_expected_normal=(current_upper_vector+current_lower_vector).rotation_difference(desired_wrist_point) @ current_upper_vector.cross(current_lower_vector).normalized()
        self.assertGreater(current_actual_normal.dot(current_expected_normal),.99999)

    def test_transported_plane_rejects_straight_arm(self):
        with self.assertRaises(ValueError):
            transport_elbow_reference(Vector((0,0,0)),Vector((0,2,0)),Vector((0,1,0)),Vector((0,1,0)),1,1)

    def test_explicit_elbow_reference_controls_bend_side(self):
        current_shoulder_point=Vector((0,0,0))
        current_elbow_point=Vector((1,1,0))
        current_wrist_point=Vector((0,2,0))
        desired_elbow_point,reachable_wrist_point,current_clamp_error=solve_two_segment(current_shoulder_point,current_elbow_point,current_wrist_point,current_wrist_point,Vector((-1,1,0)))
        self.assertLess(desired_elbow_point.x,0)
        self.assertAlmostEqual((desired_elbow_point-current_shoulder_point).length,2**.5,places=5)
        self.assertLess((reachable_wrist_point-current_wrist_point).length,1e-6)

    def test_invalid_elbow_reference_fails(self):
        with self.assertRaises(ValueError):
            solve_two_segment(Vector((0,0,0)),Vector((1,1,0)),Vector((0,2,0)),Vector((0,2,0)),Vector((float('nan'),0,0)))

    def test_shoulder_swing_preserves_length_and_reach(self):
        current_pivot_point = Vector((0,0,0))
        current_shoulder_point = Vector((.15,0,0))
        desired_wrist_point = Vector((.15,0,-.4))
        desired_shoulder_point,current_swing_degrees = solve_shoulder_reach(current_pivot_point,current_shoulder_point,desired_wrist_point,.38,current_swing_limit_degrees=15)
        self.assertAlmostEqual(desired_shoulder_point.length,.15,places=6)
        self.assertAlmostEqual((desired_wrist_point-desired_shoulder_point).length,.38,places=6)
        self.assertLess(current_swing_degrees,15)

    def test_shoulder_swing_limit_is_respected(self):
        desired_shoulder_point,current_swing_degrees = solve_shoulder_reach(Vector((0,0,0)),Vector((.15,0,0)),Vector((.15,0,-1)),.3,current_swing_limit_degrees=15)
        self.assertAlmostEqual(current_swing_degrees,15,places=5)
        self.assertAlmostEqual(desired_shoulder_point.length,.15,places=6)

    def test_shoulder_swing_rejects_degenerate_input(self):
        with self.assertRaises(ValueError):
            solve_shoulder_reach(Vector((0,0,0)),Vector((0,0,0)),Vector((1,0,0)),.3,current_swing_limit_degrees=15)

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
