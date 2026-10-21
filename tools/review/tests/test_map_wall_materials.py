"""맵별 벽면 재질 선택 계약을 검증한다."""
import unittest
from tools.review.common.map_asset_sources import validate_map_cliff_texture, load_registered_map_review

class MapWallMaterialTests(unittest.TestCase):
    def test_registered_wall_selection(self):
        self.assertEqual(validate_map_cliff_texture('cliff-wall'),'cliff-wall')
        self.assertEqual(validate_map_cliff_texture('quarry-limestone-wall-v1'),'quarry-limestone-wall-v1')

    def test_invalid_wall_selection(self):
        for current_invalid_key in ('stone', '../wall', '', None, 7):
            with self.subTest(key=current_invalid_key), self.assertRaises(ValueError):
                validate_map_cliff_texture(current_invalid_key)

    def test_quarry_wall_selection(self):
        self.assertEqual(load_registered_map_review('broken-quarry')['cliffTextureKey'],'quarry-limestone-wall-v1')
