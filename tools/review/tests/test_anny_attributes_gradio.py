import unittest

from tools.review.ui.gradio.anny_attributes_app import MANAGEMENT_SHARED_STYLES, build_anny_attribute_interface, create_anny_attribute_loader, read_anny_attribute_markup
from tools.review.ui_assets import resolve_review_ui_asset


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_anny_attribute_interface(8770)
        configuration_value = interface_blocks_value.get_config_file()
        self.assertIn('anny-attribute-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))
        self.assertNotIn('## Anny 속성 렌더러', str(configuration_value))

    def test_uses_shared_management_style_tokens(self):
        self.assertIn('--page:#10151f', MANAGEMENT_SHARED_STYLES)
        self.assertIn('button.primary', MANAGEMENT_SHARED_STYLES)
        markup_text = read_anny_attribute_markup()
        self.assertIn('class="primary"', markup_text)
        self.assertIn('aria-live="polite"', markup_text)

    def test_uses_selected_history_actions(self):
        markup_text = read_anny_attribute_markup()
        history_script_text = resolve_review_ui_asset('generation-history.js').read_text()
        self.assertIn('data-selection-actions="true"', markup_text)
        self.assertIn('createSelectedHistoryActions', history_script_text)
        self.assertIn('이력 수동 초기화', history_script_text)

    def test_loader_preserves_attribute_component_dependencies(self):
        loader_script_text=create_anny_attribute_loader(8770)
        self.assertIn("http://127.0.0.1:8770'+currentPathValue",loader_script_text)
        self.assertIn('/anny-attributes/mesh-viewer.js',loader_script_text)
        self.assertIn('/anny-attributes/history-ui.js',loader_script_text)
        self.assertIn('mesh-preview',read_anny_attribute_markup())


if __name__ == '__main__':
    unittest.main()
