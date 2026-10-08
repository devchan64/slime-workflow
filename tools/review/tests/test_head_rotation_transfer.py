"""중립 머리·원본 회전 보존 및 비회전 입력 거절을 검증한다."""
import unittest
import numpy as np
import json
import tempfile
from pathlib import Path
from generators.hy_motion.head_rotation_transfer import transfer_head_rotation
from generators.hy_motion.head_rotation_transfer import load_head_motion_rotations


class HeadMotionInputTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_reference_path = Path(self.current_temp_directory.name)
        self.current_motion_path = self.current_reference_path / 'motion.npz'
        current_joint_names = [f'joint_{current_joint_index}' for current_joint_index in range(52)]
        current_joint_names[15] = 'Head'
        current_rest_points = np.arange(156, dtype=np.float32).reshape(52, 3) / 100
        current_parent_indices = np.zeros(52, dtype=np.int32)
        current_parent_indices[0] = -1
        (self.current_reference_path / 'joint_names.json').write_text(json.dumps(current_joint_names))
        (self.current_reference_path / 'j_template.bin').write_bytes(current_rest_points.tobytes())
        (self.current_reference_path / 'kintree.bin').write_bytes(current_parent_indices.tobytes())
        current_world_points = current_rest_points[None].copy()
        self.current_motion_arrays = {'fps': np.array(30), 'keypoints3d': current_world_points.copy(), 'world_joints': current_world_points, 'rot6d': np.tile(np.eye(3, dtype=np.float32)[:, :2].reshape(6), (1, 22, 1)), 'transl': np.zeros((1, 3), dtype=np.float32), 'root_rotations_mat': np.eye(3, dtype=np.float32)[None], 'latent_denorm': np.zeros((1, 201), dtype=np.float32)}

    def test_valid_source_returns_verified_head(self):
        np.savez(self.current_motion_path, **self.current_motion_arrays)
        current_head_rotations, current_source_record = load_head_motion_rotations(self.current_motion_path, 1, source_reference_directory=self.current_reference_path)
        np.testing.assert_allclose(current_head_rotations, np.eye(3)[None], atol=1e-7)
        self.assertLess(current_source_record['fk_error_m'], 1e-5)
        self.assertEqual(len(current_source_record['motion_sha256']), 64)

    def test_frame_count_mismatch_is_rejected(self):
        np.savez(self.current_motion_path, **self.current_motion_arrays)
        with self.assertRaises(ValueError):
            load_head_motion_rotations(self.current_motion_path, 2, source_reference_directory=self.current_reference_path)

    def test_invalid_fps_and_unknown_field_are_rejected(self):
        for current_changed_fields in ({'fps': np.array(24)}, {'fps': np.array(True)}, {'unknown': np.array(1)}):
            np.savez(self.current_motion_path, **{**self.current_motion_arrays, **current_changed_fields})
            with self.assertRaises(ValueError):
                load_head_motion_rotations(self.current_motion_path, 1, source_reference_directory=self.current_reference_path)

    def test_fk_mismatch_is_rejected(self):
        self.current_motion_arrays['world_joints'][0, 15, 0] += .1
        np.savez(self.current_motion_path, **self.current_motion_arrays)
        with self.assertRaisesRegex(ValueError, 'FK'):
            load_head_motion_rotations(self.current_motion_path, 1, source_reference_directory=self.current_reference_path)


class HeadRotationTransferTests(unittest.TestCase):
    def test_blender_head_preserves_center_and_parent(self):
        try:
            import bpy
        except ImportError:
            self.skipTest('Blender 런타임이 필요합니다.')
        from generators.hy_motion.head_rotation_transfer import apply_head_rotation
        current_armature_data = bpy.data.armatures.new('head_transfer_test_rig')
        current_rig_object = bpy.data.objects.new('head_transfer_test_object', current_armature_data)
        bpy.context.collection.objects.link(current_rig_object)
        bpy.context.view_layer.objects.active = current_rig_object
        current_rig_object.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        current_neck_bone = current_armature_data.edit_bones.new('neck')
        current_neck_bone.head, current_neck_bone.tail = (0, 0, 0), (0, 0, 1)
        current_head_bone = current_armature_data.edit_bones.new('head')
        current_head_bone.head, current_head_bone.tail = (0, 0, 1), (0, 0, 2)
        current_head_bone.parent = current_neck_bone
        current_head_bone.use_connect = True
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            current_parent_pose = current_rig_object.pose.bones['neck']
            current_parent_pose.rotation_mode = 'XYZ'
            current_parent_pose.rotation_euler.x = .3
            bpy.context.view_layer.update()
            current_parent_matrix = np.asarray(current_parent_pose.matrix_basis).copy()
            current_result_metrics = apply_head_rotation(current_rig_object, np.eye(3))
            self.assertLess(current_result_metrics['head_center_error_m'], 1e-5)
            self.assertLess(current_result_metrics['head_rotation_matrix_error'], 1e-5)
            np.testing.assert_allclose(np.asarray(current_parent_pose.matrix_basis), current_parent_matrix)
        finally:
            bpy.data.objects.remove(current_rig_object, do_unlink=True)
            bpy.data.armatures.remove(current_armature_data)

    def test_neutral_head_preserves_bind_rotation(self):
        current_bind_rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        np.testing.assert_allclose(transfer_head_rotation(np.eye(3), current_bind_rotation), current_bind_rotation)

    def test_source_rotation_delta_is_preserved(self):
        current_source_rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        current_bind_rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        current_target_rotation = transfer_head_rotation(current_source_rotation, current_bind_rotation)
        np.testing.assert_allclose(current_target_rotation @ current_bind_rotation.T, current_source_rotation)

    def test_invalid_rotations_are_rejected(self):
        for current_invalid_matrix in (np.diag([-1, 1, 1]), np.zeros((3, 3)), np.full((3, 3), np.nan)):
            with self.assertRaises(ValueError):
                transfer_head_rotation(current_invalid_matrix, np.eye(3))
            with self.assertRaises(ValueError):
                transfer_head_rotation(np.eye(3), current_invalid_matrix)
