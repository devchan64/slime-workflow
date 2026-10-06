import unittest

from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface, create_anny_attribute_loader, read_anny_attribute_markup
from tools.review.ui_assets import resolve_review_ui_asset


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_anny_attribute_interface(8770)
        configuration_value = interface_blocks_value.get_config_file()
        self.assertIn('anny-attribute-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))
        self.assertNotIn('## Anny 속성 렌더러', str(configuration_value))

    def test_actions_are_native_browser_commands(self):
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_action_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'annyAttributeActions' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_action_events),3)
        for current_event_record in current_action_events:
            self.assertFalse(current_event_record['backend_fn'])
        current_markup_text=read_anny_attribute_markup()
        for current_button_identifier in ('reset','generate-preview','retry'):
            self.assertNotIn('id="'+current_button_identifier+'"',current_markup_text)
        self.assertIn('aria-live="polite"',current_markup_text)

    def test_uses_selected_history_actions(self):
        markup_text = read_anny_attribute_markup()
        history_script_text = resolve_review_ui_asset('generation-history.js').read_text()
        self.assertIn('data-selection-actions="true"', markup_text)
        self.assertIn('data-individual-history-delete="true"', markup_text)
        self.assertIn('createSelectedHistoryActions', history_script_text)
        self.assertIn('deleteSelectedHistoryRecord', history_script_text)
        self.assertIn('이력 수동 초기화', history_script_text)

    def test_loader_preserves_attribute_component_dependencies(self):
        loader_script_text=create_anny_attribute_loader(8770)
        self.assertIn("http://127.0.0.1:8770'+currentPathValue",loader_script_text)
        self.assertIn('/anny-attributes/mesh-viewer.js',loader_script_text)
        self.assertIn('/anny-attributes/history-ui.js',loader_script_text)
        self.assertIn('mesh-preview',read_anny_attribute_markup())
        self.assertNotIn('/management/workflow-ui.js',loader_script_text)
        self.assertNotIn('id="baseline-profile"',read_anny_attribute_markup())
        self.assertNotIn('id="render-rotation-y"',read_anny_attribute_markup())


if __name__ == '__main__':
    unittest.main()
