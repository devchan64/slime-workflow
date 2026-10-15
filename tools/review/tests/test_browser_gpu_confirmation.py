"""GPU 접수는 모의 브라우저 함수로만 검증한다."""
import json
import subprocess
import unittest
import gradio as gr
from tools.review.common.gradio_browser_confirmation import bind_browser_gpu_confirmation


class BrowserGpuConfirmationTests(unittest.TestCase):
    def test_busy_cancel_confirm_snapshot_and_idle_policy(self):
        with gr.Blocks() as current_interface_value:
            current_start_button=gr.Button('시작')
            current_input_value=gr.Textbox()
            current_output_value=gr.Textbox()
            bind_browser_gpu_confirmation(current_start_button,'currentInputValue=>({value:currentInputValue})','async currentSnapshotValue=>{window.executions.push(currentSnapshotValue.value);return ["접수 완료"];}',[current_input_value],[current_output_value])
        current_script_values=[current_event_record['js'] for current_event_record in current_interface_value.get_config_file()['dependencies']]
        current_prepare_code,current_confirm_code,current_cancel_code=current_script_values
        current_harness_code='''
const assert=require('node:assert/strict');
global.window={executions:[]};let currentBusyStatus=true;
global.fetch=async()=>({ok:true,json:async()=>({jobs:currentBusyStatus?[{}]:[],gpu_status:{status:'idle',processes:[]}})});
const currentPrepareAction=PREPARE,currentConfirmAction=CONFIRM,currentCancelAction=CANCEL;
(async()=>{
 let currentPrepareResult=await currentPrepareAction('고정 입력');
 assert.equal(currentPrepareResult[1].visible,true);assert.deepEqual(window.executions,[]);
 const currentCancelledReceipt=currentPrepareResult[2];currentCancelAction(currentCancelledReceipt);
 await currentConfirmAction(currentCancelledReceipt);assert.deepEqual(window.executions,[]);
 currentPrepareResult=await currentPrepareAction('확인 입력');
 await currentConfirmAction(currentPrepareResult[2]);await currentConfirmAction(currentPrepareResult[2]);
 assert.deepEqual(window.executions,['확인 입력']);
 currentBusyStatus=false;await currentPrepareAction('유휴 입력');assert.deepEqual(window.executions,['확인 입력','유휴 입력']);
 currentBusyStatus=true;global.fetch=async()=>({ok:false});await currentPrepareAction('실패 입력');assert.equal(window.executions.length,2);
})().catch(currentErrorValue=>{console.error(currentErrorValue);process.exitCode=1;});
'''.replace('PREPARE',current_prepare_code).replace('CONFIRM',current_confirm_code).replace('CANCEL',current_cancel_code)
        current_test_result=subprocess.run(['node','-e',current_harness_code],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)
