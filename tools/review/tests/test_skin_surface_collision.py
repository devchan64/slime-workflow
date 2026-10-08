"""실제 Blender 삼각형에서 교차와 정점·표면 수치 여유를 검증한다."""
import unittest
try:
    import bpy
except ImportError:
    raise unittest.SkipTest('Blender 런타임이 필요합니다.')
from generators.hy_motion.skin_collision_barrier import detect_surface_collision


class SkinSurfaceCollisionTests(unittest.TestCase):
    def test_surface_clearance_detects_near_contact(self):
        current_mesh_data = bpy.data.meshes.new('barrier_test_mesh')
        current_mesh_data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0), (.1, .1, .0004), (.5, .1, .0004), (.1, .5, .0004)], [], [(0, 1, 2), (3, 4, 5)])
        current_mesh_object = bpy.data.objects.new('barrier_test_object', current_mesh_data)
        bpy.context.collection.objects.link(current_mesh_object)
        bpy.context.view_layer.update()
        current_partition_faces = {'body': [(0, 1, 2)], 'L': [(3, 4, 5)], 'R': [(3, 4, 5)]}
        try:
            self.assertFalse(detect_surface_collision(current_mesh_object, current_partition_faces, 0))
            self.assertFalse(detect_surface_collision(current_mesh_object, current_partition_faces, .0001))
            self.assertTrue(detect_surface_collision(current_mesh_object, current_partition_faces, .0005))
            current_mesh_data.vertices[3].co.z = -.0004
            current_mesh_data.update()
            bpy.context.view_layer.update()
            self.assertTrue(detect_surface_collision(current_mesh_object, current_partition_faces, 0))
        finally:
            bpy.data.objects.remove(current_mesh_object, do_unlink=True)
            bpy.data.meshes.remove(current_mesh_data)

    def test_invalid_clearance_is_rejected(self):
        for current_clearance_value in (-1, float('nan'), True):
            with self.assertRaises(ValueError):
                detect_surface_collision(None, {}, current_clearance_value)
