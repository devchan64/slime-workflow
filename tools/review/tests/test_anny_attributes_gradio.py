import unittest

from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface, create_anny_attribute_loader, read_anny_attribute_markup


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_anny_attribute_interface(8770)
        configuration_value = interface_blocks_value.get_config_file()
        self.assertIn('anny-attribute-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))

    def test_loader_preserves_attribute_component_dependencies(self):
        loader_script_text=create_anny_attribute_loader(8770)
        self.assertIn("http://127.0.0.1:8770'+currentPathValue",loader_script_text)
        self.assertIn('/anny-attributes/mesh-viewer.js',loader_script_text)
        self.assertIn('/anny-attributes/history-ui.js',loader_script_text)
        self.assertIn('mesh-preview',read_anny_attribute_markup())


if __name__ == '__main__':
    unittest.main()
