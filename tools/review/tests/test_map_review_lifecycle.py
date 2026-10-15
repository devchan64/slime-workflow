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
const currentCanvasElement={clientWidth:100,clientHeight:100,parentElement:{getBoundingClientRect:()=>({width:100,height:100})},style:{}};
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

    def test_resize_uses_parent_bounds_and_rejects_zero_area(self):
        current_adapter_source=(Path(__file__).parents[1]/'ui/map/field-map-view.js').read_text()
        current_resize_source=current_adapter_source.split('function readReviewViewportSize',1)[1].split('/** 화면 컨트롤',1)[0]
        current_script_source=r"""
const assert=require('node:assert/strict');
const GAME_INTERNAL_RESOLUTION_SCALE=2;
SOURCE
let currentParentBounds={width:859,height:644.25};
const currentCanvasElement={clientWidth:287,clientHeight:0,style:{},parentElement:{getBoundingClientRect:()=>currentParentBounds}};
let currentResizeCalls=0;
const currentFieldGame={scale:{width:574,height:0,resize(width,height){currentResizeCalls++;this.width=width;this.height=height;currentCanvasElement.style.height='0px';}}};
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentFieldGame.scale.width,1718);
assert.equal(currentFieldGame.scale.height,1289);
assert.equal(currentCanvasElement.style.height,'100%');
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentResizeCalls,1);
currentParentBounds={width:390,height:292.5};
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentFieldGame.scale.height,585);
currentParentBounds={width:390,height:0};
assert.throws(()=>resizeReviewViewport(currentFieldGame,currentCanvasElement),/크기가 유효하지/);
assert.equal(currentResizeCalls,2);
""".replace('SOURCE','function readReviewViewportSize'+current_resize_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_container_resize_batches_frames_and_cleans_up(self):
        current_adapter_source=(Path(__file__).parents[1]/'ui/map/block-map-review.js').read_text()
        current_observer_source=current_adapter_source.split('let currentResizeFrameRequest=',1)[1].split('currentMapCanvas.onclick=',1)[0]
        current_script_source=r"""
const assert=require('node:assert/strict');
let currentResizeCallback,currentFrameCallback,currentExitCallback,currentRenderCount=0,currentCancelCount=0,currentDisconnectCount=0;
let currentViewportBounds={width:800,height:600},currentRenderFailure=false;
const currentStatusElement={textContent:''};
const currentMapCanvas={parentElement:{getBoundingClientRect:()=>currentViewportBounds}};
const document={querySelector:()=>currentStatusElement};
const window={addEventListener:(name,callback)=>{assert.equal(name,'pagehide');currentExitCallback=callback;}};
const requestAnimationFrame=callback=>{currentFrameCallback=callback;return 1;};
const cancelAnimationFrame=()=>currentCancelCount++;
class ResizeObserver{constructor(callback){currentResizeCallback=callback;}observe(element){assert.equal(element,currentMapCanvas.parentElement);}disconnect(){currentDisconnectCount++;}}
function renderBlockMap(){if(currentRenderFailure)throw Error('GPU failure');currentRenderCount++;}
SOURCE
currentResizeCallback();const currentFirstCallback=currentFrameCallback;currentResizeCallback();
assert.equal(currentFrameCallback,currentFirstCallback);currentFrameCallback();assert.equal(currentRenderCount,1);
currentViewportBounds={width:0,height:0};currentResizeCallback();currentFrameCallback();assert.equal(currentRenderCount,1);
currentViewportBounds={width:400,height:300};currentResizeCallback();currentFrameCallback();assert.equal(currentRenderCount,2);
currentRenderFailure=true;currentResizeCallback();currentFrameCallback();assert.match(currentStatusElement.textContent,/맵 크기 변경 실패: GPU failure/);
currentResizeCallback();currentExitCallback();assert.equal(currentCancelCount,1);assert.equal(currentDisconnectCount,1);
currentFrameCallback=null;currentResizeCallback();assert.equal(currentFrameCallback,null);
""".replace('SOURCE','let currentResizeFrameRequest='+current_observer_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)
