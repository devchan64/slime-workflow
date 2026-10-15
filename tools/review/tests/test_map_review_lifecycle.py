"""맵 초기화 실패·화면 이탈 시 렌더러 수명 정리를 검증한다."""
import json
from pathlib import Path
import subprocess
import unittest


class MapReviewLifecycleTests(unittest.TestCase):
    def test_initialization_failure_and_early_exit_destroy_renderer_once(self):
        current_adapter_path=Path(__file__).parents[1]/'ui/map/field-map-view.js'
        current_adapter_source='\n'.join(current_source_line for current_source_line in current_adapter_path.read_text().splitlines() if not current_source_line.startswith('import '))
        current_adapter_source=current_adapter_source.replace('export async function','async function')
        current_script_source=r"""
const assert=require('node:assert/strict');
const TERRAIN_DEPTH={actor:1,overlay:2},GAME_INTERNAL_RESOLUTION_SCALE=2;
const currentEventHandlers=new Map();
const window={addEventListener:(name,callback)=>currentEventHandlers.set(name,callback),removeEventListener:name=>currentEventHandlers.delete(name)};
let currentDestroyCount=0,currentBootCallback,currentFailAtlas=false;
const Phaser={WEBGL:1,Scale:{NONE:0},Game:class{
 constructor(settings){this.scale={};currentBootCallback=()=>settings.scene.create.call({textures:{addImage:()=>({add(){}}),exists:()=>false}});}
 destroy(){currentDestroyCount++;}
}};
const collectTerrainTextureSources=()=>({});
const createTerrainAtlas=()=>{if(currentFailAtlas)throw Error('atlas failure');};
ADAPTER_SOURCE
const currentCanvasElement={clientWidth:100,clientHeight:100,style:{}};
const currentCharacterRecord={frame:{rect:{x:0,y:0,width:1,height:1}}};
const createTestReview=()=>createSharedFieldReview(currentCanvasElement,{}, {},currentCharacterRecord,{}, {},{});
(async()=>{
 currentFailAtlas=true;
 let currentPendingReview=createTestReview();currentBootCallback();
 await assert.rejects(currentPendingReview,/atlas failure/);
 assert.equal(currentDestroyCount,1);assert.equal(currentEventHandlers.size,0);
 currentFailAtlas=false;
 currentPendingReview=createTestReview();
 currentEventHandlers.get('pagehide')();
 await assert.rejects(currentPendingReview,/닫혔습니다/);
 assert.equal(currentDestroyCount,2);assert.equal(currentEventHandlers.size,0);
 currentPendingReview=createTestReview();currentBootCallback();
 const currentReadyReview=await currentPendingReview;
 currentReadyReview.destroy();currentReadyReview.destroy();
 assert.equal(currentDestroyCount,3);assert.equal(currentEventHandlers.size,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace('ADAPTER_SOURCE',current_adapter_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_texture_progress_preserves_failure_during_other_completions(self):
        current_loader_path=Path(__file__).parents[1]/'ui/map/block-map-review.js'
        current_loader_source=current_loader_path.read_text().split('const currentTextureEntries=',1)[1].split('const reviewCharacterRecord=',1)[0]
        current_loader_source=('const currentTextureEntries='+current_loader_source).replace('import.meta.url',json.dumps('http://localhost/'))
        current_script_source=r"""
const assert=require('node:assert/strict');
const currentLoadTextures=new (Object.getPrototypeOf(async function(){}).constructor)('currentTextureRecords','loadedTextureImages','Image','document',SOURCE);
async function verifyTextureProgress(currentFailRequested){
 const currentStatusElement={textContent:''},currentImageElements=[];
 class TestImage{constructor(){currentImageElements.push(this);}set src(value){}}
 const currentPendingLoad=currentLoadTextures({a:{path:'a.png'},b:{path:'b.png'}},{},TestImage,{querySelector:()=>currentStatusElement});
 assert.match(currentStatusElement.textContent,/0 \/ 2/);
 if(currentFailRequested){
  const currentRejectedLoad=assert.rejects(currentPendingLoad,/타일 로드 실패: a/);
  currentImageElements[0].onerror();currentImageElements[1].onload();
  await currentRejectedLoad;
  assert.equal(currentStatusElement.textContent,'타일 로드 실패: a');
 }else{
  currentImageElements[0].onload();
  assert.match(currentStatusElement.textContent,/1 \/ 2/);
  currentImageElements[1].onload();await currentPendingLoad;
  assert.equal(currentStatusElement.textContent,'기본 캐릭터 원본 불러오는 중');
 }
}
(async()=>{await verifyTextureProgress(false);await verifyTextureProgress(true);})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace('SOURCE',json.dumps(current_loader_source))
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)
