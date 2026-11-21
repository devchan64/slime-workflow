import math
import unittest
from generators.momask.camera_settings import normalize_camera_angles, camera_projection_angles, camera_direction_positions


class CameraSettingsTests(unittest.TestCase):
    def test_45_degree_quadrants(self):
        self.assertEqual(camera_projection_angles(45), {'down_left':45,'down_right':315,'up_left':135,'up_right':225})
        for direction, position in camera_direction_positions(45).items():
            self.assertAlmostEqual(abs(position[0]),math.sqrt(26))
            self.assertAlmostEqual(abs(position[1]),math.sqrt(26))
            self.assertEqual(position[0]>0,direction.endswith('left'))
            self.assertEqual(position[1]>0,direction.startswith('up'))

    def test_each_direction_is_independent(self):
        angles=normalize_camera_angles(45)
        angles['up_left']=150
        self.assertEqual(camera_projection_angles(angles),{'down_left':45,'down_right':315,'up_left':150,'up_right':225})
        self.assertEqual(camera_direction_positions(angles)['down_left'],camera_direction_positions(45)['down_left'])

    def test_rejects_missing_and_invalid_angles(self):
        for angles in ({'down_left':45},float('nan'),0,90,True):
            with self.assertRaises(ValueError):normalize_camera_angles(angles)
