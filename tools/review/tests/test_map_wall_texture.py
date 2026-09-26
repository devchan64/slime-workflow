"""벽 타일의 방향별 투영과 원본 이미지 사용 검증."""
import unittest
from PIL import Image
from tools.review.build_map_review import paste_projected_wall_texture

class MapWallTextureTests(unittest.TestCase):
    def test_both_wall_faces_preserve_texture_orientation(self):
        wall_texture_image=Image.new('RGBA',(16,16),(240,10,20,255))
        for pixel_column_index in range(8,16):
            for pixel_row_index in range(16):wall_texture_image.putpixel((pixel_column_index,pixel_row_index),(10,220,30,255))
        for top_left_point,top_right_point,bottom_left_point in [((20,10),(40,20),(20,42)),((40,10),(20,20),(40,42))]:
            preview_image=Image.new('RGBA',(64,64))
            paste_projected_wall_texture(preview_image,wall_texture_image,top_left_point,top_right_point,bottom_left_point)
            for horizontal_fraction,expected_pixel_value in [(.25,(240,10,20,255)),(.75,(10,220,30,255))]:
                pixel_position_value=(round(top_left_point[0]+horizontal_fraction*(top_right_point[0]-top_left_point[0])),round(top_left_point[1]+horizontal_fraction*(top_right_point[1]-top_left_point[1])+16))
                self.assertEqual(preview_image.getpixel(pixel_position_value),expected_pixel_value)
            self.assertEqual(preview_image.getpixel((0,0)),(0,0,0,0))
