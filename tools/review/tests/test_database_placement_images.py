"""DB 맵 이미지 검증이 파일 카탈로그 대신 지정 버전을 사용한다."""
from io import BytesIO
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.domains.map_assets.placement import validate_registered_scenery_images


class DatabasePlacementImageTests(unittest.TestCase):
    def test_unlisted_database_image_uses_exact_hash(self):
        current_image_stream=BytesIO()
        Image.new('RGBA',(16,16),(0,128,0,255)).save(current_image_stream,format='PNG')
        current_object_records=[{'id':'new-tree','kind':'decoration','textureKey':'new-tree','position':{'column':3,'row':3}}]
        current_property_catalog={'new-tree':{'displayHeight':16,'anchorX':0,'anchorY':0,
            'billboardAnchorMode':'tile-intersection','groundFootprintColumns':1,'groundFootprintRows':1}}
        with patch('tools.review.common.map_tile_assets.load_registered_tiles',side_effect=AssertionError('파일 카탈로그 접근 금지')), patch(
                'tools.review.domains.map_assets.database_images.read_database_published_image',return_value=(current_image_stream.getvalue(),'image/png')) as current_image_reader:
            validate_registered_scenery_images(current_object_records,current_property_catalog,80,40,[[0]*8 for current_row_index in range(8)],.5,{'new-tree':{'sha256':'a'*64}})
            current_image_reader.assert_called_once_with('a'*64)
            with self.assertRaisesRegex(ValueError,'등록 누락'):
                validate_registered_scenery_images(current_object_records,current_property_catalog,80,40,[[0]*8 for current_row_index in range(8)],.5,{})
