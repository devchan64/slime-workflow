"""기존 타일 import 경로가 공용 구현을 그대로 연결하는지 검증한다."""
import unittest

from generators.terrain import tile_border_crop
from tools.review.common import image_edges, image_borders


class TileBorderCompatibilityTests(unittest.TestCase):
    def test_legacy_functions_reference_shared_implementation(self):
        for function_export_name in ('detect_texture_boundary', 'trace_black_border', 'scan_border_transition', 'render_texture_boundary'):
            self.assertIs(getattr(tile_border_crop, function_export_name), getattr(image_edges, function_export_name))
        for function_export_name in ('crop_traced_tile', 'crop_border_contour', 'crop_inner_border'):
            self.assertIs(getattr(tile_border_crop, function_export_name), getattr(image_borders, function_export_name))
