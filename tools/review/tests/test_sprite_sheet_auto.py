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

    def test_reload_updates_rows_and_clears_previous_results(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.ui.gradio.sprite_sheet_editor_app import prepare_sprite_sheet_load, confirm_sprite_sheet_load
        with TemporaryDirectory() as current_temp_directory:
            current_input_path=Path(current_temp_directory)/'input.png'
            Image.new('RGB',(400,600),'white').save(current_input_path)
            current_first_result=prepare_sprite_sheet_load(str(current_input_path),4,2,'',{})
            self.assertEqual(len(current_first_result[1]),8)
            current_pending_result=prepare_sprite_sheet_load(str(current_input_path),4,3,current_first_result[0],{})
            self.assertEqual(current_pending_result[5]['visible'],True)
            current_loaded_result=confirm_sprite_sheet_load(current_pending_result[6],str(current_input_path),4,3,{})
            self.assertEqual(len(current_loaded_result[1]),12)
            self.assertEqual(current_loaded_result[1][0][3],200)
            self.assertEqual(current_loaded_result[9],{})
            self.assertIsNone(current_loaded_result[10])
            self.assertIsNone(current_loaded_result[12])

    def test_variable_figures_export_row_heights_without_scaling(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from tools.review.domains.character_animation.sprite_sheet_editor import execute_sprite_sheet_export
        current_source_image=Image.new('RGB',(300,300),'white')
        current_draw_context=ImageDraw.Draw(current_source_image)
        for current_rectangle_bounds in [(40,40,79,99),(180,40,239,79),(40,180,69,229),(180,180,229,249)]:
            current_draw_context.rectangle(current_rectangle_bounds,fill='brown')
        current_encoded_image=encode_test_sprite_image(current_source_image)
        current_detected_record=execute_sprite_sheet_automatic({'image':current_encoded_image,'padding':30})
        self.assertEqual({(current_frame_record['width'],current_frame_record['height']) for current_frame_record in current_detected_record['frames']},{(120,120),(120,130)})
        self.assertEqual([current_frame_record['height'] for current_frame_record in current_detected_record['frames']],[120,120,130,130])
        with TemporaryDirectory() as current_temp_directory:
            with patch('tools.review.domains.character_animation.sprite_sheet_editor.SPRITE_SHEET_JOB_ROOT',Path(current_temp_directory)):
                current_export_record=execute_sprite_sheet_export({'image':current_encoded_image,'frames':current_detected_record['frames'],'sourceFrames':current_detected_record['sourceFrames'],'columns':2})
        self.assertEqual(current_export_record['coordinates']['sheet'],{'width':240,'height':250})
        self.assertEqual([(current_frame_record['rect']['x'],current_frame_record['rect']['y']) for current_frame_record in current_export_record['coordinates']['frames']],[(0,0),(120,0),(0,120),(120,120)])
        current_export_image=Image.open(BytesIO(base64.b64decode(current_export_record['image']))).convert('RGB')
        self.assertEqual(sum(current_pixel_value==(165,42,42) for current_pixel_value in current_export_image.getdata()),9800)
