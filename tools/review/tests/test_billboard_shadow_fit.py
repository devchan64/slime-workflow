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
            self.assertEqual(calculate_image_shadow_size(current_image_buffer,current_display_height),(.53,.53))
    def test_empty_image_rejected(self):
        current_image_buffer=io.BytesIO();Image.new('RGBA',(20,20)).save(current_image_buffer,format='PNG');current_image_buffer.seek(0)
        with self.assertRaisesRegex(ValueError,'영역'):calculate_image_shadow_size(current_image_buffer,100)

    def test_actual_renderer_width_matches_target(self):
        import json
        import subprocess
        from pathlib import Path
        current_renderer_uri=(Path(__file__).resolve().parents[3]/'tools/review/ui/map/vendor/field-renderer/field-renderer.mjs').as_uri()
        for current_columns_count,current_rows_count in ((1,1),(1,2),(2,1)):
            current_image_buffer=io.BytesIO()
            Image.new('RGBA',(116,82),(10,20,30,255)).save(current_image_buffer,format='PNG')
            current_image_buffer.seek(0)
            current_shadow_columns,current_shadow_rows=calculate_image_shadow_size(current_image_buffer,64.06,current_columns_count,current_rows_count)
            current_property_record=dict(groundFootprintColumns=current_columns_count,groundFootprintRows=current_rows_count,displayHeight=64.06,billboardAnchorMode='tile-intersection',anchorX=0,anchorY=0,shadowScaleX=current_shadow_columns,shadowScaleY=current_shadow_rows)
            current_script_text='''
import {drawBillboardContactShadow} from MODULE_URI;
const currentPolygonRecords=[];
const currentMockScene={add:{graphics:()=>({setDepth(){return this},fillStyle(){},fillPoints(currentPolygonPoints){currentPolygonRecords.push(currentPolygonPoints)}})}};
drawBillboardContactShadow(currentMockScene,PROPERTY_RECORD,{x:0,y:0},0,{tileWidth:160,tileHeight:80});
const currentHorizontalValues=currentPolygonRecords[0].map(currentPointValue=>currentPointValue.x);
console.log(Math.max(...currentHorizontalValues)-Math.min(...currentHorizontalValues));
'''.replace('MODULE_URI',json.dumps(current_renderer_uri)).replace('PROPERTY_RECORD',json.dumps(current_property_record))
            current_rendered_width=float(subprocess.run(['node','--input-type=module','-e',current_script_text],check=True,capture_output=True,text=True).stdout)
            self.assertAlmostEqual(current_rendered_width,116*64.06/82*.95,delta=1)
