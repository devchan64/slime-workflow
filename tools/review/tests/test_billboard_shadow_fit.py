"""이미지의 투명 여백·표시 배율과 그림자 제안의 관계를 검증한다."""
import io
import unittest
from PIL import Image
from tools.review.common.billboard_shadow_fit import calculate_image_shadow_size

class BillboardShadowFitTests(unittest.TestCase):
    def test_transparent_padding_preserves_visible_width(self):
        for current_canvas_size,current_display_height in ((100,100),(200,200)):
            current_image_buffer=io.BytesIO()
            current_test_image=Image.new('RGBA',(current_canvas_size,current_canvas_size))
            current_test_image.paste((10,20,30,255),(10,10,90,90))
            current_test_image.save(current_image_buffer,format='PNG');current_image_buffer.seek(0)
            self.assertEqual(calculate_image_shadow_size(current_image_buffer,current_display_height),(.42,.42))
    def test_empty_image_rejected(self):
        current_image_buffer=io.BytesIO();Image.new('RGBA',(20,20)).save(current_image_buffer,format='PNG');current_image_buffer.seek(0)
        with self.assertRaisesRegex(ValueError,'영역'):calculate_image_shadow_size(current_image_buffer,100)
