"""Blender 런타임에서 체인 입력 거절과 방향·길이 전달을 검증한다."""
import unittest
try:
    import bpy
    from mathutils import Vector
except ImportError as current_import_error:
    raise unittest.SkipTest('Blender Python 런타임에서 실행해야 합니다.') from current_import_error
from generators.hy_motion.arm_chain_transfer import align_arm_segment, apply_arm_directions, redistribute_segment_twist


class ArmChainTransferTest(unittest.TestCase):
    def test_twist_invalid_parameters_rejected(self):
        for current_angle_value, current_share_value in ((float('nan'), .5), (.2, -.1), (.2, 1.1), (True, .5)):
            with self.assertRaises(ValueError):
                redistribute_segment_twist(None, ['start', 'middle', 'end'], current_angle_value, current_share_value)

    def test_compensated_twist_preserves_endpoint_and_rotation(self):
        current_armature_data = bpy.data.armatures.new('test_compensated_data')
        current_armature_object = bpy.data.objects.new('test_compensated_rig', current_armature_data)
        bpy.context.collection.objects.link(current_armature_object)
        bpy.context.view_layer.objects.active = current_armature_object
        current_armature_object.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            current_parent_bone = None
            for current_bone_name, current_bone_head, current_bone_tail in (('start', (0, 0, 0), (.1, .5, 0)), ('middle', (.1, .5, 0), (0, 1, 0)), ('end', (0, 1, 0), (0, 1.5, 0))):
                current_edit_bone = current_armature_data.edit_bones.new(current_bone_name)
                current_edit_bone.head, current_edit_bone.tail = current_bone_head, current_bone_tail
                current_edit_bone.parent = current_parent_bone
                current_parent_bone = current_edit_bone
            bpy.ops.object.mode_set(mode='POSE')
            for current_angle_value in (-.35, 0, .35):
                for current_share_value in (0, .5, 1):
                    current_reference_point = current_armature_object.pose.bones['end'].head.copy()
                    current_reference_rotation = current_armature_object.pose.bones['end'].matrix.to_quaternion().to_matrix()
                    current_result_record = redistribute_segment_twist(current_armature_object, ['start', 'middle', 'end'], current_angle_value, current_share_value)
                    self.assertLess(current_result_record['endpoint_error_m'], 1e-5)
                    self.assertLess(current_result_record['downstream_rotation_matrix_error'], 1e-5)
                    self.assertLess((current_armature_object.pose.bones['end'].head - current_reference_point).length, 1e-5)
                    self.assertLess(max(abs(current_armature_object.pose.bones['end'].matrix.to_quaternion().to_matrix()[current_row_index][current_column_index] - current_reference_rotation[current_row_index][current_column_index]) for current_row_index in range(3) for current_column_index in range(3)), 1e-5)
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.objects.remove(current_armature_object, do_unlink=True)
            bpy.data.armatures.remove(current_armature_data)

    def test_chain_contract_rejected_before_mutation(self):
        with self.assertRaises(ValueError):
            apply_arm_directions(None, ['a', 'b'], ['a', 'b', 'c'], [[0, 0, 0]] * 3)

    def test_nonfinite_points_rejected_before_mutation(self):
        with self.assertRaises(ValueError):
            apply_arm_directions(None, list('abcdefg'), ['c', 'e', 'g'], [[float('nan'), 0, 0]] * 3)

    def test_direction_and_length_on_real_blender_chain(self):
        current_armature_data = bpy.data.armatures.new('test_transfer_data')
        current_armature_object = bpy.data.objects.new('test_transfer_rig', current_armature_data)
        bpy.context.collection.objects.link(current_armature_object)
        bpy.context.view_layer.objects.active = current_armature_object
        current_armature_object.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            current_parent_bone = current_armature_data.edit_bones.new('start')
            current_parent_bone.head, current_parent_bone.tail = (0, 0, 0), (0, 1, 0)
            current_child_bone = current_armature_data.edit_bones.new('end')
            current_child_bone.head, current_child_bone.tail = (0, 1, 0), (0, 2, 0)
            current_child_bone.parent = current_parent_bone
            bpy.ops.object.mode_set(mode='POSE')
            align_arm_segment(current_armature_object, 'start', 'end', (1, 0, 0))
            self.assertLess((current_armature_object.pose.bones['end'].head - Vector((1, 0, 0))).length, 1e-5)
            with self.assertRaises(ValueError):
                align_arm_segment(current_armature_object, 'start', 'end', (0, 0, 0))
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.objects.remove(current_armature_object, do_unlink=True)
            bpy.data.armatures.remove(current_armature_data)
