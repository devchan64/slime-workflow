"""운영 작업 없이 브라우저 확인의 취소·대상 보존·중복 방지를 검증한다."""
from pathlib import Path
import subprocess
import unittest

import gradio as gr

from tools.review.common.gradio_browser_confirmation import build_browser_confirmation


class SpriteBrowserConfirmationTests(unittest.TestCase):
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
