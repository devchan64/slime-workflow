"""테두리 추적·출력 픽셀 환산 및 검출 실패 검증."""
import unittest
from PIL import Image, ImageDraw
from tools.review.common.image_edges import is_black_border, trace_black_border
from tools.review.common.image_borders import crop_traced_tile


class ImageBorderCropTests(unittest.TestCase):
    def test_black_classification_limits(self):
        for pixel_color_value in ((0, 0, 0), (48, 48, 48), (38, 38, 40), (40, 38, 38), (47, 47, 49), (9, 11, 12), (1, 2, 3), (35, 38, 40)):
            self.assertTrue(is_black_border(pixel_color_value))
        for pixel_color_value in ((49, 49, 49), (72, 72, 72), (31, 40, 48), (40, 56, 40), (17, 0, 0), (10, 0, 0), (39, 40, 50), (41, 42, 50), (8, 0, 0), (34, 38, 40), (42, 42, 50)):
            self.assertFalse(is_black_border(pixel_color_value))

    def test_dark_gray_texture_boundary(self):
        source_image_value = self.create_framed_image()
        ImageDraw.Draw(source_image_value).rectangle((16, 20, 111, 107), fill=(60, 60, 60))
        self.assertEqual(trace_black_border(source_image_value).content_crop_bounds, (16, 20, 112, 108))

    def create_framed_image(self):
        source_image_value = Image.new('RGB', (128, 128), 'white')
        source_image_draw = ImageDraw.Draw(source_image_value)
        source_image_draw.rectangle((8, 8, 119, 119), fill='black')
        source_image_draw.rectangle((16, 20, 111, 107), fill=(80, 160, 40))
        return source_image_value

    def test_detects_each_inner_boundary(self):
        self.assertEqual(trace_black_border(self.create_framed_image()).content_crop_bounds, (16, 20, 112, 108))

    def test_keeps_two_output_pixels(self):
        cropped_tile_image, border_trace_result, source_crop_bounds = crop_traced_tile(self.create_framed_image(), output_tile_size=64)
        self.assertEqual(cropped_tile_image.size, (64, 64))
        self.assertAlmostEqual((16-source_crop_bounds[0])*64/(source_crop_bounds[2]-source_crop_bounds[0]), 2)
        self.assertAlmostEqual((20-source_crop_bounds[1])*64/(source_crop_bounds[3]-source_crop_bounds[1]), 2)
        self.assertLess(max(cropped_tile_image.getpixel((0, 32))), 20)
        self.assertGreater(cropped_tile_image.getpixel((4, 32))[1], 140)

    def test_ignores_sparse_content_protrusions(self):
        source_image_value = self.create_framed_image()
        ImageDraw.Draw(source_image_value).rectangle((12, 50, 20, 53), fill=(80, 160, 40))
        self.assertEqual(trace_black_border(source_image_value).content_crop_bounds, (16, 20, 112, 108))

    def test_missing_frame_fails_explicitly(self):
        for source_image_value in (Image.new('RGB', (128, 128), 'white'), Image.new('RGB', (128, 128), 'black')):
            with self.assertRaisesRegex(ValueError, '검출 근거 부족'):
                trace_black_border(source_image_value)

    def test_invalid_output_parameters_fail(self):
        with self.assertRaises(ValueError):
            crop_traced_tile(self.create_framed_image(), output_tile_size=4, retained_edge_pixels=2)

    def test_zero_edge_contour_removes_frame_and_detached_marks(self):
        from tools.review.common.image_borders import crop_border_contour
        source_image_value = self.create_framed_image()
        source_image_draw = ImageDraw.Draw(source_image_value)
        source_image_draw.rectangle((10, 10, 11, 11), fill='white')
        source_image_draw.rectangle((12, 50, 16, 53), fill=(80, 160, 40))
        cropped_tile_image, content_crop_bounds = crop_border_contour(source_image_value, output_tile_size=100)
        self.assertEqual(content_crop_bounds, (12, 20, 112, 108))
        self.assertEqual(cropped_tile_image.mode, 'RGBA')
        self.assertEqual(cropped_tile_image.getpixel((0, 0))[3], 0)
        self.assertEqual(cropped_tile_image.getpixel((50, 50))[3], 255)

    def test_boundary_follows_texture_and_preserves_interior_shadows(self):
        from tools.review.common.image_edges import detect_texture_boundary
        source_image_value = self.create_framed_image()
        source_image_draw = ImageDraw.Draw(source_image_value)
        source_image_draw.rectangle((12, 50, 16, 53), fill=(80, 160, 40))
        source_image_draw.rectangle((50, 50, 55, 55), fill='black')
        original_image_bytes = source_image_value.tobytes()
        boundary_trace_result = detect_texture_boundary(source_image_value)
        self.assertIn((12, 51), boundary_trace_result.texture_boundary_points)
        self.assertIn((16, 30), boundary_trace_result.texture_boundary_points)
        self.assertNotIn((50, 50), boundary_trace_result.texture_boundary_points)
        self.assertEqual(boundary_trace_result.texture_region_mask.getpixel((50, 50)), 255)
        self.assertEqual(boundary_trace_result.black_frame_mask.getpixel((50, 50)), 0)
        self.assertEqual(boundary_trace_result.black_frame_mask.getpixel((10, 30)), 255)
        self.assertEqual(source_image_value.tobytes(), original_image_bytes)
        for boundary_pixel_point in boundary_trace_result.texture_boundary_points:
            self.assertEqual(boundary_trace_result.texture_region_mask.getpixel(boundary_pixel_point), 255)
            self.assertEqual(boundary_trace_result.texture_boundary_mask.getpixel(boundary_pixel_point), 255)

    def test_overlay_marks_detected_boundary_only(self):
        from tools.review.common.image_edges import detect_texture_boundary, render_texture_boundary
        source_image_value = self.create_framed_image()
        boundary_trace_result = detect_texture_boundary(source_image_value)
        boundary_overlay_image = render_texture_boundary(source_image_value, boundary_trace_result)
        self.assertEqual(boundary_overlay_image.getpixel((16, 30)), (255, 40, 40))
        self.assertEqual(boundary_overlay_image.getpixel((50, 50)), source_image_value.getpixel((50, 50)))

    def test_scan_requires_black_before_texture_and_stops_at_first_boundary(self):
        from tools.review.common.image_edges import scan_border_transition
        white_pixel_value = (255, 255, 255)
        black_pixel_value = (0, 0, 0)
        texture_pixel_value = (60, 160, 30)
        self.assertEqual(scan_border_transition([white_pixel_value]*4+[black_pixel_value]*5+[texture_pixel_value]*8+[black_pixel_value]*4), (4, 9))
        self.assertIsNone(scan_border_transition([white_pixel_value]*4+[texture_pixel_value]*8))
        self.assertIsNone(scan_border_transition([black_pixel_value]*8+[white_pixel_value]*4))

    def test_records_outer_black_then_inner_texture_in_each_direction(self):
        from tools.review.common.image_edges import detect_texture_boundary
        boundary_trace_result = detect_texture_boundary(self.create_framed_image())
        self.assertIn(((8, 30), (16, 30)), boundary_trace_result.side_transition_records['left'])
        self.assertIn(((119, 30), (111, 30)), boundary_trace_result.side_transition_records['right'])
        self.assertIn(((30, 8), (30, 20)), boundary_trace_result.side_transition_records['top'])
        self.assertIn(((30, 119), (30, 107)), boundary_trace_result.side_transition_records['bottom'])

    def test_inner_border_uses_innermost_edge_and_rounds_up(self):
        from tools.review.common.image_borders import crop_inner_border
        source_image_value = self.create_framed_image()
        ImageDraw.Draw(source_image_value).rectangle((16, 40, 18, 44), fill='black')
        cropped_tile_image, crop_measurement_record = crop_inner_border(source_image_value)
        self.assertEqual(crop_measurement_record['inner_bounds'], [19, 20, 112, 108])
        self.assertEqual(crop_measurement_record['border_pixels'], [1, 1])
        self.assertEqual(crop_measurement_record['crop_box'], [18, 19, 113, 109])
        self.assertEqual(cropped_tile_image.size, (95, 90))

    def test_inner_window_cannot_replace_missing_outer_edge(self):
        from tools.review.common.image_borders import crop_inner_border
        source_image_value = self.create_framed_image()
        source_drawing_context = ImageDraw.Draw(source_image_value)
        source_drawing_context.rectangle((50, 0, 52, 19), fill='white')
        source_drawing_context.rectangle((50, 45, 52, 85), fill='black')
        source_drawing_context.rectangle((50, 86, 52, 90), fill=(80, 160, 40))
        cropped_image_value, crop_measurement_record = crop_inner_border(source_image_value)
        self.assertEqual(crop_measurement_record['inner_bounds'], [16, 20, 112, 108])
        self.assertEqual(cropped_image_value.size, (98, 90))

    def test_inner_border_rejects_invalid_ratio(self):
        from tools.review.common.image_borders import crop_inner_border
        for invalid_ratio_value in (-0.1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                crop_inner_border(self.create_framed_image(), retained_border_ratio=invalid_ratio_value)

    def test_sensitive_scan_detects_dark_texture_before_bright_texture(self):
        from tools.review.common.image_edges import scan_border_transition
        scan_pixel_values = [(255, 255, 255)]*4+[(20, 20, 20)]*5+[(25, 32, 22)]*3+[(80, 160, 40)]*5
        self.assertEqual(scan_border_transition(scan_pixel_values), (4, 9))

    def test_sensitive_scan_ignores_single_pixel_color_noise(self):
        from tools.review.common.image_edges import scan_border_transition
        scan_pixel_values = [(20, 20, 20)]*5+[(25, 32, 22)]+[(20, 20, 20)]*3+[(80, 160, 40)]*3
        self.assertEqual(scan_border_transition(scan_pixel_values), (0, 9))
