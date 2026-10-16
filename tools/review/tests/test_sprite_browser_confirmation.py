"""운영 작업 없이 브라우저 확인의 취소·대상 보존·중복 방지를 검증한다."""
from pathlib import Path
import subprocess
import unittest

import gradio as gr

from tools.review.common.gradio_browser_confirmation import build_browser_confirmation


class SpriteBrowserConfirmationTests(unittest.TestCase):
    def test_upload_picker_and_clipboard_pause_before_waiting(self):
        current_source_path=Path(__file__).resolve().parents[1]/'ui/character_animation/sprite-editor-v2.js'
        current_action_source='\n'.join(current_source_line for current_source_line in current_source_path.read_text().splitlines() if current_source_line.startswith(("bindEditorAction('upload',", "bindEditorAction('paste',")))
        current_test_script=r"""
const assert=require('node:assert/strict');
const currentActionCallbacks=new Map();let currentProjectIdentifier='fixture',currentPlayingState=true;
let currentPickerCalls=0,currentClipboardCalls=0;
const currentFileInput={disabled:true,click(){assert.equal(currentPlayingState,false);currentPickerCalls++;}};
function findEditorElement(){return currentFileInput;}
function bindEditorAction(currentActionName,currentActionCallback){currentActionCallbacks.set(currentActionName,currentActionCallback);}
function stopEditorPlayback(){currentPlayingState=false;}
const navigator={clipboard:{async read(){assert.equal(currentPlayingState,false);currentClipboardCalls++;throw Error('denied');}}};
SOURCE
(async()=>{
 currentActionCallbacks.get('upload')();assert.equal(currentPickerCalls,1);
 currentPlayingState=true;
 await assert.rejects(currentActionCallbacks.get('paste')(),/클립보드 접근/);
 assert.equal(currentClipboardCalls,1);assert.equal(currentPlayingState,false);
 currentProjectIdentifier=null;
 assert.throws(()=>currentActionCallbacks.get('upload')(),/작업을 생성/);
 assert.equal(currentPickerCalls,1);
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
""".replace('SOURCE',current_action_source)
        current_test_result=subprocess.run(['node','-e',current_test_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_image_batch_failure_preserves_document_and_retry_commits_once(self):
        current_source_path=Path(__file__).resolve().parents[1]/'ui/character_animation/sprite-editor-v2.js'
        current_register_source=next(current_source_line for current_source_line in current_source_path.read_text().splitlines() if current_source_line.startswith('async function registerEditorFiles('))
        current_test_script=r"""
const assert=require('node:assert/strict');
let currentProjectIdentifier='fixture',currentUploadTarget='append',currentFrameIndex=0;
const currentProjectDocument={frames:[{id:'original',asset:'original'}],reference:{asset:'reference'}};
let currentUndoCount=0,currentRefreshCount=0,currentUploadCount=0,currentFailureMode='upload';
class FileReader{readAsDataURL(currentFileValue){this.result='data:image/png;base64,'+currentFileValue.name;this.onload();}}
async function requestEditorCommand(currentCommandName,currentPayloadRecord){currentUploadCount++;if(currentFailureMode==='upload'&&currentPayloadRecord.data==='second')throw Error('upload failure');return {asset:currentPayloadRecord.data,data:'image'};}
async function cacheEditorImage(currentAssetName){if(currentFailureMode==='decode'&&currentAssetName==='second')throw Error('decode failure');}
function stopEditorPlayback(){}
function createEditorImageRecord(currentAssetName,currentFileName){return {asset:currentAssetName,name:currentFileName};}
function retainUndoSnapshot(){currentUndoCount++;}
function refreshEditorScreen(){currentRefreshCount++;}
function writeEditorStatus(){}
SOURCE
(async()=>{
 const currentOriginalDocument=JSON.stringify(currentProjectDocument);
 for(const currentTargetValue of ['append','reference','replace']){
  currentUploadTarget=currentTargetValue;
  await registerEditorFiles([]);
  assert.equal(JSON.stringify(currentProjectDocument),currentOriginalDocument);
  assert.equal(currentFrameIndex,0);assert.equal(currentUndoCount,0);assert.equal(currentRefreshCount,0);assert.equal(currentUploadCount,0);
 }
 currentUploadTarget='append';
 const currentBatchFiles=[{name:'first',size:1},{name:'second',size:1}];
 for(const currentFailureValue of ['upload','decode']){
  currentFailureMode=currentFailureValue;
  await assert.rejects(registerEditorFiles(currentBatchFiles),/failure/);
  assert.equal(JSON.stringify(currentProjectDocument),currentOriginalDocument);
  assert.equal(currentFrameIndex,0);assert.equal(currentUndoCount,0);assert.equal(currentRefreshCount,0);
 }
 currentFailureMode='none';await registerEditorFiles(currentBatchFiles);
 assert.deepEqual(currentProjectDocument.frames.map(currentFrameRecord=>currentFrameRecord.asset),['original','first','second']);
 assert.equal(currentFrameIndex,1);assert.equal(currentUndoCount,1);assert.equal(currentRefreshCount,1);
 assert.deepEqual(currentProjectDocument.reference,{asset:'reference'});
 currentUploadTarget='replace';currentFrameIndex=0;
 const currentNormalRequest=requestEditorCommand;
 requestEditorCommand=async(...currentRequestArguments)=>{const currentResponseValue=await currentNormalRequest(...currentRequestArguments);currentFrameIndex=1;return currentResponseValue;};
 await registerEditorFiles([{name:'replacement',size:1}]);
 assert.equal(currentProjectDocument.frames[0].asset,'replacement');
 assert.equal(currentProjectDocument.frames[0].id,'original');
 assert.equal(currentProjectDocument.frames[1].asset,'first');
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
""".replace('SOURCE',current_register_source)
        current_test_result=subprocess.run(['node','-e',current_test_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_project_delete_rejects_changed_confirmation_target(self):
        import ast
        current_source_path = Path(__file__).resolve().parents[1] / 'ui/gradio/sprite_editor_v2_app.py'
        current_source_tree = ast.parse(current_source_path.read_text())
        current_delete_script = next(ast.literal_eval(current_source_node.value) for current_source_node in ast.walk(current_source_tree) if isinstance(current_source_node, ast.Assign) and any(isinstance(current_target_node, ast.Name) and current_target_node.id == 'current_delete_script' for current_target_node in current_source_node.targets))
        current_test_source = """
const assert=require('node:assert/strict');
const currentCommandRecords=[];
const window={spriteV2ProjectControls:async(...currentArguments)=>{currentCommandRecords.push(currentArguments);return ['list','deleted','revisions'];}};
const currentDeleteCallback=""" + current_delete_script + """;
(async()=>{
 for(const currentSelectedIdentifier of ['', 'other']){
  const currentResultValues=await currentDeleteCallback('name',384,currentSelectedIdentifier,'original');
  assert.match(currentResultValues[1],/삭제 대상이 변경/);
  assert.deepEqual(currentResultValues[0],{__type__:'update'});
 }
 assert.equal(currentCommandRecords.length,0);
 const currentResultValues=await currentDeleteCallback('name',384,'original','original');
 assert.deepEqual(currentCommandRecords,[['delete','name',384,'original',null]]);
 assert.deepEqual(currentResultValues.slice(3),[{__type__:'update',visible:false},'','']);
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
"""
        current_test_result = subprocess.run(['node', '-e', current_test_source], capture_output=True, text=True, timeout=20)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

    def test_native_confirmation_has_no_python_callback(self):
        with gr.Blocks() as current_test_blocks:
            build_browser_confirmation('spriteV2ConfirmationState','spriteV2ResolveConfirmation')
        current_test_config=current_test_blocks.get_config_file()
        self.assertEqual(len(current_test_config['dependencies']),3)
        for current_event_record in current_test_config['dependencies']:
            self.assertFalse(current_event_record['backend_fn'])
            self.assertFalse(current_event_record['queue'])
        with gr.Blocks():
            with self.assertRaises(ValueError):
                build_browser_confirmation('bad();','resolvePendingConfirmation')

    def test_cancel_and_accept_preserve_browser_target(self):
        current_source_path=Path(__file__).resolve().parents[1]/'ui/character_animation/sprite-editor-v2.js'
        current_browser_source=current_source_path.read_text()
        self.assertNotIn('!confirm(',current_browser_source)
        current_confirmation_source=current_browser_source.split('let currentPendingConfirmation=')[1].split('window.spriteV2ReadinessControls=')[0]
        current_action_source='\n'.join(current_line for current_line in current_browser_source.splitlines() if current_line.startswith(('async function createEditorProject(', 'async function runEditorAction(')))
        current_test_source="""
const assert=require('node:assert/strict');
const window={};let currentUnsavedChanges=true,currentBusyState=false;
const currentCommandRecords=[];let currentStatusText='';
function stopEditorPlayback(){} function refreshEditorAvailability(){}
function writeEditorStatus(currentMessageText){currentStatusText=currentMessageText;}
async function requestEditorCommand(currentCommandName,currentPayloadRecord){currentCommandRecords.push([currentCommandName,currentPayloadRecord]);return {id:'created-fixture'};}
async function loadEditorProject(currentProjectIdentifier){currentCommandRecords.push(['load',currentProjectIdentifier]);}
async function refreshEditorProjects(){}
"""+'let currentPendingConfirmation='+current_confirmation_source+current_action_source+"""
(async()=>{
 const currentCancelledAction=runEditorAction(()=>createEditorProject('원래 대상',384),true);
 assert.equal(currentBusyState,true);assert.equal(currentCommandRecords.length,0);
 const currentCancelledId=window.spriteV2ConfirmationState().id;
 window.spriteV2ResolveConfirmation(currentCancelledId,false);await currentCancelledAction;
 assert.equal(currentCommandRecords.length,0);assert.equal(currentUnsavedChanges,true);assert.equal(currentBusyState,false);
 assert.match(currentStatusText,/취소/);
 const currentAcceptedAction=runEditorAction(()=>createEditorProject('확인 대상',256),true);
 const currentAcceptedId=window.spriteV2ConfirmationState().id;
 assert.notEqual(currentAcceptedId,currentCancelledId);
 assert.throws(()=>window.spriteV2ResolveConfirmation(currentCancelledId,true),/변경/);
 assert.equal(currentCommandRecords.length,0);
 assert.match(window.spriteV2ConfirmationState().message,/확인 대상.*256px/);
 window.spriteV2ResolveConfirmation(currentAcceptedId,true);
 assert.throws(()=>window.spriteV2ResolveConfirmation(currentAcceptedId,true),/변경/);
 await currentAcceptedAction;
 assert.deepEqual(currentCommandRecords,[['create',{name:'확인 대상',cellSize:256}],['load','created-fixture']]);
 assert.equal(currentBusyState,false);assert.equal(window.spriteV2ConfirmationState(),null);
 currentCommandRecords.length=0;
 await runEditorAction(()=>createEditorProject('수정 없음',384),true);
 assert.equal(currentCommandRecords.length,2);assert.equal(window.spriteV2ConfirmationState(),null);
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
"""
        current_test_result=subprocess.run(['node','-e',current_test_source],capture_output=True,text=True,timeout=20)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_load_revision_cancel_failure_and_retry(self):
        current_source_path=Path(__file__).resolve().parents[1]/'ui/character_animation/sprite-editor-v2.js'
        current_browser_source=current_source_path.read_text()
        current_confirmation_source='let currentPendingConfirmation='+current_browser_source.split('let currentPendingConfirmation=')[1].split('window.spriteV2ReadinessControls=')[0]
        current_action_source='\n'.join(current_line for current_line in current_browser_source.splitlines() if current_line.startswith(('async function loadEditorProject(', 'async function runEditorAction(')))
        current_test_source="""
const assert=require('node:assert/strict');const window={};
let currentUnsavedChanges=true,currentBusyState=false,currentStatusText='',currentFailureMode=false,currentHistoryFailure=false;
let currentProjectIdentifier='original',currentProjectDocument={frames:[{id:'original-frame'}]},currentParentRevision='original-revision',currentFrameIndex=2,currentLoadedRevision='original-revision';
let currentRevisionChoices=[['원래 수정본','original-revision']];
const currentUndoRecords=['original-undo'],currentSelectedFrames=new Set(['original-frame']),currentCommandRecords=[];
const currentOriginalDocument=currentProjectDocument;
function stopEditorPlayback(){} function refreshEditorAvailability(){} function refreshEditorScreen(){}
function writeEditorStatus(currentMessageText){currentStatusText=currentMessageText;}
function findEditorElement(){return null;} async function cacheEditorImage(){}
async function readEditorHistoryChoices(currentTargetIdentifier){currentCommandRecords.push(['history',currentTargetIdentifier]);if(currentHistoryFailure)throw Error('격리된 이력 실패');return [['새 수정본','revision-3']];}
function renderEditorHistoryChoices(){}
async function requestEditorCommand(currentCommandName,currentPayloadRecord){
 currentCommandRecords.push([currentCommandName,currentPayloadRecord]);
 if(currentFailureMode)throw Error('격리된 연결 실패');
 return {images:{},document:{frames:[{id:'target-frame'}]},latest:'latest-revision',revision:currentPayloadRecord.revision};
}
"""+current_confirmation_source+current_action_source+"""
(async()=>{
 const currentCancelledAction=runEditorAction(()=>loadEditorProject('target','revision-2'),true);
 assert.match(window.spriteV2ConfirmationState().message,/target.*revision-2/);
 window.spriteV2ResolveConfirmation(window.spriteV2ConfirmationState().id,false);
 await currentCancelledAction;
 assert.equal(currentCommandRecords.length,0);assert.equal(currentProjectDocument,currentOriginalDocument);
 assert.equal(currentLoadedRevision,'original-revision');assert.equal(currentUnsavedChanges,true);
 currentFailureMode=true;
 const currentFailedAction=runEditorAction(()=>loadEditorProject('target','revision-2'),true);
 window.spriteV2ResolveConfirmation(window.spriteV2ConfirmationState().id,true);
 await assert.rejects(currentFailedAction,/격리된 연결 실패/);
 assert.equal(currentProjectDocument,currentOriginalDocument);assert.equal(currentUnsavedChanges,true);
 assert.deepEqual(currentUndoRecords,['original-undo']);assert.equal(currentBusyState,false);
 assert.equal(window.spriteV2ConfirmationState(),null);
 currentFailureMode=false;currentHistoryFailure=true;
 const currentHistoryFailedAction=runEditorAction(()=>loadEditorProject('target','revision-2'),true);
 window.spriteV2ResolveConfirmation(window.spriteV2ConfirmationState().id,true);
 await assert.rejects(currentHistoryFailedAction,/격리된 이력 실패/);
 assert.equal(currentProjectDocument,currentOriginalDocument);assert.equal(currentUnsavedChanges,true);
 assert.equal(currentLoadedRevision,'original-revision');assert.equal(currentProjectIdentifier,'original');
 assert.deepEqual(currentRevisionChoices,[['원래 수정본','original-revision']]);
 assert.deepEqual(currentUndoRecords,['original-undo']);assert.equal(currentBusyState,false);
 currentHistoryFailure=false;currentCommandRecords.length=0;
 const currentRetriedAction=runEditorAction(()=>loadEditorProject('target','revision-3'),true);
 window.spriteV2ResolveConfirmation(window.spriteV2ConfirmationState().id,true);
 await currentRetriedAction;
 assert.deepEqual(currentCommandRecords,[['load',{id:'target',revision:'revision-3'}],['history','target']]);
 assert.equal(currentProjectIdentifier,'target');assert.equal(currentLoadedRevision,'revision-3');
 assert.equal(currentFrameIndex,0);assert.equal(currentUnsavedChanges,false);assert.equal(currentBusyState,false);
 assert.equal(currentUndoRecords.length,0);assert.equal(currentSelectedFrames.size,0);
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
"""
        current_test_result=subprocess.run(['node','-e',current_test_source],capture_output=True,text=True,timeout=20)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)
