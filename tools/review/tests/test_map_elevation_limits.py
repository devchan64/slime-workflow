"""두 자리 고도 원본과 기존 문자열 맵의 호환성을 확인한다."""
import unittest
from tools.review.common.map_asset_sources import normalize_field_surface_data

class MapElevationLimitTests(unittest.TestCase):
    def test_numeric_height_roundtrip(self):
        current_map_record=dict(columns=3,rows=1,elevations=[[10,19,20]],terrainMovementVersion=2)
        normalize_field_surface_data(current_map_record)
        self.assertEqual(current_map_record['elevations'],[[10,19,20]])

    def test_legacy_height_compatibility(self):
        current_map_record=dict(columns=3,rows=1,elevations=['019'],terrainMovementVersion=2)
        normalize_field_surface_data(current_map_record)
        self.assertEqual(current_map_record['elevations'],[[0,1,9]])

    def test_invalid_height_rejected(self):
        for current_invalid_value in (21,-1,True,20.0,'20'):
            with self.subTest(value=current_invalid_value), self.assertRaises(ValueError):
                normalize_field_surface_data(dict(columns=1,rows=1,elevations=[[current_invalid_value]],terrainMovementVersion=2))
