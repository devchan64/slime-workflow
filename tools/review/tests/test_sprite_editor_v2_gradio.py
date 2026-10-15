"""v2의 일반 작업 컨트롤과 브라우저 편집기 연결을 검증한다."""
import json
import subprocess
from pathlib import Path
import unittest
from tools.review.ui.gradio.sprite_editor_v2_app import build_sprite_v2_interface, create_sprite_project_script


class SpriteV2GradioTests(unittest.TestCase):
    def test_readiness_updates_stay_in_browser(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_ready_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2ReadinessControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_ready_events),1)
        current_ready_event=current_ready_events[0]
        self.assertFalse(current_ready_event['backend_fn'])
        self.assertFalse(current_ready_event['queue'])
        current_component_lookup={current_component_record['id']:current_component_record for current_component_record in current_interface_config['components']}
        self.assertEqual(len(current_ready_event['outputs']),36)
        for current_control_id in current_ready_event['outputs'][:-3]:
            self.assertFalse(current_component_lookup[current_control_id]['props']['interactive'])
        self.assertIn('작업을 생성하거나 불러오세요',current_component_lookup[current_ready_event['outputs'][-1]]['props']['value'])

    def test_edit_readiness_distinguishes_empty_and_populated_projects(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_ready_event=next(current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2ReadinessControls' in (current_event_record.get('js') or ''))
        current_browser_script="const currentUpdateFunction=("+current_ready_event['js']+"); global.window={}; const currentResults=[]; for(const currentReadyRecord of [{projectReady:false,framesReady:false,reason:'없음'},{projectReady:true,framesReady:false,reason:'빈 작업'},{projectReady:true,framesReady:true,reason:'프레임 있음'},{projectReady:false,framesReady:false,reason:'처리 중'}]) {window.spriteV2ReadinessControls=()=>currentReadyRecord; currentResults.push(currentUpdateFunction());} console.log(JSON.stringify(currentResults));"
        current_command_result=subprocess.run(['node','-e',current_browser_script],check=True,capture_output=True,text=True)
        current_update_results=json.loads(current_command_result.stdout)
        for current_result_index,current_expected_flags in enumerate(((False,False),(True,False),(True,True),(False,False))):
            current_output_values=current_update_results[current_result_index]
            self.assertEqual(len(current_output_values),len(current_ready_event['outputs']))
            self.assertEqual([current_output_value['interactive'] for current_output_value in current_output_values[:2]],[current_expected_flags[0]]*2)
            self.assertEqual([current_output_value['interactive'] for current_output_value in current_output_values[2:15]],[current_expected_flags[1]]*13)
            self.assertTrue(all(not current_output_value['interactive'] for current_output_value in current_output_values[15:33]))

    def test_target_readiness_matches_image_selection_and_undo(self):
        current_source_text=(Path(__file__).parents[1]/'ui/character_animation/sprite-editor-v2.js').read_text()
        current_collect_source=next(current_source_line for current_source_line in current_source_text.splitlines() if current_source_line.startswith('function collectEditorTargets('))
        current_ready_source=current_source_text.split('window.spriteV2ReadinessControls=',1)[1].split('function refreshEditorAvailability',1)[0]
        current_browser_script="""
const assert=require('node:assert/strict');
let currentProjectDocument=null,currentBusyState=false,currentEditorMode='guide',currentEditorTarget='frame',currentFrameIndex=0;
const currentSelectedFrames=new Set(),currentUndoRecords=[];
COLLECT
const readCurrentReadiness=READY
assert.equal(readCurrentReadiness().targetReady,false);
currentProjectDocument={reference:null,frames:[{id:'one'}]};
assert.equal(readCurrentReadiness().targetReady,true);
currentEditorTarget='reference';assert.equal(readCurrentReadiness().targetReady,false);
currentEditorTarget='selected';assert.equal(readCurrentReadiness().targetReady,false);
currentSelectedFrames.add('one');assert.equal(readCurrentReadiness().targetReady,true);
assert.equal(readCurrentReadiness().undoReady,false);
currentUndoRecords.push({});assert.equal(readCurrentReadiness().undoReady,true);
currentBusyState=true;assert.equal(readCurrentReadiness().targetReady,false);assert.equal(readCurrentReadiness().undoReady,false);
""".replace('COLLECT',current_collect_source).replace('READY',current_ready_source)
        current_command_result=subprocess.run(['node','-e',current_browser_script],capture_output=True,text=True)
        self.assertEqual(current_command_result.returncode,0,current_command_result.stderr)

    def test_shared_joypad_preserves_existing_consumer_contract(self):
        import gradio as gr
        from tools.review.common.gradio_joypad import build_transform_joypad
        for current_scale_enabled,current_axes_separate,current_expected_buttons in ((False,False,7),(True,False,10),(True,True,17)):
            for current_readiness_requested in (False,True):
                with self.subTest(scale=current_scale_enabled,separate=current_axes_separate,readiness=current_readiness_requested):
                    current_readiness_controls=[] if current_readiness_requested else None
                    with gr.Blocks() as current_test_blocks:
                        current_feedback_output=gr.Textbox()
                        current_input_controls=build_transform_joypad('testJoypadControls',current_feedback_output,current_scale_enabled,current_axes_separate,current_readiness_controls)
                    current_interface_config=current_test_blocks.get_config_file()
                    current_buttons_records=[current_component_record for current_component_record in current_interface_config['components'] if current_component_record['type']=='button']
                    self.assertEqual(len(current_buttons_records),current_expected_buttons)
                    self.assertEqual(len(current_input_controls),6 if current_axes_separate else 5)
                    self.assertTrue(all(current_button_record['props']['interactive']==(not current_readiness_requested) for current_button_record in current_buttons_records))
                    if current_readiness_requested:self.assertEqual(len(current_readiness_controls),current_expected_buttons)
                    for current_event_record in current_interface_config['dependencies']:
                        self.assertFalse(current_event_record['backend_fn'])
                        self.assertEqual(len(current_event_record['outputs']),5 if current_axes_separate else 4)

    def test_reference_delete_uses_browser_command(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_delete_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2ImageDeleteControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_delete_events),1)
        self.assertFalse(current_delete_events[0]['backend_fn'])
        self.assertFalse(current_delete_events[0]['queue'])

    def test_project_controls_are_native_and_canvas_is_preserved(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_html_markup=''.join(current_component_record['props'].get('value','') for current_component_record in current_interface_config['components'] if current_component_record['type']=='html')
        for current_removed_identifier in ('sv2-edit-target','sv2-mode','sv2-guide-choice','sv2-guide-label','sv2-guide-axis','sv2-x','sv2-y','sv2-scale','sv2-face-x','sv2-face-y','sv2-diameter','sv2-guide-position','sv2-name','sv2-size','sv2-fps','sv2-duration','sv2-create','sv2-project-refresh','sv2-load','sv2-projects','sv2-save','sv2-export','sv2-history','sv2-revision-load','sv2-zoom','sv2-background','sv2-overlay','sv2-onion','sv2-guides','sv2-prev','sv2-play','sv2-next','sv2-earlier','sv2-later','sv2-duplicate','sv2-remove','sv2-undo','sv2-upload','sv2-paste','sv2-upload-target','sv2-smaller','sv2-larger','sv2-face-match','sv2-guide-add','sv2-guide-vertical','sv2-guide-remove','sv2-guide-copy'):
            self.assertNotIn('id="'+current_removed_identifier+'"',current_html_markup)
        self.assertNotIn('data-sv2-move',current_html_markup)
        self.assertIn('id="sv2-reference"',current_html_markup)
        self.assertIn('id="sv2-frame"',current_html_markup)
        self.assertIn('id="sv2-timeline"',current_html_markup)
        current_dropdown_labels=[current_component_record['props'].get('label') for current_component_record in current_interface_config['components'] if current_component_record['type']=='dropdown']
        self.assertIn('새 작업 출력 크기',current_dropdown_labels)
        self.assertIn('저장된 작업',current_dropdown_labels)
        self.assertIn('수정 이력',current_dropdown_labels)
        self.assertNotIn('설정할 조절 대상',current_dropdown_labels)
        self.assertIn('화면 확대',current_dropdown_labels)
        self.assertIn('배경',current_dropdown_labels)

    def test_target_and_seek_controls_stay_in_browser(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        for current_bridge_name in ('spriteV2TargetControls','spriteV2SeekControls'):
            current_matching_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if current_bridge_name in (current_event_record.get('js') or '')]
            self.assertEqual(len(current_matching_events),2 if current_bridge_name=='spriteV2SeekControls' else 1)
            self.assertFalse(current_matching_events[0]['backend_fn'])
            self.assertFalse(current_matching_events[0]['queue'])

    def test_guide_editor_uses_native_browser_controls(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_guide_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2GuideControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_guide_events),9)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_guide_events))

    def test_circle_editor_is_part_of_guide_controls(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_component_props=[current_component_record['props'] for current_component_record in current_interface_config['components']]
        self.assertNotIn('얼굴 원 수치',[current_component_record.get('label') for current_component_record in current_component_props])
        for current_circle_label in ('원 중심 X · px','원 중심 Y · px','원 지름 · px'):
            self.assertIn(current_circle_label,[current_component_record.get('label') for current_component_record in current_component_props])
        current_apply_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2GuideControls.apply(' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_apply_events),1)
        self.assertEqual(len(current_apply_events[0]['inputs']),7)
        self.assertEqual(len(current_apply_events[0]['outputs']),8)
        self.assertFalse(current_apply_events[0]['backend_fn'])

    def test_metadata_edit_is_native_and_browser_only(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_metadata_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2MetadataControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_metadata_events),1)
        self.assertFalse(current_metadata_events[0]['backend_fn'])
        self.assertFalse(current_metadata_events[0]['queue'])
        current_size_components=[current_component_record['props'] for current_component_record in current_interface_config['components'] if current_component_record['props'].get('label')=='변경할 출력 크기']
        self.assertEqual(current_size_components[0]['value'],'keep')

    def test_timing_edit_uses_explicit_browser_only_apply(self):
        current_interface_config=build_sprite_v2_interface().get_config_file()
        current_timing_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'spriteV2TimingControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_timing_events),1)
        self.assertFalse(current_timing_events[0]['backend_fn'])
        self.assertFalse(current_timing_events[0]['queue'])
        current_timing_fields=[current_component_record['props'] for current_component_record in current_interface_config['components'] if current_component_record['type']=='number' and current_component_record['props'].get('label') in ('변경할 FPS','선택 프레임 유지 시간 · ms')]
        self.assertEqual(len(current_timing_fields),2)
        current_timing_toggles=[current_component_record['props'] for current_component_record in current_interface_config['components'] if current_component_record['type']=='checkbox' and current_component_record['props'].get('label') in ('FPS 변경','유지 시간 변경')]
        self.assertEqual(len(current_timing_toggles),2)
        self.assertTrue(all(current_toggle_record.get('value') is False for current_toggle_record in current_timing_toggles))

    def test_commands_use_browser_state_and_reject_unknown_actions(self):
        for current_action_name in ('create','list','load','history','revision','save','export','delete'):
            current_script_text=create_sprite_project_script(current_action_name)
            self.assertIn('window.spriteV2ProjectControls',current_script_text)
            self.assertNotIn('.click()',current_script_text)
        with self.assertRaises(ValueError):create_sprite_project_script('unsupported')

    def test_browser_buttons_do_not_add_server_callbacks(self):
        from tools.review.common.gradio_browser_controls import build_browser_action_button
        import gradio as gr
        with gr.Blocks() as current_test_blocks:
            current_feedback_output=gr.Textbox()
            build_browser_action_button('재생','spriteV2PlaybackControls','play',current_feedback_output)
        current_event_record=current_test_blocks.get_config_file()['dependencies'][0]
        self.assertFalse(current_event_record['backend_fn'])
        self.assertFalse(current_event_record['queue'])
        self.assertIn('spriteV2PlaybackControls',current_event_record['js'])
        with gr.Blocks():
            with self.assertRaises(ValueError):
                build_browser_action_button('잘못된 연결','handler();','play',gr.Textbox())
