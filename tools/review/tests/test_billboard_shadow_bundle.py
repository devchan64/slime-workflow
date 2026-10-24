"""채택 배포본에서도 이미지 높이와 무관한 타일 단위 그림자를 검증한다."""
import subprocess
import unittest
from pathlib import Path

CURRENT_WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


class BillboardShadowBundleTests(unittest.TestCase):
    def test_installed_shadow_uses_tile_lengths(self):
        current_module_uri = (CURRENT_WORKFLOW_ROOT / 'tools/review/ui/map/vendor/field-renderer/field-renderer.mjs').as_uri()
        current_script_text = '''
import assert from 'node:assert/strict';
import {drawBillboardContactShadow} from MODULE_URI;
const currentPolygonRecords=[];
const currentMockScene={add:{graphics:()=>({setDepth(){return this;},fillStyle(){},fillPoints(currentPolygonPoints){currentPolygonRecords.push(currentPolygonPoints);}})}};
for(const currentDisplayHeight of [42.5,87.64]){
 drawBillboardContactShadow(currentMockScene,{displayHeight:currentDisplayHeight,groundFootprintColumns:1,groundFootprintRows:1,shadowScaleX:2,shadowScaleY:2,billboardAnchorMode:'tile-intersection',anchorX:0,anchorY:0},{x:0,y:0},100,{tileWidth:80,tileHeight:40,billboardScale:.5});
}
assert.deepEqual(currentPolygonRecords.slice(0,3),currentPolygonRecords.slice(3));
const currentColumnValues=currentPolygonRecords[0].map(currentPointValue=>currentPointValue.x/80+currentPointValue.y/40);
assert.ok(Math.abs(Math.max(...currentColumnValues)-Math.min(...currentColumnValues)-2)<1e-10);
'''
        import json
        subprocess.run(['node', '--input-type=module', '-e', current_script_text.replace('MODULE_URI', json.dumps(current_module_uri))], check=True, capture_output=True, text=True)
