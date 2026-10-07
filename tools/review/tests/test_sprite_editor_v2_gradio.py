"""v2의 일반 작업 컨트롤과 브라우저 편집기 연결을 검증한다."""
import unittest
from tools.review.ui.gradio.sprite_editor_v2_app import build_sprite_v2_interface, create_sprite_project_script


class SpriteV2GradioTests(unittest.TestCase):
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
        self.assertEqual(len(current_guide_events),8)
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
        for current_action_name in ('create','list','load','history','revision','save','export'):
            current_script_text=create_sprite_project_script(current_action_name)
            self.assertIn('window.spriteV2ProjectControls',current_script_text)
            self.assertNotIn('.click()',current_script_text)
        with self.assertRaises(ValueError):create_sprite_project_script('delete')

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
