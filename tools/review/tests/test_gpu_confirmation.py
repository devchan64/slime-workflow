"""Gradio 확인 단계는 승인 시에만 생성 명령을 전달한다."""
import unittest
from unittest.mock import Mock
import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation

class GpuConfirmationTests(unittest.TestCase):
    def test_external_readiness_success_respects_pending_confirmation(self):
        current_generation_mock = Mock()
        with gr.Blocks() as current_interface_blocks:
            current_ready_state = gr.State(False)
            current_refresh_event = gr.Button('조회').click(lambda: True, outputs=current_ready_state)
            current_generate_button = gr.Button('생성', interactive=False)
            bind_gpu_generation_confirmation(current_generate_button, current_generation_mock, gr.Textbox(), gr.Textbox(),
                generation_readiness_callback=lambda current_ready_value: current_ready_value,
                generation_readiness_inputs=[current_ready_state], generation_readiness_events=[current_refresh_event])
        current_dependencies = current_interface_blocks.get_config_file()['dependencies']
        current_success_events = [current_dependency for current_dependency in current_dependencies if current_dependency.get('trigger_after') == current_refresh_event['id']]
        self.assertEqual(len(current_success_events), 1)
        self.assertTrue(current_success_events[0]['trigger_only_on_success'])
        current_readiness_callback = current_interface_blocks.fns[current_success_events[0]['id']].fn
        self.assertTrue(current_readiness_callback(None, True)['interactive'])
        self.assertFalse(current_readiness_callback(None, False)['interactive'])
        self.assertFalse(current_readiness_callback({'inputs': ('saved',), 'consumed': False}, True)['interactive'])
        current_generation_mock.assert_not_called()

    def test_confirmation_observation_reports_unknown_and_discards_old_result(self):
        import subprocess
        from tools.review.common.gradio_gpu_confirmation import build_gpu_confirmation_observation_script
        current_script_value=build_gpu_confirmation_observation_script('test-group','test-status')
        current_harness_code=r"""
const assert=require('node:assert/strict');
const currentStatus={dataset:{},textContent:''};
global.document={getElementById:id=>id==='test-status'?currentStatus:{scrollIntoView:()=>{}}};
global.requestAnimationFrame=fn=>fn();let currentNextToken=0;global.crypto={randomUUID:()=>String(++currentNextToken)};
const currentAction=SCRIPT;
(async()=>{
 global.fetch=async()=>({ok:true,json:async()=>({jobs:[],gpu_status:{status:'idle',processes:[]}})});
 await currentAction();assert.match(currentStatus.textContent,/GPU 프로세스 관측 없음.*대기 작업 0건/);
 global.fetch=async()=>({ok:true,json:async()=>({jobs:[{service:'kimodo',id:'job'}],gpu_status:{status:'busy',processes:[{pid:1}]}})});
 await currentAction();assert.match(currentStatus.textContent,/GPU 프로세스 1개 관측.*대기 작업 1건/);
 for(const currentBadRecord of [{jobs:[],gpu_status:{status:'unavailable',processes:[]}},{jobs:[],gpu_status:{status:'idle',processes:[{}]}},{jobs:[{}],gpu_status:{status:'idle',processes:[]}}]){
  global.fetch=async()=>({ok:true,json:async()=>currentBadRecord});await currentAction();assert.match(currentStatus.textContent,/상태 확인 불가/);
 }
 global.fetch=async()=>({ok:false});await currentAction();assert.match(currentStatus.textContent,/상태 확인 불가/);
 let currentReleaseOld;global.fetch=()=>new Promise(resolve=>{currentReleaseOld=resolve});const currentOldRequest=currentAction();
 global.fetch=async()=>({ok:true,json:async()=>({jobs:[],gpu_status:{status:'idle',processes:[]}})});await currentAction();
 currentReleaseOld({ok:true,json:async()=>({jobs:[{service:'kimodo',id:'job'}],gpu_status:{status:'busy',processes:[{pid:1}]}})});await currentOldRequest;
 assert.match(currentStatus.textContent,/GPU 프로세스 관측 없음/);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SCRIPT',current_script_value)
        current_result_value=subprocess.run(['node','-e',current_harness_code],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result_value.returncode,0,current_result_value.stderr)

    def test_confirmation_explains_external_gpu_overlap(self):
        with gr.Blocks() as current_interface:
            bind_gpu_generation_confirmation(gr.Button('생성'), Mock(), gr.Textbox(), gr.Textbox())
        current_markdown_values=[current_component.get('props',{}).get('value','') for current_component in current_interface.config['components'] if current_component.get('type')=='markdown']
        current_notice_text=' '.join(current_value for current_value in current_markdown_values if isinstance(current_value,str))
        self.assertIn('GPU 사용 중에도',current_notice_text)
        self.assertIn('외부 GPU 작업',current_notice_text)
        self.assertNotIn('GPU가 사용 중이면 대기',current_notice_text)

    def test_confirmation_and_cancel_preserve_generation_boundary(self):
        generation_callback_mock = Mock(return_value='accepted')
        with gr.Blocks() as interface_blocks_value:
            bind_gpu_generation_confirmation(gr.Button('생성'), generation_callback_mock, gr.Textbox(), gr.Textbox())
        callback_function_values = {record.fn.__name__: record.fn for record in interface_blocks_value.fns.values() if record.fn}
        pending_input_values = callback_function_values['prepare_generation_confirmation']('original')[0]
        generation_callback_mock.assert_not_called()
        self.assertIsNone(callback_function_values['cancel_generation_confirmation'](pending_input_values)[0])
        generation_callback_mock.assert_not_called()
        with self.assertRaises(gr.Error):
            list(callback_function_values['execute_confirmed_generation'](pending_input_values))
        pending_input_values = callback_function_values['prepare_generation_confirmation']('original')[0]
        self.assertEqual(list(callback_function_values['execute_confirmed_generation'](pending_input_values)), ['accepted'])
        with self.assertRaises(gr.Error):
            list(callback_function_values['execute_confirmed_generation'](pending_input_values))
        generation_callback_mock.assert_called_once_with('original')

    def test_missing_confirmation_rejected(self):
        with gr.Blocks() as interface_blocks_value:
            bind_gpu_generation_confirmation(gr.Button('생성'), Mock(), gr.Textbox(), gr.Textbox())
        callback_function_value = next(record.fn for record in interface_blocks_value.fns.values() if record.fn and record.fn.__name__ == 'execute_confirmed_generation')
        with self.assertRaises(gr.Error):
            list(callback_function_value(None))

    def test_reference_readiness_preserves_pending_lock_and_current_inputs(self):
        current_generation_callback = Mock(return_value='accepted')
        with gr.Blocks() as current_interface_blocks:
            current_reference_controls = [gr.Textbox(), gr.Textbox()]
            bind_gpu_generation_confirmation(gr.Button('생성', interactive=False), current_generation_callback,
                current_reference_controls, gr.Textbox(),
                generation_readiness_callback=lambda *current_reference_values: all(current_reference_values),
                generation_readiness_inputs=current_reference_controls)
        current_callback_functions = {current_function_record.fn.__name__: current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn}
        current_readiness_callback = current_callback_functions['refresh_generation_readiness']
        self.assertFalse(current_readiness_callback(None, '', '')['interactive'])
        self.assertFalse(current_readiness_callback(None, 'identity', '')['interactive'])
        self.assertTrue(current_readiness_callback(None, 'identity', 'pose')['interactive'])
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('identity', 'pose')[0]
        self.assertFalse(current_readiness_callback(current_pending_inputs, 'changed', 'pose')['interactive'])
        self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs)), ['accepted'])
        current_generation_callback.assert_called_once_with('identity', 'pose')
        self.assertFalse(current_readiness_callback(current_pending_inputs, 'changed', 'pose')['interactive'])
        current_cancel_result = current_callback_functions['cancel_generation_confirmation'](current_pending_inputs, 'identity', '')
        self.assertFalse(current_cancel_result[2]['interactive'])
        self.assertTrue(current_callback_functions['cancel_generation_confirmation'](None, 'identity', 'pose')[2]['interactive'])

    def test_confirmation_rejects_input_changed_while_open(self):
        current_generation_callback = Mock(return_value='accepted')
        with gr.Blocks() as current_interface_blocks:
            current_prompt_control = gr.Textbox()
            bind_gpu_generation_confirmation(gr.Button('생성'), current_generation_callback, [current_prompt_control], gr.Textbox(), generation_confirmation_validator=lambda current_saved, current_live: current_saved == current_live, generation_confirmation_inputs=[current_prompt_control])
        current_callback_functions = {current_function_record.fn.__name__: current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn}
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('first')[0]
        with self.assertRaises(gr.Error):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs, 'changed'))
        current_generation_callback.assert_not_called()
        with self.assertRaises(gr.Error):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs, 'first'))
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('second')[0]
        self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs, 'second')), ['accepted'])
        current_generation_callback.assert_called_once_with('second')

    def test_failed_submission_releases_confirmation_for_new_inputs(self):
        current_generation_callback = Mock(side_effect=[ValueError('입력 검증 실패'), 'accepted'])
        with gr.Blocks() as current_interface_blocks:
            bind_gpu_generation_confirmation(gr.Button('생성'), current_generation_callback, gr.Textbox(), gr.Textbox())
        current_callback_functions = {current_function_record.fn.__name__: current_function_record.fn for current_function_record in current_interface_blocks.fns.values() if current_function_record.fn}
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('invalid')[0]
        with self.assertRaisesRegex(ValueError, '입력 검증 실패'):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))
        with self.assertRaises(gr.Error):
            list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs))
        current_failure_events = [current_event_record for current_event_record in current_interface_blocks.get_config_file()['dependencies'] if current_event_record.get('trigger_only_on_failure')]
        self.assertEqual(len(current_failure_events), 1)
        current_failure_callback = current_interface_blocks.fns[current_failure_events[0]['id']].fn
        current_cleanup_result = current_failure_callback(current_pending_inputs)
        self.assertIsNone(current_cleanup_result[0])
        self.assertFalse(current_cleanup_result[1]['visible'])
        self.assertTrue(current_cleanup_result[2]['interactive'])
        current_pending_inputs = current_callback_functions['prepare_generation_confirmation']('corrected')[0]
        self.assertEqual(list(current_callback_functions['execute_confirmed_generation'](current_pending_inputs)), ['accepted'])
        self.assertEqual(current_generation_callback.call_count, 2)
        current_generation_callback.assert_called_with('corrected')
