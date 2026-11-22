"""자동 검출은 원본을 변경하지 않고 검수할 좌표만 반환한다."""
import base64
from io import BytesIO
import unittest
from PIL import Image, ImageDraw
from workflow.common.management_gateway import execute_management_command
from workflow.domains.character_animation.sprite_sheet_auto import execute_sprite_sheet_automatic


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
        import json,subprocess
        from pathlib import Path
        current_source_image=Image.new('RGB',(100,100),'white')
        ImageDraw.Draw(current_source_image).rectangle((20,20,59,79),fill='brown')
        image=encode_test_sprite_image(current_source_image)
        result=execute_sprite_sheet_automatic({'image':image,'padding':50})
        script="""import {cropCandidate,confirmCropCandidate} from './gui/spriteCropCandidate.mjs';
          import assert from 'node:assert/strict';const {image,result}=JSON.parse(process.argv[1]);
          const reviewed=cropCandidate(image,50,result);assert.deepEqual(confirmCropCandidate(reviewed,image,50),result);
          assert.throws(()=>confirmCropCandidate(reviewed,image,40),/변경/);
          assert.throws(()=>confirmCropCandidate(reviewed,image+'A',50),/변경/);
          assert.throws(()=>cropCandidate(image,50,{frames:[],sourceFrames:[]}),/확인/);"""
        root=Path(__file__).resolve().parents[2]
        process=subprocess.run(['node','--input-type=module','-e',script,json.dumps({'image':image,'result':result})],cwd=root,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)

    def test_variable_figures_export_row_heights_without_scaling(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from workflow.domains.character_animation.sprite_sheet_editor import execute_sprite_sheet_export
        current_source_image=Image.new('RGB',(300,300),'white')
        current_draw_context=ImageDraw.Draw(current_source_image)
        for current_rectangle_bounds in [(40,40,79,99),(180,40,239,79),(40,180,69,229),(180,180,229,249)]:
            current_draw_context.rectangle(current_rectangle_bounds,fill='brown')
        current_encoded_image=encode_test_sprite_image(current_source_image)
        current_detected_record=execute_sprite_sheet_automatic({'image':current_encoded_image,'padding':30})
        self.assertEqual({(current_frame_record['width'],current_frame_record['height']) for current_frame_record in current_detected_record['frames']},{(120,120),(120,130)})
        self.assertEqual([current_frame_record['height'] for current_frame_record in current_detected_record['frames']],[120,120,130,130])
        with TemporaryDirectory() as current_temp_directory:
            with patch('workflow.domains.character_animation.sprite_sheet_editor.SPRITE_SHEET_JOB_ROOT',Path(current_temp_directory)):
                current_export_record=execute_sprite_sheet_export({'image':current_encoded_image,'frames':current_detected_record['frames'],'sourceFrames':current_detected_record['sourceFrames'],'columns':2})
        self.assertEqual(current_export_record['coordinates']['sheet'],{'width':240,'height':250})
        self.assertEqual([(current_frame_record['rect']['x'],current_frame_record['rect']['y']) for current_frame_record in current_export_record['coordinates']['frames']],[(0,0),(120,0),(0,120),(120,120)])
        current_export_image=Image.open(BytesIO(base64.b64decode(current_export_record['image']))).convert('RGB')
        self.assertEqual(sum(current_pixel_value==(165,42,42) for current_pixel_value in current_export_image.getdata()),9800)
