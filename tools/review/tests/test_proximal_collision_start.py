"""리그에서 유도한 바깥 방향·안전 시작점·실패 복원을 검증한다."""
import unittest
import numpy as np
try:
    import bpy
except ImportError:
    raise unittest.SkipTest('Blender 런타임이 필요합니다.')
from generators.hy_motion.proximal_collision_start import initialize_proximal_collision_start


class ProximalCollisionStartTests(unittest.TestCase):
    def setUp(self):
        self.current_armature_data = bpy.data.armatures.new('proximal_test_rig')
        self.current_rig_object = bpy.data.objects.new('proximal_test_object', self.current_armature_data)
        bpy.context.collection.objects.link(self.current_rig_object)
        bpy.context.view_layer.objects.active = self.current_rig_object
        self.current_rig_object.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for current_side_name, current_side_sign in (('L', 1), ('R', -1)):
            current_upper_bone = self.current_armature_data.edit_bones.new('upperarm01.' + current_side_name)
            current_upper_bone.head = (.2 * current_side_sign, 0, 1)
            current_upper_bone.tail = (.2 * current_side_sign, 0, .6)
            current_lower_bone = self.current_armature_data.edit_bones.new('lowerarm01.' + current_side_name)
            current_lower_bone.head = current_upper_bone.tail
            current_lower_bone.tail = (.2 * current_side_sign, 0, .3)
            current_lower_bone.parent = current_upper_bone
            current_lower_bone.use_connect = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.update()

    def tearDown(self):
        bpy.data.objects.remove(self.current_rig_object, do_unlink=True)
        bpy.data.armatures.remove(self.current_armature_data)

    def test_first_clear_pose_uses_rig_axis(self):
        current_result_record = initialize_proximal_collision_start(self.current_rig_object, lambda: self.current_rig_object.pose.bones['lowerarm01.L'].head.x < .3, 2, 10)
        self.assertGreater(current_result_record['fraction'], 0)
        self.assertLess(current_result_record['fraction'], .2)
        self.assertGreaterEqual(self.current_rig_object.pose.bones['lowerarm01.L'].head.x, .3)
        self.assertLessEqual(self.current_rig_object.pose.bones['lowerarm01.R'].head.x, -.3)
        np.testing.assert_allclose(current_result_record['outward_axis'], [1, 0, 0], atol=1e-6)

    def test_already_clear_pose_is_unchanged(self):
        self.current_rig_object.pose.bones['upperarm01.L'].rotation_mode = 'XYZ'
        self.current_rig_object.pose.bones['upperarm01.L'].rotation_euler.z = .3
        bpy.context.view_layer.update()
        current_saved_matrices = {current_pose_bone.name: np.asarray(current_pose_bone.matrix_basis).copy() for current_pose_bone in self.current_rig_object.pose.bones}
        current_result_record = initialize_proximal_collision_start(self.current_rig_object, lambda: False, 2, 10)
        self.assertEqual(current_result_record['fraction'], 0)
        for current_pose_bone in self.current_rig_object.pose.bones:
            np.testing.assert_allclose(np.asarray(current_pose_bone.matrix_basis), current_saved_matrices[current_pose_bone.name], atol=1e-6)

    def test_failed_search_restores_pose(self):
        current_saved_matrices = {current_pose_bone.name: np.asarray(current_pose_bone.matrix_basis).copy() for current_pose_bone in self.current_rig_object.pose.bones}
        with self.assertRaisesRegex(ValueError, '찾지 못'):
            initialize_proximal_collision_start(self.current_rig_object, lambda: True, 10, 4)
        for current_pose_bone in self.current_rig_object.pose.bones:
            np.testing.assert_allclose(np.asarray(current_pose_bone.matrix_basis), current_saved_matrices[current_pose_bone.name], atol=1e-6)

    def test_invalid_step_is_rejected(self):
        with self.assertRaises(ValueError):
            initialize_proximal_collision_start(self.current_rig_object, lambda: False, 0, 10)
