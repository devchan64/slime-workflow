import unittest

from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface, create_anny_attribute_loader, read_anny_attribute_markup


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_history_stale_failure_preserves_new_selection(self):
        import subprocess
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_history_script=next(current_event['js'] for current_event in current_configuration_record['dependencies'] if 'currentRefreshState' in (current_event.get('js') or '') and '"inspect"' in current_event['js'])
        current_browser_script="""
const assert=require('node:assert/strict');
const currentPendingRequests=[];
const window={annyHistoryControls:(currentActionName,currentSelectedId)=>new Promise((resolve,reject)=>currentPendingRequests.push({id:currentSelectedId,resolve,reject}))};
const inspectCurrentHistory=SOURCE;
(async()=>{
 const currentOlderRequest=inspectCurrentHistory('old',true);
 const currentNewerRequest=inspectCurrentHistory('new',true);
 currentPendingRequests[1].resolve(['new','new',{id:'new'},'new log','new selected']);
 assert.equal((await currentNewerRequest)[1],'new');
 currentPendingRequests[0].reject(Error('old failed'));
 assert.deepEqual(await currentOlderRequest,Array.from({length:5},()=>({__type__:'update'})));
 const currentLatestRequest=inspectCurrentHistory('latest',true);
 currentPendingRequests[2].reject(Error('latest failed'));
 assert.deepEqual(await currentLatestRequest,[{__type__:'update'},'latest',null,'','latest failed']);
})().catch(currentError=>{console.error(currentError);process.exitCode=1;});
""".replace('SOURCE',current_history_script)
        current_process_result=subprocess.run(['node','-e',current_browser_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)

    def test_loader_reports_dependency_failure_without_starting_inline_script(self):
        import subprocess
        current_loader_source=create_anny_attribute_loader(8798)
        current_browser_script="""
const assert=require('node:assert/strict');
const window={};const currentStatusElement={textContent:''};let currentAppendedCount=0,currentFailurePath='log-viewer.js';
const document={querySelector:currentSelector=>currentSelector==='#anny-attribute-root #status'?currentStatusElement:null,createElement:()=>({dataset:{}}),body:{append:currentElement=>{currentAppendedCount++;if(currentElement.src?.endsWith(currentFailurePath))currentElement.onerror();else currentElement.onload?.();}}};
const runCurrentLoader=SOURCE;
(async()=>{
 await runCurrentLoader();assert.equal(currentAppendedCount,1);assert.match(window.annyComponentLoadError,/log-viewer.js.*새로고침/);assert.equal(currentStatusElement.textContent,window.annyComponentLoadError);
 currentFailurePath='mesh-viewer.js';currentAppendedCount=0;await runCurrentLoader();assert.equal(currentAppendedCount,2);assert.match(currentStatusElement.textContent,/mesh-viewer.js.*새로고침/);
 currentFailurePath='none';await runCurrentLoader();assert.match(currentStatusElement.textContent,/초기화에 실패.*새로고침/);
})().catch(currentError=>{console.error(currentError);process.exitCode=1;});
""".replace('SOURCE',current_loader_source)
        current_process_result=subprocess.run(['node','-e',current_browser_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)

    def test_profile_latest_selection_survives_out_of_order_responses(self):
        import subprocess
        from tools.review.ui.gradio.anny_attributes_app import read_anny_attribute_script
        current_source_text=read_anny_attribute_script()
        current_profile_source='let currentProfileRequestSequence='+current_source_text.split('let currentProfileRequestSequence=',1)[1].split('window.prepareAnnyGenerationInput=',1)[0]
        current_browser_script="""
const assert=require('node:assert/strict');const window={};
let baselineAttributeValues={profile:{profile_id:'initial'}},currentRestoreCount=0;
const renderStatusLabel={textContent:''},currentPendingRequests=[];
function restoreAttributeDefaults(){currentRestoreCount++;}
function fetchRenderRecord(currentPathValue){return new Promise((resolve,reject)=>currentPendingRequests.push({path:currentPathValue,resolve,reject}));}
const currentProfilesRecord={profiles:[{id:'A',label:'A'},{id:'B',label:'B'}]};
const makeCurrentProfile=currentProfileId=>({profile:{profile_id:currentProfileId,label:currentProfileId}});
SOURCE
(async()=>{
 const currentFirstRequest=window.annyProfileControls('apply','A');currentPendingRequests.shift().resolve(currentProfilesRecord);await Promise.resolve();
 const currentOldRequest=currentPendingRequests.shift();assert.match(currentOldRequest.path,/base\/A$/);
 const currentSecondRequest=window.annyProfileControls('apply','B');currentPendingRequests.shift().resolve(currentProfilesRecord);await Promise.resolve();
 currentPendingRequests.shift().resolve(makeCurrentProfile('B'));await currentSecondRequest;
 currentOldRequest.resolve(makeCurrentProfile('A'));assert.deepEqual(await currentFirstRequest,[{__type__:'update'},{__type__:'update'}]);
 assert.equal(baselineAttributeValues.profile.profile_id,'B');assert.equal(currentRestoreCount,1);
 const currentFailedRequest=window.annyProfileControls('apply','A');currentPendingRequests.shift().resolve(currentProfilesRecord);await Promise.resolve();
 currentPendingRequests.shift().reject(Error('연결 실패'));await assert.rejects(currentFailedRequest,/연결 실패/);
 assert.equal(baselineAttributeValues.profile.profile_id,'B');assert.equal(currentRestoreCount,1);
 const currentListingRequest=window.annyProfileControls('list',null);const currentOldList=currentPendingRequests.shift();
 const currentThirdRequest=window.annyProfileControls('apply','A');currentPendingRequests.shift().resolve(currentProfilesRecord);await Promise.resolve();currentPendingRequests.shift().resolve(makeCurrentProfile('A'));await currentThirdRequest;
 currentOldList.reject(Error('오래된 목록 실패'));assert.deepEqual(await currentListingRequest,[{__type__:'update'},{__type__:'update'}]);assert.equal(baselineAttributeValues.profile.profile_id,'A');
 baselineAttributeValues=null;await assert.rejects(window.annyProfileControls('apply','A'),/준비가 끝난 뒤/);assert.equal(currentPendingRequests.length,0);
})().catch(currentError=>{console.error(currentError);process.exitCode=1;});
""".replace('SOURCE',current_profile_source)
        current_process_result=subprocess.run(['node','-e',current_browser_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)

    def test_numeric_readiness_rejects_unprepared_unknown_and_locked_fields(self):
        import subprocess
        from tools.review.ui.gradio.anny_attributes_app import read_anny_attribute_script
        current_source_text=read_anny_attribute_script()
        current_readiness_source=current_source_text.split('window.annyNumericReadiness=',1)[1].split('window.annyNumericControls=',1)[0]
        current_browser_script="""
const assert=require('node:assert/strict');
let baselineAttributeValues=null;const currentAttributeValues={};
const attributeFieldSpecs=[['age'],['hip-waist-up']];
const readCurrentReadiness=SOURCE
assert.equal(readCurrentReadiness('age').readReady,false);
baselineAttributeValues={};currentAttributeValues.age=0.5;
assert.equal(readCurrentReadiness(null).readReady,true);
assert.equal(readCurrentReadiness(null).applyReady,false);
assert.equal(readCurrentReadiness('unknown').applyReady,false);
assert.equal(readCurrentReadiness('age').applyReady,true);
assert.equal(readCurrentReadiness('hip-waist-up').applyReady,false);
assert.match(readCurrentReadiness('hip-waist-up').reason,/잠긴 속성/);
""".replace('SOURCE',current_readiness_source)
        current_process_result=subprocess.run(['node','-e',current_browser_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
        current_interface_config=build_anny_attribute_interface(8770).get_config_file()
        current_ready_event=next(current_event_record for current_event_record in current_interface_config['dependencies'] if 'window.annyNumericReadiness' in (current_event_record.get('js') or ''))
        self.assertFalse(current_ready_event['backend_fn'])
        self.assertFalse(current_ready_event['queue'])
        current_component_lookup={current_component_record['id']:current_component_record for current_component_record in current_interface_config['components']}
        for current_button_identifier in current_ready_event['outputs'][:2]:
            self.assertFalse(current_component_lookup[current_button_identifier]['props']['interactive'])

    def test_delete_confirmation_accepts_browser_choices_and_serializes_target(self):
        import gradio as gr
        current_interface_value=build_anny_attribute_interface(8770)
        current_open_functions=[current_function for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='open_file_confirmation']
        current_delete_function=next(current_function for current_function in current_open_functions if current_function.fn.__defaults__==('delete',))
        self.assertFalse(current_delete_function.preprocess)
        current_confirmation_result=current_delete_function.fn('isolated-history')
        self.assertEqual(current_confirmation_result[1],'delete')
        self.assertEqual(current_confirmation_result[2],{'id':'isolated-history'})
        self.assertIsInstance(current_delete_function.outputs[1],gr.Textbox)
        self.assertIsInstance(current_delete_function.outputs[2],gr.JSON)
        self.assertEqual(current_delete_function.outputs[2].postprocess(current_confirmation_result[2]).root,{'id':'isolated-history'})
        for current_invalid_identifier in (None, '', ' ', [], {}):
            with self.subTest(identifier=current_invalid_identifier),self.assertRaises(gr.Error):
                current_delete_function.fn(current_invalid_identifier)

    def test_status_view_uses_shared_service_values(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_status_function=next(current_function for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='render_anny_generation_status')
        current_display_text=current_status_function.fn({'status':'running','metrics':{'gpu_observations':{'GPU-test':{'process_current_mib':100,'process_peak_mib':200,'scope':'작업 및 자식 프로세스'}}}})
        self.assertIn('200 MiB',current_display_text)
        self.assertIn('계산 중',current_display_text)
        self.assertIn('window.annyGenerationStatus',str(current_interface_value.get_config_file()))

    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_anny_attribute_interface(8770)
        configuration_value = interface_blocks_value.get_config_file()
        self.assertIn('anny-attribute-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))
        self.assertNotIn('<dialog', read_anny_attribute_markup())
        self.assertNotIn('attribute-direct-input-form', read_anny_attribute_markup())
        self.assertIn('속성값 적용', str(configuration_value))
        self.assertIn('## Anny 속성 렌더러', str(configuration_value))
        self.assertNotIn('<h1>', read_anny_attribute_markup())

    def test_actions_are_native_browser_commands(self):
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_action_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'annyAttributeActions' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_action_events),1)
        for current_event_record in current_action_events:
            self.assertFalse(current_event_record['backend_fn'])
        current_markup_text=read_anny_attribute_markup()
        for current_button_identifier in ('reset','generate-preview','retry'):
            self.assertNotIn('id="'+current_button_identifier+'"',current_markup_text)
        self.assertIn('aria-live="polite"',current_markup_text)

    def test_uses_selected_history_actions(self):
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_history_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'annyHistoryControls' in (current_event_record.get('js') or '')]
        for current_expected_action in ('list','result','restore','logs','resume','cancel','delete','reset','inspect','prioritize'):
            self.assertTrue(any('\"'+current_expected_action+'\"' in current_event_record['js'] for current_event_record in current_history_events), current_expected_action)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_history_events))
        self.assertNotIn('id="generation-history"',read_anny_attribute_markup())
        self.assertIn('선택한 생성 ID',str(current_configuration_record))
        self.assertIn('이력 수동 정리',str(current_configuration_record))

    def test_only_user_selection_invalidates_file_confirmation(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_configuration_record=current_interface_value.get_config_file()
        current_selection_identifier=next(current_component['id'] for current_component in current_configuration_record['components'] if current_component['props'].get('label')=='이력 선택 · ID·상태 검색')
        current_selection_events=[current_event for current_event in current_configuration_record['dependencies'] if any(current_target[0]==current_selection_identifier for current_target in current_event['targets'])]
        self.assertTrue(current_selection_events)
        self.assertTrue(all(current_target[1]=='input' for current_event in current_selection_events for current_target in current_event['targets']))

    def test_selected_actions_follow_job_status(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_callback_value=next(current_function.fn for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='update_browser_history_actions')
        for current_status_name,current_expected_values in [('queued',[False,True,False,True,True,False]),('running',[False,True,False,False,True,False]),('completed',[True,True,False,False,False,True]),('failed',[False,True,True,False,False,True]),('paused',[False,True,False,False,False,True])]:
            with self.subTest(status=current_status_name):
                current_button_updates=current_callback_value({'status':{'status':current_status_name}})
                self.assertEqual([current_update_record['interactive'] for current_update_record in current_button_updates],[True,*current_expected_values])
        self.assertTrue(current_callback_value({'status':{'status':'running'},'preview_ready':True})[1]['interactive'])
        self.assertTrue(all(not current_update_record['interactive'] for current_update_record in current_callback_value(None)))

    def test_loader_preserves_attribute_component_dependencies(self):
        loader_script_text=create_anny_attribute_loader(8770)
        self.assertIn("http://127.0.0.1:8770'+currentPathValue",loader_script_text)
        self.assertIn('/anny-attributes/mesh-viewer.js',loader_script_text)
        self.assertNotIn('/anny-attributes/history-ui.js',loader_script_text)
        self.assertIn('mesh-preview',read_anny_attribute_markup())
        self.assertNotIn('/management/workflow-ui.js',loader_script_text)
        self.assertNotIn('id="baseline-profile"',read_anny_attribute_markup())
        self.assertNotIn('id="render-rotation-y"',read_anny_attribute_markup())

    def test_reset_confirmation_preserves_preview_and_rejects_busy(self):
        from unittest.mock import patch
        import gradio as gr
        current_interface_value=build_anny_attribute_interface(8770)
        current_reset_function=next(current_function for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='open_file_confirmation' and current_function.fn.__defaults__==('reset',))
        current_preview_record={'can_reset':True,'job_count':2,'notice':'격리 작업 파일 삭제','jobs':[{'id':'a'},{'id':'b'}]}
        with patch('tools.review.common.gradio_browser_history.execute_remote_management_command',return_value=current_preview_record) as current_gateway_mock:
            current_confirmation_result=current_reset_function.fn(None)
        current_gateway_mock.assert_called_once_with('anny','history-reset-preview',{})
        self.assertEqual(current_confirmation_result[2],current_preview_record)
        self.assertEqual(current_reset_function.outputs[2].postprocess(current_confirmation_result[2]).root,current_preview_record)
        self.assertIn('2개 작업',current_confirmation_result[3])
        with patch('tools.review.common.gradio_browser_history.execute_remote_management_command',return_value={**current_preview_record,'can_reset':False}):
            with self.assertRaisesRegex(gr.Error,'실행·대기'):
                current_reset_function.fn(None)

    def test_browser_confirmation_passes_snapshot_and_rejects_changed_selection(self):
        import subprocess
        current_interface_value=build_anny_attribute_interface(8770)
        current_confirmation_script=next(current_event_record['js'] for current_event_record in current_interface_value.get_config_file()['dependencies'] if '삭제 확인이 만료되었습니다.' in (current_event_record.get('js') or ''))
        current_test_script="""
const assert=require('node:assert/strict');const currentCalls=[];
global.window={annyHistoryControls:async(...currentArguments)=>{currentCalls.push(currentArguments);return [null,'',null,'','모의 완료'];}};
const currentConfirmAction=SCRIPT;
(async()=>{
 await currentConfirmAction('b',false,'delete',{id:'a'});assert.equal(currentCalls.length,0);
 await currentConfirmAction('a',false,'',{id:'a'});assert.equal(currentCalls.length,0);
 await currentConfirmAction('a',false,'delete',{id:'a'});
 assert.equal(currentCalls[0][0],'delete');assert.deepEqual(currentCalls[0][2],{confirmed:true,id:'a',preview:null});
 const currentPreviewRecord={can_reset:true,job_count:2,jobs:[{id:'a'},{id:'b'}]};
 await currentConfirmAction(null,false,'reset',currentPreviewRecord);
 assert.equal(currentCalls[1][0],'reset');assert.deepEqual(currentCalls[1][2].preview,currentPreviewRecord);
})().catch(currentTestError=>{console.error(currentTestError);process.exitCode=1;});
""".replace('SCRIPT',current_confirmation_script)
        current_test_result=subprocess.run(['node','-e',current_test_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)


if __name__ == '__main__':
    unittest.main()
