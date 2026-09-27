"""스프라이트 편집기 Gradio 연결을 검증한다."""
import unittest

from tools.review.ui.gradio.sprite_editor_app import build_sprite_editor_interface, create_sprite_editor_loader, read_sprite_editor_markup, read_sprite_editor_styles


class SpriteEditorGradioTests(unittest.TestCase):
    def test_interface_uses_gradio_custom_component(self):
        interface_blocks_value=build_sprite_editor_interface(8770)
        configuration_record_value=interface_blocks_value.get_config_file()
        self.assertIn('sprite-editor-root',str(configuration_record_value))
        self.assertNotIn('<iframe',str(configuration_record_value))

    def test_loader_targets_review_server_component_route(self):
        loader_script_text=create_sprite_editor_loader(8770)
        self.assertIn("spriteEditorServerBase='http://127.0.0.1:8770'",loader_script_text)
        self.assertIn("+'/character-animation/sprite-editor.js'",loader_script_text)
        self.assertIn('sprite-canvas',read_sprite_editor_markup())

    def test_comparison_and_export_use_shared_styles(self):
        editor_markup_text=read_sprite_editor_markup()
        for required_element_name in ('sprite-canvas','sprite-directions','sprite-sheet'):
            self.assertIn(required_element_name,editor_markup_text)
        self.assertNotIn('id="sprite-original"',editor_markup_text)
        for removed_control_name in ('sprite-json','sprite-png','sprite-png-all','sprite-size','sprite-height'):
            self.assertNotIn('id="'+removed_control_name+'"',editor_markup_text)
        self.assertIn('--page:',read_sprite_editor_styles())
        self.assertIn('#sprite-editor-root>header',read_sprite_editor_styles())
