"""자동 검출은 원본을 변경하지 않고 검수할 좌표만 반환한다."""
import base64
from io import BytesIO
import unittest
from PIL import Image, ImageDraw
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.character_animation.sprite_sheet_auto import execute_sprite_sheet_automatic


def encode_test_sprite_image(current_source_image):
    current_output_stream=BytesIO()
    current_source_image.save(current_output_stream,format='PNG')
    return base64.b64encode(current_output_stream.getvalue()).decode()


class AutomaticSpriteCropTests(unittest.TestCase):
    def test_detect_grid_and_default_padding(self):
        current_source_image=Image.new('RGB',(300,300),'white')
        current_draw_context=ImageDraw.Draw(current_source_image)
        current_draw_context.rectangle((0,0,299,5),fill='black')
        for current_left_pixels,current_top_pixels in [(40,40),(180,40),(40,180),(180,180)]:
            current_draw_context.rectangle((current_left_pixels,current_top_pixels,current_left_pixels+39,current_top_pixels+59),fill='brown')
        current_result_record=execute_management_command('character-animation','sheet-auto',{'image':encode_test_sprite_image(current_source_image)})
        self.assertEqual(current_result_record['columns'],2)
        self.assertEqual(current_result_record['rows'],2)
        self.assertEqual(current_result_record['frames'][0],dict(x=10,y=10,width=100,height=120,anchorX=50,anchorY=89))
        self.assertNotIn('image',current_result_record)

    def test_transparent_background(self):
        current_source_image=Image.new('RGBA',(100,100),(0,0,0,0))
        ImageDraw.Draw(current_source_image).rectangle((20,20,59,79),fill='brown')
        current_result_record=execute_sprite_sheet_automatic({'image':encode_test_sprite_image(current_source_image),'padding':0})
        self.assertEqual(current_result_record['sourceFrames'],[[20,20,40,60]])

    def test_invalid_inputs_and_empty_background(self):
        current_encoded_image=encode_test_sprite_image(Image.new('RGB',(100,100),'white'))
        for current_bad_padding in [-1,501,True,1.5]:
            with self.assertRaises(ValueError):
                execute_sprite_sheet_automatic({'image':current_encoded_image,'padding':current_bad_padding})
        with self.assertRaises(ValueError):
            execute_sprite_sheet_automatic({'image':current_encoded_image})
        with self.assertRaises(ValueError):
            execute_sprite_sheet_automatic({'image':current_encoded_image,'unknown':1})

    def test_review_rejects_changed_input(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from tools.review.ui.gradio.sprite_sheet_editor_app import detect_automatic_sprite_crops, apply_automatic_sprite_crops
        current_source_image=Image.new('RGB',(100,100),'white')
        ImageDraw.Draw(current_source_image).rectangle((20,20,59,79),fill='brown')
        with TemporaryDirectory() as current_temp_directory:
            current_input_path=Path(current_temp_directory)/'input.png'
            current_source_image.save(current_input_path)
            with patch('tools.review.ui.gradio.sprite_sheet_editor_app.execute_remote_management_command',side_effect=lambda current_service_name,current_command_name,current_payload_record:execute_sprite_sheet_automatic(current_payload_record)):
                current_pending_record,*_=detect_automatic_sprite_crops('data:image/png;base64,'+encode_test_sprite_image(current_source_image),50)
            current_loaded_values=apply_automatic_sprite_crops(current_pending_record,'data:image/png;base64,'+base64.b64encode(current_input_path.read_bytes()).decode(),50)
            self.assertEqual(len(current_loaded_values[1]),1)
            with self.assertRaises(Exception):
                apply_automatic_sprite_crops(current_pending_record,'data:image/png;base64,'+encode_test_sprite_image(current_source_image),40)
            Image.new('RGB',(100,100),'red').save(current_input_path)
            with self.assertRaises(Exception):
                apply_automatic_sprite_crops(current_pending_record,'data:image/png;base64,'+base64.b64encode(current_input_path.read_bytes()).decode(),50)
