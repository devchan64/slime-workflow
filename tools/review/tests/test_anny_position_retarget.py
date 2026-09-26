"""Blender Python에서 공통 위치 리타깃의 기하 불변량과 프로필 계약을 검증한다."""
import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml
try:
    import bpy
    from mathutils import Matrix, Quaternion, Vector
except ImportError as runtime_import_error:
    raise unittest.SkipTest('Blender Python 런타임에서 실행해야 합니다.') from runtime_import_error

REPOSITORY_ROOT_PATH = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT_PATH / 'generators/momask'))
from position_retarget import PositionRetargetSolver, load_retarget_profile


def create_segment_profile():
    return {'schema_version': 2, 'source_reference': {'id':'synthetic-reference', 'source_url':'test://reference', 'source_sha256':'0'*64, 'joint_positions':[[0,0,0],[0,-1,0],[1,0,0]]}, 'profile_id': 'synthetic-rig', 'joint_count': 3,
            'coordinate_matrix': [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            'root_joint': 0, 'scale_source': [0, 1], 'scale_target': ['start', 'end'],
            'unmapped_policy': 'inherit_rest_local',
            'segments': [{'transfer_mode': 'absolute_direction', 'segment_id': 'segment', 'source_primary': [0, 1],
                          'target_primary': ['start', 'end'], 'source_secondary': None,
                          'target_secondary': None, 'target_bones': ['start', 'split']}]}


def create_segment_solver(profile_record_values=None, coordinate_rotation_value=None, target_length_scale=1):
    profile_record_values = profile_record_values or create_segment_profile()
    coordinate_rotation_value = coordinate_rotation_value or Quaternion()
    rest_position_values = {current_bone_name: coordinate_rotation_value @ Vector(current_point_values) * target_length_scale for current_bone_name, current_point_values in [('start', (0, 0, 0)), ('end', (0, -1, 0)), ('split', (0, -.5, 0)), ('lateral', (1, 0, 0))]}
    rest_rotation_values = {current_bone_name: coordinate_rotation_value.copy() for current_bone_name in rest_position_values}
    return PositionRetargetSolver(profile_record_values, rest_position_values, rest_rotation_values)


class PositionChannelRetargetTests(unittest.TestCase):
    def test_reference_delta_preserves_different_target_rest(self):
        profile_record_values = create_segment_profile()
        profile_record_values['segments'][0]['transfer_mode'] = 'reference_delta'
        profile_record_values['source_reference']['joint_positions'] = [[0, 0, 0], [0, 0, 1], [1, 0, 0]]
        current_solver_value = create_segment_solver(profile_record_values)
        for current_angle_value in (0, .2, .5):
            source_delta_rotation = Quaternion(Vector((1, 0, 0)), current_angle_value)
            current_joint_points = [Vector((0, 0, 0)), source_delta_rotation @ Vector((0, 0, 1)), Vector((1, 0, 0))]
            frame_rotation_values, frame_diagnostic_values = current_solver_value.calculate_frame_rotations(current_joint_points)
            self.assertAlmostEqual(abs(frame_rotation_values['start'].dot(source_delta_rotation)), 1, places=5)
            expected_target_direction = source_delta_rotation @ Vector((0, -1, 0))
            self.assertLess((Vector(frame_diagnostic_values['segment']['expected_target_direction']) - expected_target_direction).length, 1e-5)

    def test_registered_reference_preserves_axial_bind_rotations(self):
        profile_record_values = load_retarget_profile(REPOSITORY_ROOT_PATH / 'generators/momask/config/humanml22-anny-retarget.yaml')
        rig_archive_values = np.load(REPOSITORY_ROOT_PATH / 'assets/animation-models/anny-neutral-v4/anny-rest-rig.npz')
        rest_position_values = {current_bone_name: Vector(current_matrix_values[:3, 3]) for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
        rest_rotation_values = {current_bone_name: Matrix(current_matrix_values.tolist()).to_quaternion() for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
        source_reference_points = np.asarray(profile_record_values['source_reference']['joint_positions']) @ np.asarray(profile_record_values['coordinate_matrix']).T
        frame_rotation_values, _ = PositionRetargetSolver(profile_record_values, rest_position_values, rest_rotation_values).calculate_frame_rotations(source_reference_points)
        for current_segment_record in profile_record_values['segments']:
            if current_segment_record['transfer_mode'] == 'reference_delta':
                for current_bone_name in current_segment_record['target_bones']:
                    self.assertAlmostEqual(abs(frame_rotation_values[current_bone_name].dot(rest_rotation_values[current_bone_name])), 1, places=5)

    def test_opposite_rest_direction_preserves_motion(self):
        current_solver_value = create_segment_solver()
        previous_rotation_value = None
        previous_direction_value = None
        for current_angle_value in (-.02, -.01, 0, .01, .02, .8):
            current_direction_value = Vector((math.sin(current_angle_value), math.cos(current_angle_value), 0))
            current_rotation_values, current_diagnostic_values = current_solver_value.calculate_frame_rotations([(0, 0, 0), current_direction_value, (1, 0, 0)])
            current_rotation_value = current_rotation_values['start']
            self.assertLess(((current_rotation_value @ Vector((0, -1, 0))) - current_direction_value).length, 1e-5)
            self.assertLess(current_diagnostic_values['segment']['direction_error_degrees'], .001)
            self.assertAlmostEqual(abs(current_rotation_value.dot(current_rotation_values['split'])), 1, places=5)
            if previous_rotation_value is not None:
                rotation_step_value = previous_rotation_value.rotation_difference(current_rotation_value).angle
                direction_step_value = previous_direction_value.angle(current_direction_value)
                self.assertAlmostEqual(rotation_step_value, direction_step_value, delta=2e-4)
            previous_rotation_value = current_rotation_value
            previous_direction_value = current_direction_value

    def test_antipodal_step_preserves_direction(self):
        current_solver_value = create_segment_solver()
        for current_direction_value in ((0, -1, 0), (0, 1, 0), (0, -1, 0)):
            current_rotation_values, _ = current_solver_value.calculate_frame_rotations([(0, 0, 0), current_direction_value, (1, 0, 0)])
            self.assertLess(((current_rotation_values['start'] @ Vector((0, -1, 0))) - Vector(current_direction_value)).length, 1e-5)

    def test_coordinate_and_scale_equivariance(self):
        coordinate_rotation_value = Quaternion(Vector((1, 2, 3)).normalized(), 1.2)
        original_solver_value = create_segment_solver()
        transformed_solver_value = create_segment_solver(coordinate_rotation_value=coordinate_rotation_value, target_length_scale=2.7)
        for current_direction_value in ((.1, -1, .2), (.5, .4, .7), (.1, 1, .2)):
            current_joint_values = [Vector((0, 0, 0)), Vector(current_direction_value), Vector((1, 0, 0))]
            original_rotation_values, _ = original_solver_value.calculate_frame_rotations(current_joint_values)
            transformed_rotation_values, _ = transformed_solver_value.calculate_frame_rotations([coordinate_rotation_value @ current_point_value * 4 + Vector((3, 4, 5)) for current_point_value in current_joint_values])
            expected_rotation_value = coordinate_rotation_value @ original_rotation_values['start']
            self.assertAlmostEqual(abs(expected_rotation_value.dot(transformed_rotation_values['start'])), 1, places=5)

    def test_observed_frame_tracks_rotation(self):
        profile_record_values = create_segment_profile()
        profile_record_values['segments'][0].update(source_secondary=[0, 2], target_secondary=['start', 'lateral'])
        current_solver_value = create_segment_solver(profile_record_values)
        for current_angle_value in (0, .5, 2, 3.5, 6):
            expected_rotation_value = Quaternion(Vector((1, 1, 1)).normalized(), current_angle_value)
            current_rotation_values, _ = current_solver_value.calculate_frame_rotations([Vector((0, 0, 0)), expected_rotation_value @ Vector((0, -1, 0)), expected_rotation_value @ Vector((1, 0, 0))])
            self.assertAlmostEqual(abs(expected_rotation_value.dot(current_rotation_values['start'])), 1, places=5)
        with self.assertRaisesRegex(ValueError, '독립 축'):
            current_solver_value.calculate_frame_rotations([(0, 0, 0), (0, 1, 0), (0, 2, 0)])

    def test_invalid_frame_preserves_state(self):
        current_solver_value = create_segment_solver()
        current_solver_value.calculate_frame_rotations([(0, 0, 0), (0, -1, 0), (1, 0, 0)])
        saved_state_values = copy.deepcopy(current_solver_value.previous_segment_states)
        for invalid_joint_values in [[(0, 0, 0)] * 3, [(0, 0, 0), (float('nan'), 1, 0), (1, 0, 0)]]:
            with self.assertRaises(ValueError):
                current_solver_value.calculate_frame_rotations(invalid_joint_values)
        self.assertEqual(current_solver_value.previous_segment_states, saved_state_values)

    def test_resume_state_matches_continuous(self):
        current_solver_value = create_segment_solver()
        current_solver_value.calculate_frame_rotations([(0, 0, 0), (.3, -.7, .2), (1, 0, 0)])
        resumed_solver_value = create_segment_solver()
        resumed_solver_value.previous_segment_states = copy.deepcopy(current_solver_value.previous_segment_states)
        expected_rotation_values, _ = current_solver_value.calculate_frame_rotations([(0, 0, 0), (.8, .1, .5), (1, 0, 0)])
        resumed_rotation_values, _ = resumed_solver_value.calculate_frame_rotations([(0, 0, 0), (.8, .1, .5), (1, 0, 0)])
        self.assertEqual(expected_rotation_values, resumed_rotation_values)

    def test_profile_rejects_invalid_contracts(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            profile_source_path = Path(temporary_directory_name) / 'profile.yaml'
            profile_record_values = create_segment_profile()
            profile_source_path.write_text(yaml.safe_dump(profile_record_values))
            self.assertEqual(load_retarget_profile(profile_source_path), profile_record_values)
            for invalid_profile_values in [dict(profile_record_values, unknown=True), dict(profile_record_values, root_joint=9), dict(profile_record_values, segments=profile_record_values['segments'] * 2), dict(profile_record_values, coordinate_matrix=[[1, 0, 0], [0, 2, 0], [0, 0, 1]])]:
                profile_source_path.write_text(yaml.safe_dump(invalid_profile_values))
                with self.assertRaises(ValueError):
                    load_retarget_profile(profile_source_path)
            profile_source_path.write_text('schema_version: 1\nschema_version: 1\n')
            with self.assertRaisesRegex(ValueError, '중복'):
                load_retarget_profile(profile_source_path)

    def test_registered_rig_profiles_bind(self):
        profile_record_values = load_retarget_profile(REPOSITORY_ROOT_PATH / 'generators/momask/config/humanml22-anny-retarget.yaml')
        for current_rig_version in ('v1', 'v4'):
            rig_archive_values = np.load(REPOSITORY_ROOT_PATH / f'assets/animation-models/anny-neutral-{current_rig_version}/anny-rest-rig.npz')
            rest_position_values = {current_bone_name: Vector(current_matrix_values[:3, 3]) for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
            rest_rotation_values = {current_bone_name: Matrix(current_matrix_values.tolist()).to_quaternion() for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
            current_solver_value = PositionRetargetSolver(profile_record_values, rest_position_values, rest_rotation_values)
            self.assertEqual(len(current_solver_value.segment_binding_values), 22)

    def test_registered_motions_preserve_directions(self):
        profile_record_values = load_retarget_profile(REPOSITORY_ROOT_PATH / 'generators/momask/config/humanml22-anny-retarget.yaml')
        rig_archive_values = np.load(REPOSITORY_ROOT_PATH / 'assets/animation-models/anny-neutral-v4/anny-rest-rig.npz')
        rest_position_values = {current_bone_name: Vector(current_matrix_values[:3, 3]) for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
        rest_rotation_values = {current_bone_name: Matrix(current_matrix_values.tolist()).to_quaternion() for current_bone_name, current_matrix_values in zip(rig_archive_values['bone_names'], rig_archive_values['bone_matrices'])}
        for current_motion_name in ('momask-standing-v8', 'momask-walking-v9', 'momask-stretch-v1'):
            source_joint_frames = np.load(REPOSITORY_ROOT_PATH / 'assets/motion-sheet' / current_motion_name / 'motion.npz')['joints'] @ np.asarray(profile_record_values['coordinate_matrix']).T
            current_solver_value = PositionRetargetSolver(profile_record_values, rest_position_values, rest_rotation_values)
            for current_joint_points in source_joint_frames:
                _, current_diagnostic_values = current_solver_value.calculate_frame_rotations(current_joint_points)
                self.assertLess(max(current_segment_values['direction_error_degrees'] for current_segment_values in current_diagnostic_values.values()), .001, current_motion_name)


if __name__ == '__main__':
    unittest.main()
