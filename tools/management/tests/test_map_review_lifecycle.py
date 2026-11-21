"""맵 초기화 실패·화면 이탈 시 렌더러 수명 정리를 검증한다."""
import json
from pathlib import Path
import subprocess
import unittest


class MapReviewLifecycleTests(unittest.TestCase):
    def test_source_list_preserves_nodes_until_sources_change(self):
        current_source_path=Path(__file__).parents[1]/'ui/map/block-map-review.js'
        current_render_source=current_source_path.read_text().split('let currentAppliedSourceSignature=',1)[1].split('\nrenderAppliedTileSourceList();',1)[0]
        current_render_source=('let currentAppliedSourceSignature='+current_render_source).replace('import.meta.url',json.dumps('http://localhost/'))
        current_script_source=r"""
const assert=require('node:assert/strict');
const isFieldMapReview=false,isCharacterReviewPage=true;
const groundTextureNames={paving:'first'};
const currentMapRecord={terrainCodes:{p:'paving'},guardCenters:[]};
const currentSafeVisualRecords={};
const currentTextureRecords={first:{path:'first.png',source:'/tiles/first.png',source_size:[128,128]},second:{path:'second.png',source:'/tiles/second.png',source_size:[128,128]}};
const currentAppliedGameKeys={};
let currentReplacementCount=0;
function createTestElement(){return {children:[],append(...currentChildNodes){this.children.push(...currentChildNodes);},setAttribute(){},addEventListener(){},replaceChildren(){this.children=[];},get childElementCount(){return this.children.length;}};}
const currentSourceList=createTestElement(),currentOtherLists={};
currentSourceList.replaceChildren=()=>{currentReplacementCount++;currentSourceList.children=[];};
const document={querySelector:(currentSelectorName)=>currentSelectorName==='#applied-tile-list'?currentSourceList:(currentOtherLists[currentSelectorName]??=createTestElement()),createElement:createTestElement};
SOURCE
renderAppliedTileSourceList();
const currentOriginalNode=currentSourceList.children[0];
currentOriginalNode.expanded=true;
renderAppliedTileSourceList();
assert.equal(currentReplacementCount,1);
assert.equal(currentSourceList.children[0],currentOriginalNode);
assert.equal(currentSourceList.children[0].expanded,true);
groundTextureNames.paving='second';renderAppliedTileSourceList();
assert.equal(currentReplacementCount,2);
assert.notEqual(currentSourceList.children[0],currentOriginalNode);
currentTextureRecords.second.path='updated.png';renderAppliedTileSourceList();
assert.equal(currentReplacementCount,3);
assert.equal(currentSourceList.children[1].children[1].children[0].children[0].children[0].href,'http://localhost/updated.png');
""".replace('SOURCE',current_render_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_initialization_failure_and_early_exit_destroy_renderer_once(self):
        current_adapter_path=Path(__file__).parents[1]/'ui/map/field-map-view.js'
        current_adapter_source='\n'.join(current_source_line for current_source_line in current_adapter_path.read_text().splitlines() if not current_source_line.startswith('import '))
        current_adapter_source=current_adapter_source.replace('export async function','async function').replace('export function','function')
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
 assert.throws(()=>currentReadyReview.render({}, {}, {}),/맵 검수 화면이 닫혔습니다/);
 assert.throws(()=>currentReadyReview.renderTown({}, {}, ()=>({})),/맵 검수 화면이 닫혔습니다/);
 assert.equal(currentDestroyCount,3);assert.equal(currentEventHandlers.size,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace('ADAPTER_SOURCE',current_adapter_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_texture_progress_preserves_failure_during_other_completions(self):
        current_loader_path = (Path(__file__).parents[1] / 'ui/map/vendor/field-renderer/town-renderer.mjs').resolve()
        current_loader_source = 'var MAP_RESOURCE_CONCURRENCY = ' + current_loader_path.read_text().split('var MAP_RESOURCE_CONCURRENCY = ', 1)[1].split('function collectMapResourceKeys', 1)[0]
        current_script_source = r"""
const assert=require('node:assert/strict');
SOURCE
(async()=>{
 const currentProgressRecords=[],currentPendingLoads={};
 const currentResourceRecords=[{key:'a',url:'a.png'},{key:'b',url:'b.png'}];
 const currentLoadPromise=loadMapResourceImages(currentResourceRecords,{onProgress:currentProgressRecord=>currentProgressRecords.push(currentProgressRecord),loadImage:(currentImageUrl)=>new Promise((resolveImage,rejectImage)=>{currentPendingLoads[currentImageUrl]={resolveImage,rejectImage};})});
 const currentRejectedLoad=assert.rejects(currentLoadPromise,/타일 로드 실패/);
 currentPendingLoads['a.png'].rejectImage(Error('타일 로드 실패'));
 await currentRejectedLoad;
 currentPendingLoads['b.png'].resolveImage({});
 await new Promise(currentResolve=>setImmediate(currentResolve));
 assert.deepEqual(currentProgressRecords,[{completed:0,total:2}]);
 const currentSuccessProgress=[];
 const currentImages=await loadMapResourceImages(currentResourceRecords,{onProgress:currentProgressRecord=>currentSuccessProgress.push(currentProgressRecord),loadImage:async currentImageUrl=>currentImageUrl});
 assert.deepEqual(currentImages,{a:'a.png',b:'b.png'});
 assert.deepEqual(currentSuccessProgress,[{completed:0,total:2},{completed:1,total:2},{completed:2,total:2}]);
})().catch(currentError=>{console.error(currentError);process.exitCode=1;});
""".replace('SOURCE', current_loader_source)
        current_test_result = subprocess.run(['node', '-e', current_script_source], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

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

    def test_character_keyboard_movement_preserves_camera_and_rejects_blocked_cells(self):
        current_source_text=(Path(__file__).parents[1]/'ui/map/block-map-review.js').read_text()
        current_move_source='function placeReviewCharacterCell'+current_source_text.split('function placeReviewCharacterCell',1)[1].split('currentMapCanvas.onclick=',1)[0]
        current_key_source='currentMapCanvas.onkeydown='+current_source_text.split('currentMapCanvas.onkeydown=',1)[1].split("currentMapCanvas.addEventListener('wheel'",1)[0]
        current_offsets_source='const CHARACTER_CELL_KEY_OFFSETS='+current_source_text.split('const CHARACTER_CELL_KEY_OFFSETS=',1)[1].split(';',1)[0]+';'
        current_script_source=r"""
const assert=require('node:assert/strict');
const isCharacterReviewPage=false;
const canTraverseBridgeEdge=()=>true;
const currentMapRecord={columns:3,rows:3},currentBlockedCells=new Set(['2,1']),currentMapCanvas={};
let currentCharacterCell={column:1,row:1},currentOffsetX=0,currentOffsetY=0,currentRenderCount=0;
const MAP_KEYBOARD_PAN_DISTANCE=48,MAP_ZOOM_FACTOR=1.25,currentStatusElement={textContent:''};
global.document={querySelector:()=>currentStatusElement};
function renderBlockMap(){currentRenderCount++;} function changeMapZoom(){}
SOURCE
function pressReviewKey(currentKeyName,currentShiftEnabled){currentMapCanvas.onkeydown({key:currentKeyName,shiftKey:currentShiftEnabled,preventDefault(){}});}
pressReviewKey('ArrowRight',true);assert.deepEqual(currentCharacterCell,{column:1,row:1});assert.match(currentStatusElement.textContent,/이동할 수 없는/);
pressReviewKey('ArrowLeft',true);assert.deepEqual(currentCharacterCell,{column:0,row:1});assert.equal(currentOffsetX,0);
pressReviewKey('ArrowLeft',true);assert.deepEqual(currentCharacterCell,{column:0,row:1});
pressReviewKey('ArrowUp',true);assert.deepEqual(currentCharacterCell,{column:0,row:0});
pressReviewKey('ArrowRight',false);assert.equal(currentOffsetX,-48);assert.deepEqual(currentCharacterCell,{column:0,row:0});
assert.equal(placeReviewCharacterCell(1.5,0),false);assert.equal(placeReviewCharacterCell(1,2),true);
assert.equal(currentRenderCount,4);
""".replace('SOURCE',current_offsets_source+current_move_source+current_key_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)
