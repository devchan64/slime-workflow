"""Blender 런타임에서 공식 셰이딩 노드와 포즈 보존을 검증한다."""
import importlib.util
import unittest
from generators.hy_motion.official_shading import apply_official_shading, OFFICIAL_SHADING_VERSION


@unittest.skipUnless(importlib.util.find_spec('bpy'), 'Blender Python 런타임에서 실행')
class OfficialShadingContractTests(unittest.TestCase):
    def test_material_and_pose_preservation(self):
        import bpy
        bpy.ops.wm.read_factory_settings(use_empty=False)
        current_body_object = bpy.data.objects['Cube']
        current_render_scene = bpy.context.scene
        current_body_object.location = (1, 2, 3)
        current_camera_matrix = current_render_scene.camera.matrix_world.copy()
        current_vertex_positions = [tuple(current_mesh_vertex.co) for current_mesh_vertex in current_body_object.data.vertices]
        current_shading_record = apply_official_shading(current_render_scene, current_body_object)
        self.assertEqual(current_shading_record['profile'], OFFICIAL_SHADING_VERSION)
        self.assertFalse(current_shading_record['pixel_equivalence'])
        self.assertEqual(tuple(current_body_object.location), (1, 2, 3))
        self.assertEqual(current_render_scene.camera.matrix_world, current_camera_matrix)
        self.assertEqual([tuple(current_mesh_vertex.co) for current_mesh_vertex in current_body_object.data.vertices], current_vertex_positions)
        self.assertEqual(current_render_scene.view_settings.view_transform, 'Standard')
        self.assertEqual(len(current_body_object.data.materials), 1)
        current_material_nodes = current_body_object.data.materials[0].node_tree.nodes
        current_transform_node = next(current_shader_node for current_shader_node in current_material_nodes if current_shader_node.type == 'VECT_TRANSFORM')
        self.assertEqual(current_transform_node.convert_to, 'CAMERA')
        self.assertEqual(current_transform_node.vector_type, 'NORMAL')
        self.assertTrue(any(current_shader_node.type == 'EMISSION' for current_shader_node in current_material_nodes))
        self.assertFalse(any(current_shader_node.type == 'BSDF_PRINCIPLED' for current_shader_node in current_material_nodes))


if __name__ == '__main__':
    unittest.main()
