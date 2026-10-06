"""스프라이트 편집기 Gradio 연결을 검증한다."""
import unittest

from tools.review.ui.gradio.sprite_editor_app import build_sprite_editor_interface, create_sprite_editor_loader, read_sprite_editor_markup, read_sprite_editor_styles


class SpriteEditorGradioTests(unittest.TestCase):
    def test_interface_uses_gradio_custom_component(self):
        interface_blocks_value=build_sprite_editor_interface(8770)
        configuration_record_value=interface_blocks_value.get_config_file()
        self.assertIn('sprite-editor-root',str(configuration_record_value))
        self.assertNotIn('<iframe',str(configuration_record_value))
        current_playback_events=[current_event_record for current_event_record in configuration_record_value['dependencies'] if 'spriteEditorPlaybackControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_playback_events),4)
        current_view_events=[current_event_record for current_event_record in configuration_record_value['dependencies'] if 'spriteEditorViewControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_view_events),6)
        current_source_events=[current_event_record for current_event_record in configuration_record_value['dependencies'] if any(current_bridge_name in (current_event_record.get('js') or '') for current_bridge_name in ('spriteEditorSourceControls','spriteEditorDirectionControls'))]
        self.assertEqual(len(current_source_events),3)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_source_events))
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_view_events))
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_playback_events))

    def test_editor_commands_preserve_browser_state_contract(self):
        current_interface_config=build_sprite_editor_interface(8770).get_config_file()
        for current_bridge_name,current_event_count in (
            ('spriteEditorScopeControls',1),('spriteEditorSelectionControls',2),
            ('spriteEditorNumericControls',2),('spriteEditorAlignmentControls',1),
            ('spriteEditorGuideControls',5),('spriteEditorSaveControls',1),
            ('spriteEditorHistoryControls',5),
        ):
            with self.subTest(bridge=current_bridge_name):
                current_matching_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if current_bridge_name in (current_event_record.get('js') or '')]
                self.assertEqual(len(current_matching_events),current_event_count)
                self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_matching_events))
        current_markup_text=read_sprite_editor_markup()
        for current_removed_id in ('sprite-frame-options','sprite-scope','sprite-fields','sprite-guide-list','sprite-history','sprite-history-input','sprite-align-floor','sprite-align-center','sprite-normalize','sprite-apply'):
            self.assertNotIn('id="'+current_removed_id+'"',current_markup_text)
        for current_retained_id in ('sprite-timeline','sprite-canvas'):
            self.assertIn('id="'+current_retained_id+'"',current_markup_text)

    def test_loader_targets_review_server_component_route(self):
        loader_script_text=create_sprite_editor_loader(8770)
        self.assertIn("spriteEditorServerBase='http://127.0.0.1:8770'",loader_script_text)
        self.assertIn("+'/character-animation/sprite-editor.js'",loader_script_text)
        self.assertIn('sprite-canvas',read_sprite_editor_markup())

    def test_comparison_and_export_use_shared_styles(self):
        editor_markup_text=read_sprite_editor_markup()
        for required_element_name in ('sprite-canvas','sprite-directions','sprite-sheet'):
            self.assertIn(required_element_name,str(build_sprite_editor_interface(8770).get_config_file()))
        self.assertNotIn('id="sprite-original"',editor_markup_text)
        for removed_control_name in ('sprite-save','sprite-frames-all','sprite-frames-none','sprite-undo','sprite-reset','sprite-guides','sprite-onion','sprite-mode','sprite-asset','sprite-asset-load','sprite-direction','sprite-zoom','sprite-background','sprite-speed','sprite-prev','sprite-play','sprite-stop','sprite-next','sprite-json','sprite-png','sprite-png-all','sprite-size','sprite-height','sprite-job','sprite-load'):
            self.assertNotIn('id="'+removed_control_name+'"',editor_markup_text)
        self.assertNotIn('--page:',read_sprite_editor_styles())
        self.assertNotIn('.gradio-container',read_sprite_editor_styles())
        self.assertIn('--sprite-display-size',read_sprite_editor_styles())
        self.assertNotIn('border-radius',read_sprite_editor_styles())
        self.assertNotIn('padding:',read_sprite_editor_styles())
