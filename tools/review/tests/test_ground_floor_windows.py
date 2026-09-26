"""1층 창문 간격 규칙을 검증한다."""
import unittest

from tools.review.build_map_review import select_floor_wall_texture


class GroundFloorWindowTests(unittest.TestCase):
    def test_ground_floor_places_small_windows_at_odd_door_distances(self):
        default_wall_texture = object()
        plain_wall_texture = object()
        small_window_wall_texture = object()
        large_window_wall_texture = object()

        self.assertIs(select_floor_wall_texture(0, 0, 0, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), plain_wall_texture)
        self.assertIs(select_floor_wall_texture(0, 1, 0, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)
        self.assertIs(select_floor_wall_texture(0, 2, 0, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), plain_wall_texture)
        self.assertIs(select_floor_wall_texture(0, 3, 0, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)

    def test_ground_floor_applies_window_spacing_to_every_wall_face(self):
        default_wall_texture = object()
        plain_wall_texture = object()
        small_window_wall_texture = object()
        large_window_wall_texture = object()

        self.assertIs(select_floor_wall_texture(0, 0, 1, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)
        self.assertIs(select_floor_wall_texture(0, 1, 1, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), plain_wall_texture)
        self.assertIs(select_floor_wall_texture(0, 2, 1, default_wall_texture, plain_wall_texture, small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)

    def test_upper_floors_alternate_small_and_large_windows(self):
        default_wall_texture = object()
        small_window_wall_texture = object()
        large_window_wall_texture = object()
        self.assertIs(select_floor_wall_texture(1, 0, 0, default_wall_texture, object(), small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)
        self.assertIs(select_floor_wall_texture(1, 1, 0, default_wall_texture, object(), small_window_wall_texture, large_window_wall_texture), large_window_wall_texture)
        self.assertIs(select_floor_wall_texture(2, 2, 0, default_wall_texture, object(), small_window_wall_texture, large_window_wall_texture), small_window_wall_texture)
