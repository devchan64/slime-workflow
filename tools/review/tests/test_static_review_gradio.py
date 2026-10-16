import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path

from tools.review.serve import load_static_review_route_identifiers
from tools.review.ui.gradio.static_review_app import build_static_review_interface, create_static_review_loader, load_static_review_paths, collect_anchor_review_paths


class StaticReviewGradioTest(unittest.TestCase):
    def test_anchor_edit_commands_wait_for_runtime(self):
        current_interface_blocks=build_static_review_interface({'audit':'/fixture/anchors.html'})
        current_expected_labels={'X 적용','Y 적용','↑ 위로','← 왼쪽','현재 값 읽기','오른쪽 →','↓ 아래로','실행 취소','다시 실행','이전 프레임 앵커 가져오기','현재 프레임 원본 복원','좌표 변경 상태 읽기','정규화 JSON 다운로드','좌표 저장','동작 목록 읽기','선택 목록 읽기','표시 설정 읽기','표시 설정 적용','출력 설정 읽기','출력 설정 적용'}
        current_matched_controls=[]
        for current_component in current_interface_blocks.blocks.values():
            current_component_value=getattr(current_component,'value',None)
            if isinstance(current_component_value,str) and current_component_value in current_expected_labels:
                current_matched_controls.append(current_component)
        self.assertEqual(len(current_matched_controls),len(current_expected_labels))
        self.assertTrue(all(current_component.interactive is False for current_component in current_matched_controls))
        current_timer_records=[current_record for current_record in current_interface_blocks.get_config_file()['dependencies'] if 'currentReadyState' in (current_record.get('js') or '')]
        self.assertEqual(len(current_timer_records),1)
        self.assertTrue({current_component._id for current_component in current_matched_controls}.issubset(current_timer_records[0]['outputs']))

    def test_anchor_navigation_readiness_recovers_after_failure(self):
        from tools.review.ui.gradio.static_review_app import create_anchor_navigation_status_script
        current_script_source="""const assert=require('node:assert/strict');global.window={};
const currentReadStatus="""+create_anchor_navigation_status_script(6)+""";
let currentStatusValues=currentReadStatus();
assert.equal(currentStatusValues.length,7);
assert.ok(currentStatusValues.slice(1).every(currentValue=>currentValue.interactive===false));
window.anchorReviewPlayback=()=>{throw Error('손상 초안');};
currentStatusValues=currentReadStatus();
assert.match(currentStatusValues[0],/손상 초안/);
assert.ok(currentStatusValues.slice(1).every(currentValue=>currentValue.interactive===false));
window.anchorReviewPlayback=()=> '프레임 1 / 8';
currentStatusValues=currentReadStatus();
assert.equal(currentStatusValues[0],'프레임 1 / 8');
assert.ok(currentStatusValues.slice(1).every(currentValue=>currentValue.interactive===true));
"""
        current_script_source+="\nconst currentReadSelection="+create_anchor_navigation_status_script(6,True)+""";
assert.equal(currentReadSelection(null,null,null).slice(-2).every(currentValue=>!currentValue.interactive),true);
assert.equal(currentReadSelection('walk','down_left','anchor').slice(-2).every(currentValue=>currentValue.interactive),true);
window.anchorReviewPlayback=()=>{throw Error('실패');};
assert.equal(currentReadSelection('walk','down_left','anchor').slice(-2).every(currentValue=>!currentValue.interactive),true);
"""
        current_command_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_command_result.returncode,0,current_command_result.stderr)

    def test_anchor_disposal_cancels_pending_restore_once(self):
        current_loader_source = Path('tools/review/ui/shared/animation-anchor-editor/native-loader.js').read_text()
        current_disposal_source = current_loader_source.split('const disposeAnchorRuntime=()=>{', 1)[1].split('\n };', 1)[0]
        current_node_script = """
const assert=require('node:assert/strict');
let currentRuntimeDisposed=false,currentAbortCount=0,currentResolveCount=0,currentDisconnectCount=0;
const currentLifecycleController={abort(){currentAbortCount++;}};
const currentScheduledFrames=new Set([11]);const currentCancelledFrames=[];
const cancelAnimationFrame=currentFrameHandle=>currentCancelledFrames.push(currentFrameHandle);
const currentRemovalObserver={disconnect(){currentDisconnectCount++;}};
const currentAnchorHandlerNames=['anchorRestoreConfirmationState','resolveAnchorRestoreConfirmation'];
let currentPendingRecord={id:'pending-one'};
const currentRuntimeWindow={anchorRestoreConfirmationState:()=>currentPendingRecord,resolveAnchorRestoreConfirmation(currentIdentifierValue,currentAcceptedValue){assert.equal(currentIdentifierValue,'pending-one');assert.equal(currentAcceptedValue,false);currentResolveCount++;currentPendingRecord=null;}};
const window={...currentRuntimeWindow};
const disposeAnchorRuntime=()=>{DISPOSAL};
disposeAnchorRuntime();disposeAnchorRuntime();
assert.equal(currentResolveCount,1);assert.equal(currentAbortCount,1);assert.equal(currentDisconnectCount,1);
assert.deepEqual(currentCancelledFrames,[11]);assert.equal(currentScheduledFrames.size,0);
assert.deepEqual(window,{});assert.equal(currentPendingRecord,null);
""".replace('DISPOSAL', current_disposal_source)
        subprocess.run(['node', '-e', current_node_script], check=True, capture_output=True, text=True)

    def test_anchor_restore_confirmation_preserves_changed_edits(self):
        current_editor_source = Path('tools/review/ui/shared/animation-anchor-editor/editor.js').read_text()
        current_restore_source = current_editor_source.split('let pendingAnchorRestoreConfirmation=null;', 1)[1].split('async function refreshAnchorHistoryList()', 1)[0]
        current_node_script = """
const assert=require('node:assert/strict');
global.window={};global.document={body:{dataset:{coordinateDownloadPending:'true'}},querySelector:()=>currentStatusRecord};
const currentStatusRecord={textContent:''};const currentEmbeddedReviewMode=true;
const anchorHistoryViewState={selected:null};let currentRequestCount=0;let currentEditVersion=1;
const buildCoordinateArtifact=()=>({version:currentEditVersion});
const requestAnchorHistoryCommand=async()=>{currentRequestCount++;throw Error('격리 읽기 실패');};
let pendingAnchorRestoreConfirmation=null;
""" + current_restore_source + """
(async()=>{
 let currentRestorePromise=restoreAnchorHistoryRecord({id:'first'});
 window.resolveAnchorRestoreConfirmation(window.anchorRestoreConfirmationState().id,false);
 await currentRestorePromise;assert.equal(currentRequestCount,0);assert.match(currentStatusRecord.textContent,/취소/);
 currentRestorePromise=restoreAnchorHistoryRecord({id:'first'});
 currentEditVersion++;
 window.resolveAnchorRestoreConfirmation(window.anchorRestoreConfirmationState().id,true);
 await currentRestorePromise;assert.equal(currentRequestCount,0);assert.match(currentStatusRecord.textContent,/편집 내용이 변경/);
 currentRestorePromise=restoreAnchorHistoryRecord({id:'first'});
 anchorHistoryViewState.selected='second';
 window.resolveAnchorRestoreConfirmation(window.anchorRestoreConfirmationState().id,true);
 await currentRestorePromise;assert.equal(currentRequestCount,0);assert.match(currentStatusRecord.textContent,/대상이 변경/);
 currentRestorePromise=restoreAnchorHistoryRecord({id:'first'});
 window.resolveAnchorRestoreConfirmation(window.anchorRestoreConfirmationState().id,true);
 await currentRestorePromise;assert.equal(currentRequestCount,1);assert.match(currentStatusRecord.textContent,/격리 읽기 실패/);
 assert.equal(currentEditVersion,2);assert.equal(window.anchorRestoreConfirmationState(),null);
})().catch(currentErrorValue=>{console.error(currentErrorValue);process.exitCode=1;});
"""
        current_node_result = subprocess.run(['node', '-e', current_node_script], capture_output=True, text=True)
        self.assertEqual(current_node_result.returncode, 0, current_node_result.stderr)

    def test_anchor_restore_success_and_inflight_edit_protection(self):
        current_editor_source = Path('tools/review/ui/shared/animation-anchor-editor/editor.js').read_text()
        current_restore_source = current_editor_source.split('let pendingAnchorRestoreConfirmation=null;', 1)[1].split('async function refreshAnchorHistoryList()', 1)[0]
        current_node_script = """
const assert=require('node:assert/strict');
global.window={};global.document={body:{dataset:{coordinateDownloadPending:'true'}},querySelector:()=>currentStatusRecord};
const currentStatusRecord={textContent:''};const currentEmbeddedReviewMode=true;
const anchorHistoryViewState={selected:null};
const reviewFrameRecords=[{frameId:'one',direction:'down_left',image:'sheet',rect:{x:0,y:0,width:100,height:100},anchor:{x:10,y:20},contacts:[]}];
const usesAnchorOnlyMode=true,usesFootCentersOnly=false;let currentChangeCount=0,currentPauseCount=0,currentRequestCount=0;
const buildCoordinateArtifact=()=>structuredClone({source:{id:'sample'},coordinateMode:'anchor',frames:reviewFrameRecords});
const copyFrameCoordinates=currentFrameRecord=>structuredClone(currentFrameRecord);
const recordCoordinateChange=()=>{currentChangeCount++;};const pauseFramePlayback=()=>{currentPauseCount++;};
const currentSavedDocument=buildCoordinateArtifact();currentSavedDocument.frames[0].anchor={x:30,y:40};
let currentDuringLoadCallback=()=>{};
const requestAnchorHistoryCommand=async()=>{currentRequestCount++;currentDuringLoadCallback();return {document:structuredClone(currentSavedDocument)};};
let pendingAnchorRestoreConfirmation=null;
""" + current_restore_source + """
(async()=>{
 let currentRestorePromise=restoreAnchorHistoryRecord({id:'accepted'});
 assert.equal(currentRequestCount,0);
 window.resolveAnchorRestoreConfirmation(window.anchorRestoreConfirmationState().id,true);
 await currentRestorePromise;
 assert.deepEqual(reviewFrameRecords[0].anchor,{x:30,y:40});
 assert.deepEqual(reviewFrameRecords[0].contacts,[{x:30,y:40},{x:30,y:40}]);
 assert.equal(currentChangeCount,1);assert.equal(currentPauseCount,1);
 assert.equal(currentStatusRecord.textContent,'불러옴 · accepted');
 document.body.dataset.coordinateDownloadPending='false';
 await restoreAnchorHistoryRecord({id:'clean'});
 assert.equal(window.anchorRestoreConfirmationState(),null);assert.equal(currentRequestCount,2);
 currentDuringLoadCallback=()=>{reviewFrameRecords[0].anchor.x=77;};
 await restoreAnchorHistoryRecord({id:'inflight'});
 assert.equal(reviewFrameRecords[0].anchor.x,77);assert.equal(currentChangeCount,2);
 assert.match(currentStatusRecord.textContent,/불러오는 동안 편집 내용이 변경/);
})().catch(currentErrorValue=>{console.error(currentErrorValue);process.exitCode=1;});
"""
        current_node_result = subprocess.run(['node', '-e', current_node_script], capture_output=True, text=True)
        self.assertEqual(current_node_result.returncode, 0, current_node_result.stderr)

    def test_browser_choices_skip_stale_server_choice_validation(self):
        from tools.review.ui.gradio.sprite_editor_v2_app import build_sprite_v2_interface
        from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface
        current_interface_records = (
            ('static', build_static_review_interface({'test': '/test/anchors.html'})),
            ('sprite', build_sprite_v2_interface()),
            ('anny', build_anny_attribute_interface(8770)),
        )
        for current_page_name, current_interface_blocks in current_interface_records:
            current_browser_identifiers = {
                current_component._id
                for current_event_record in current_interface_blocks.fns.values()
                if current_event_record.fn is None and current_event_record.js
                for current_component in current_event_record.outputs
                if type(current_component).__name__ == 'Dropdown' and not current_component.choices
            }
            current_backend_events = [
                current_event_record for current_event_record in current_interface_blocks.fns.values()
                if current_event_record.fn and any(current_component._id in current_browser_identifiers for current_component in current_event_record.inputs)
            ]
            if current_page_name!='static':self.assertTrue(current_backend_events, current_page_name)
            for current_event_record in current_backend_events:
                with self.subTest(page=current_page_name, callback=current_event_record.name):
                    self.assertFalse(current_event_record.preprocess)

    def test_read_selection_updates_apply_button_without_change_event(self):
        current_interface_blocks = build_static_review_interface({'walk-review': 'animation/anchors.html'})
        current_config_record = current_interface_blocks.get_config_file()
        current_read_script = next(current_event['js'] for current_event in current_config_record['dependencies'] if 'currentSelectionValues=window.anchorReviewSelection' in (current_event.get('js') or ''))
        current_node_script = "const assert=require('node:assert/strict');global.window={};const readSelection=(" + current_read_script + ");" + """
window.anchorReviewSelection=()=>[{value:'down_left'},{value:'anchor'},'선택 완료'];
assert.equal(readSelection()[3].interactive,true);
window.anchorReviewSelection=()=>[{value:'down_left'},{value:''},'좌표 없음'];
assert.equal(readSelection()[3].interactive,false);
window.anchorReviewSelection=()=>{throw Error('원본 준비 실패');};
const failedValues=readSelection();
assert.equal(failedValues[3].interactive,false);
assert.equal(failedValues[2],'원본 준비 실패');
assert.deepEqual(failedValues[0],{__type__:'update'});
"""
        current_node_result = subprocess.run(['node', '-e', current_node_script], capture_output=True, text=True)
        self.assertEqual(current_node_result.returncode, 0, current_node_result.stderr)

    def test_empty_review_selection_disables_apply(self):
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_config_record=current_interface_blocks.get_config_file()
        for current_button_label in ('선택 동작 불러오기','방향·좌표 선택 적용'):
            current_button_record=next(current_component for current_component in current_config_record['components'] if current_component['type']=='button' and current_component['props']['value']==current_button_label)
            self.assertFalse(current_button_record['props']['interactive'])
        current_scripts=[current_event.js for current_event in current_interface_blocks.fns.values() if current_event.js and len(current_event.outputs)==1 and getattr(current_event.outputs[0],'value',None) in ('선택 동작 불러오기','방향·좌표 선택 적용')]
        self.assertEqual(len(current_scripts),2)
        current_node_script="const assert=require('node:assert/strict');global.window={anchorReviewPlayback:()=> 'ready'};const scripts="+json.dumps(current_scripts)+""";for(const source of scripts){const callback=eval('('+source+')');assert.equal(callback(null,null).interactive,false);assert.equal(callback('', '').interactive,false);assert.equal(callback('walk','anchor').interactive,true);window.anchorReviewPlayback=()=>{throw Error('로드 실패');};assert.equal(callback('walk','anchor').interactive,false);window.anchorReviewPlayback=()=> 'ready';}"""
        current_node_result=subprocess.run(['node','-e',current_node_script],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)



    def test_invalid_static_manifest_fails_before_mapping(self):
        current_page_record={'id':'walk-review','path':'animation/anchors.html','uiMode':'gradio-static'}
        for current_source_record in ([], {'pages':{}}, {'pages':[None]}, {'pages':[current_page_record,current_page_record]}, {'pages':[{**current_page_record,'path':'animation/image.png'}]}):
            with self.subTest(source=current_source_record), tempfile.TemporaryDirectory() as current_directory_name:
                current_source_path=Path(current_directory_name)/'manager-source.json'
                current_source_path.write_text(json.dumps(current_source_record))
                with self.assertRaises(ValueError):
                    load_static_review_paths(current_source_path)
                with self.assertRaises(ValueError):
                    load_static_review_route_identifiers(current_source_path)

    def test_loads_only_declared_static_review_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_file_path=Path(temporary_directory_name)/'manager-source.json'
            source_file_path.write_text(json.dumps({'pages':[
                {'id':'walk-review','path':'animation/anchors.html','uiMode':'gradio-static'},
                {'id':'momask','path':'/momask-generator/','uiMode':'gradio'},
            ]}),encoding='utf-8')

            static_review_paths=load_static_review_paths(source_file_path)

        self.assertEqual(static_review_paths,{'walk-review':'animation/anchors.html'})

    def test_declared_anchor_preview_uses_same_editor_and_controls(self):
        current_static_paths={'standing-anchors':'standing/preview.html','walk-anchors':'walking/anchors.html'}
        current_anchor_paths=['standing/preview.html']
        self.assertEqual(collect_anchor_review_paths(current_static_paths,current_anchor_paths),['standing/preview.html','walking/anchors.html'])
        self.assertEqual(collect_anchor_review_paths(current_static_paths,['/standing/preview.html']),['standing/preview.html','walking/anchors.html'])
        with self.assertRaisesRegex(ValueError,'등록되지 않은'):
            collect_anchor_review_paths(current_static_paths,['outside/preview.html'])
        current_interface_blocks=build_static_review_interface(current_static_paths,current_anchor_paths)
        current_visibility_scripts=[current_event_record['js'] for current_event_record in current_interface_blocks.get_config_file()['dependencies'] if 'visible:' in (current_event_record.get('js') or '') and 'currentReviewId=' in current_event_record['js']]
        current_script_source="const assert=require('node:assert/strict');global.location={search:'?review=standing-anchors'};\n"+'\n'.join('assert.deepEqual(('+current_script_value+')().map(value=>value.visible),[true,true,true,true]);' for current_script_value in current_visibility_scripts)
        self.assertEqual(len(current_visibility_scripts),1)
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_collects_direct_static_page_routes(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_file_path=Path(temporary_directory_name)/'manager-source.json'
            source_file_path.write_text(json.dumps({'pages':[
                {'id':'walk-review','path':'animation/anchors.html','uiMode':'gradio-static'},
                {'id':'momask','path':'/momask-generator/','uiMode':'gradio'},
            ]}),encoding='utf-8')

            static_review_routes=load_static_review_route_identifiers(source_file_path)

        self.assertEqual(static_review_routes,{'/animation/anchors.html':'walk-review'})

    def test_unknown_static_identifier_finishes_loading(self):
        current_loader_text=create_static_review_loader(8770,{'walk-review':'animation/anchors.html'})
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_visibility_scripts=[current_event_record['js'] for current_event_record in current_interface_blocks.get_config_file()['dependencies'] if 'const currentReviewPaths=' in (current_event_record.get('js') or '')]
        for current_visibility_script in current_visibility_scripts:
            current_visibility_result=subprocess.run(['node','-e',"global.location={search:'?review=toString'};const assert=require('node:assert/strict');const currentUpdates=("+current_visibility_script+")();for(const currentUpdate of (Array.isArray(currentUpdates)?currentUpdates:[currentUpdates]))assert.equal(currentUpdate.visible,false);"],capture_output=True,text=True)
            self.assertEqual(current_visibility_result.returncode,0,current_visibility_result.stderr)
        current_script_text="""
const assert=require('node:assert/strict');
const currentRootRecord={dataset:{},attributes:{'aria-busy':'true'},setAttribute(name,value){this.attributes[name]=value;},innerHTML:''};
global.document={querySelector:()=>currentRootRecord};
global.window={location:{search:'?review=toString'}};
(async()=>{await ("""+current_loader_text+""")();assert.equal(currentRootRecord.attributes['aria-busy'],'false');assert.match(currentRootRecord.innerHTML,/표시할 정적 검수 페이지/);})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        current_node_result=subprocess.run(['node','-e',current_script_text],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_component_uses_allowlisted_page_and_isolates_game_design(self):
        loader_script_value=create_static_review_loader(8770,{'walk-review':'animation/anchors.html'})
        interface_blocks_value=build_static_review_interface({'walk-review':'animation/anchors.html'})

        self.assertIn('staticReviewPaths',loader_script_value)
        self.assertIn('selectedReviewPath',loader_script_value)
        self.assertIn("searchParams.set('embedded','gradio-static')",loader_script_value)
        self.assertNotIn('window.fetch=',loader_script_value)
        self.assertNotIn('document.head.append',loader_script_value)
        self.assertNotIn("document.createElement('iframe')",loader_script_value)
        self.assertNotIn('terrain-preview.html',loader_script_value)
        self.assertNotIn('contentWindow.anchorReviewPlayback',loader_script_value)
        self.assertIn('await mountNativeAnchorReview(staticReviewRoot,staticReviewPageLocation)',loader_script_value)
        self.assertIn('await mountNativeGameReview(staticReviewRoot,staticReviewPageLocation)',loader_script_value)
        self.assertNotIn('contentWindow.anchorReviewSeekFrame',loader_script_value)
        current_terrain_events=[current_event_record for current_event_record in interface_blocks_value.get_config_file()['dependencies'] if 'window.terrainReviewControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_terrain_events),0)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_terrain_events))
        self.assertFalse(interface_blocks_value.css)
        self.assertIn('static-review-root',str(interface_blocks_value.get_config_file()))
        self.assertIn('aria-busy="true"',str(interface_blocks_value.get_config_file()))

    def test_game_mount_disposes_once_and_ignores_detached_request(self):
        current_loader_source=(Path(__file__).parents[1]/'ui/gradio/game_native_loader.js').read_text()
        current_script_source="""
const assert=require('node:assert/strict'),vm=require('node:vm');
const currentManifestRecord={schemaVersion:2,kind:'slime-ui-review',pages:[{id:'design-system',path:'review/design-system.html'}],componentModules:{'design-system':'assets/native.js'},files:[{path:'assets/native.js',sha256:'a'.repeat(64)}]};
let currentMountCount=0,currentDisposeCount=0,currentObserverCallback,currentDisconnectCount=0;
const currentWindowEvents=new Map();
global.window={addEventListener:(name,callback)=>currentWindowEvents.set(name,callback),removeEventListener:name=>currentWindowEvents.delete(name)};
global.document={body:{},createElement:()=>({setAttribute(){}})};
global.MutationObserver=class{constructor(callback){currentObserverCallback=callback;}observe(){}disconnect(){currentDisconnectCount++;}};
const createReviewRoot=()=>({isConnected:true,children:[],attributes:{},replaceChildren(...children){this.children=children;},setAttribute(name,value){this.attributes[name]=value;}});
(async()=>{
 let currentModuleController={dispose(){currentDisposeCount++;}};
 const currentModuleInstance=new vm.SyntheticModule(['mountReviewPage'],function(){this.setExport('mountReviewPage',()=>{currentMountCount++;return currentModuleController;});});
 await currentModuleInstance.link(()=>{});await currentModuleInstance.evaluate();
 const mountNativeGameReview=vm.compileFunction("""+json.dumps(current_loader_source+'\nreturn mountNativeGameReview;')+""",[],{importModuleDynamically:()=>currentModuleInstance})();
 const currentPageLocation=new URL('http://localhost/ui-aaaaaaaaaaaaaaaa/review/design-system.html');
 global.fetch=async()=>({ok:true,json:async()=>currentManifestRecord});
 const currentFirstRoot=createReviewRoot();
 await mountNativeGameReview(currentFirstRoot,currentPageLocation);
 assert.equal(currentMountCount,1);assert.equal(currentFirstRoot.attributes['aria-busy'],'false');
 const currentPagehideHandler=currentWindowEvents.get('pagehide');currentPagehideHandler();currentPagehideHandler();
 assert.equal(currentDisposeCount,1);assert.equal(currentDisconnectCount,1);assert.equal(currentWindowEvents.size,0);
 let currentResolveRequest,currentRequestSignal;
 global.fetch=(_url,options)=>{currentRequestSignal=options.signal;return new Promise(resolve=>currentResolveRequest=resolve);};
 const currentDetachedRoot=createReviewRoot();
 const currentPendingMount=mountNativeGameReview(currentDetachedRoot,currentPageLocation);
 currentDetachedRoot.isConnected=false;currentObserverCallback();assert.equal(currentRequestSignal.aborted,true);
 currentResolveRequest({ok:true,json:async()=>currentManifestRecord});await currentPendingMount;
 assert.equal(currentMountCount,1);assert.equal(currentDetachedRoot.children.length,0);
 global.fetch=async()=>({ok:true,json:async()=>({...currentManifestRecord,componentModules:{'design-system':'https://outside.test/native.js'}})});
 const currentInvalidRoot=createReviewRoot();await mountNativeGameReview(currentInvalidRoot,currentPageLocation);
 assert.match(currentInvalidRoot.children[0].textContent,/검증된 검수 컴포넌트/);assert.equal(currentMountCount,1);assert.equal(currentWindowEvents.size,0);
 let currentBattlefieldChoice='all';const currentBrowserChanges=[];
 window.location={href:'http://localhost/management/?review=battle'};window.history={replaceState:(_state,_title,url)=>currentBrowserChanges.push(String(url))};
 currentModuleController={dispose(){currentDisposeCount++;},readState:()=>({choices:[['전체','all'],['전장','field-a']],field:currentBattlefieldChoice,status:'렌더 상태'}),selectField:currentFieldName=>{if(!['all','field-a'].includes(currentFieldName))throw Error('지원하지 않는 전장');currentBattlefieldChoice=currentFieldName;}};
 global.fetch=async()=>({ok:true,json:async()=>({...currentManifestRecord,pages:[{id:'battle',path:'review/battlefield-preview.html'}],componentModules:{battle:'assets/native.js'}})});
 await mountNativeGameReview(createReviewRoot(),new URL('http://localhost/ui-aaaaaaaaaaaaaaaa/review/battlefield-preview.html'));
 assert.equal(window.battlefieldReviewControls(null)[0].value,'all');
 assert.throws(()=>window.battlefieldReviewControls('unknown'),/지원하지 않는 전장/);assert.equal(currentBattlefieldChoice,'all');assert.equal(currentBrowserChanges.length,0);
 assert.equal(window.battlefieldReviewControls('field-a')[0].value,'field-a');assert.match(currentBrowserChanges[0],/field=field-a/);
 currentWindowEvents.get('pagehide')();assert.equal(window.battlefieldReviewControls,undefined);assert.equal(currentDisposeCount,2);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        current_node_result=subprocess.run(['node','--experimental-vm-modules','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_anchor_history_omits_unsupported_generation_actions(self):
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_config_record=current_interface_blocks.get_config_file()
        current_button_labels=[current_component_record['props'].get('value') for current_component_record in current_config_record['components'] if current_component_record['type']=='button']
        for current_button_label in ['좌표 저장','결과 조회','입력값 불러오기','이력 목록 초기화']:
            self.assertIn(current_button_label,current_button_labels)
        for current_button_label in ['생성 재개','작업 중지','로그 조회','선택 이력 삭제']:
            self.assertNotIn(current_button_label,current_button_labels)

    def test_confirmed_reset_rejects_duplicate_submission_and_changed_target(self):
        current_config_record=build_static_review_interface({'walk-review':'animation/anchors.html'}).get_config_file()
        current_confirm_script=next(current_event_record['js'] for current_event_record in current_config_record['dependencies'] if 'const currentResultValues=await (' in (current_event_record.get('js') or ''))
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_history_source=current_editor_source.split('window.anchorReviewResetTarget=',1)[1].split('const anchorHistoryViewState=',1)[0]
        current_script_source="""
const assert=require('node:assert/strict');global.window={};
const currentEmbeddedReviewMode=true,reviewAnimationIdentity='walk',reviewAnimationVersion='v1';
const currentCommandRecords=[];
async function requestAnchorHistoryCommand(currentCommandName,currentPayloadRecord){currentCommandRecords.push(currentCommandName);return currentCommandName==='anchor-history'?{items:[]}:{cleared:0};}
window.anchorReviewResetTarget="""+current_history_source+"""
(async()=>{
 await assert.rejects(window.anchorReviewHistory('reset',null,'idle · v1'),/확인 대상/);
 assert.equal(currentCommandRecords.length,0);
 await window.anchorReviewHistory('reset',null,'walk · v1');assert.deepEqual(currentCommandRecords,['anchor-history-reset','anchor-history']);
 let currentResolveRequest,currentRequestCount=0;
 window.anchorReviewHistory=()=>{currentRequestCount++;return new Promise(currentResolveValue=>{currentResolveRequest=currentResolveValue;});};
 const currentConfirmCallback="""+current_confirm_script+""";
 const currentFirstRequest=currentConfirmCallback(null,true,'walk · v1');
 const currentDuplicateResult=await currentConfirmCallback(null,true,'walk · v1');
 assert.equal(currentRequestCount,1);assert.match(currentDuplicateResult[4],/초기화 중/);
 currentResolveRequest([null,'',null,'','완료']);assert.equal((await currentFirstRequest)[4],'완료');
})().catch(currentErrorValue=>{console.error(currentErrorValue);process.exitCode=1;});
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_output_settings_reject_invalid_values_without_partial_updates(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('window.anchorReviewOutputSettings=',1)[1].split('// 표시 선택은',1)[0]
        current_script_source="""
const assert=require('node:assert/strict');global.window={};
const currentMapInput={value:'field',onchange:()=>{}};
const gameOutputScaleToggleElement={checked:true},actorSizeChoiceElement={value:'medium'},bodyHeightInputElement={value:'80'},previewTileWidthElement={value:'240'};
const gameRenderMetrics={tileWidth:80,tileHeight:40,townTileWidth:64,townTileHeight:32};
const GAME_SIZE_PRESETS={small:{},medium:{},large:{},huge:{}};
const PREVIEW_TILE_MINIMUM_WIDTH=32,PREVIEW_TILE_MAXIMUM_WIDTH=600;
global.document={querySelector:name=>name==='#mapScaleChoice'?currentMapInput:{textContent:'크기 기준'}};
window.anchorReviewOutputSettings="""+current_bridge_source+"""
const currentInitialValues=window.anchorReviewOutputSettings(null);
assert.throws(()=>window.anchorReviewOutputSettings([false,'town','large',120,241]));
assert.deepEqual(window.anchorReviewOutputSettings(null),currentInitialValues);
assert.throws(()=>window.anchorReviewOutputSettings([false,'town','large',0,240]));
assert.deepEqual(window.anchorReviewOutputSettings(null),currentInitialValues);
assert.deepEqual(window.anchorReviewOutputSettings([false,'town','large',120,320]).slice(0,5),[false,'town','large',120,320]);
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_display_settings_validate_before_applying(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('window.anchorReviewDisplay=',1)[1].split('// 좌표 조작은',1)[0]
        current_script_source="""
const assert=require('node:assert/strict');global.window={};
const guideToggleElement={checked:true},rigMiniMapToggleElement={checked:true,onchange:()=>{}};
const currentTileInput={checked:true},currentShadowInput={checked:true};
global.document={querySelector:name=>name==='#tilePreviewToggle'?currentTileInput:currentShadowInput};
window.anchorReviewDisplay="""+current_bridge_source+"""
assert.deepEqual(window.anchorReviewDisplay(null).slice(0,4),[true,true,true,true]);
assert.deepEqual(window.anchorReviewDisplay([false,false,true,false]).slice(0,4),[false,false,true,false]);
assert.throws(()=>window.anchorReviewDisplay([true,true,false,1]));
assert.deepEqual(window.anchorReviewDisplay(null).slice(0,4),[false,false,true,false]);
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_anchor_coordinates_use_position_only_shared_joypad(self):
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_config_record=current_interface_blocks.get_config_file()
        current_button_labels=[current_component_record['props'].get('value') for current_component_record in current_config_record['components'] if current_component_record['type']=='button']
        self.assertIn('X 적용',current_button_labels)
        self.assertIn('Y 적용',current_button_labels)
        self.assertIn('선택 목록 읽기',current_button_labels)
        self.assertNotIn('배율 적용',current_button_labels)
        self.assertNotIn('배율 늘리기 +',current_button_labels)
        current_coordinate_events=[current_event_record for current_event_record in current_config_record['dependencies'] if 'anchorReviewCoordinates' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_coordinate_events),7)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_coordinate_events))

    def test_direct_entrypoint_loads_shared_components(self):
        current_entrypoint_path=Path(__file__).parents[1]/'ui/gradio/static_review_app.py'
        current_process_result=subprocess.run([sys.executable,str(current_entrypoint_path),'--help'],capture_output=True,text=True)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
        self.assertIn('--source-file',current_process_result.stdout)

    def test_anchor_navigation_preserves_frames_on_invalid_seek(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('// 공용 Gradio 탐색기',1)[1].split('if(window.anchorReviewNativeMode',1)[0]
        current_bridge_source=current_bridge_source[current_bridge_source.index('window.anchorReviewPlayback='):]
        current_script_source="""
const assert=require('node:assert/strict');
global.window={};global.document={querySelector:()=>({textContent:''})};
const frameChoiceElement={value:'0'},REVIEW_FRAME_COUNT=8,REVIEW_FRAME_DURATION=125;
let animationPlaybackActive=false,animationStartedTime=0;
const currentImageLoadFailure=null,currentImageLoadComplete=true;
function pauseFramePlayback(){animationPlaybackActive=false;}
function moveFrameSelection(delta){pauseFramePlayback();frameChoiceElement.value=String((Number(frameChoiceElement.value)+delta+REVIEW_FRAME_COUNT)%REVIEW_FRAME_COUNT);}
"""+current_bridge_source+"""
assert.equal(window.anchorReviewPlayback('next'),'2 / 8 · 정지');
assert.equal(window.anchorReviewSeekFrame(8),'8 / 8 · 정지');
assert.equal(window.anchorReviewPlayback('next'),'1 / 8 · 정지');
assert.equal(window.anchorReviewPlayback('play'),'1 / 8 · 재생 중');
assert.throws(()=>window.anchorReviewSeekFrame(9));
assert.equal(animationPlaybackActive,true);assert.equal(frameChoiceElement.value,'0');
assert.equal(window.anchorReviewPlayback('stop'),'1 / 8 · 정지');
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

if __name__=='__main__':
    unittest.main()
